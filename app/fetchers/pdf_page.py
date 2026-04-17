"""
app/fetchers/pdf_page.py

Fetcher genérico para páginas web que publican colecciones de PDFs
organizadas por ejercicio (año fiscal u otro parámetro periódico).

Params del Resource:
  url_template   (required) — URL con {ejercicio}, p.ej.
                              "https://example.es/presupuesto/{ejercicio}"
  pdf_dir        (required) — directorio destino, también templatable:
                              "data/pdfs/presupuesto/{ejercicio}"
  ejercicio      (required) — valor a interpolar; puede venir como
                              execution_param para reutilizar el Resource
                              por periodo sin crear uno nuevo
  url_overrides  (optional) — JSON con excepciones al template:
                              {"2026": "https://example.es/presupuesto/2026/prorroga-2025"}
                              Si ejercicio tiene entrada aquí, se usa
                              esta URL en lugar del template.
  script_module  (required) — módulo Python que sabe parsear los PDFs
                              descargados. Misma interfaz que ScriptFetcher:
                              def run(params: dict) -> list[dict]
  function_name  (optional, default: "run")
  link_selector  (optional, default: "a[href$='.pdf']") — selector CSS
                              para filtrar qué enlaces descargar
  delay_seconds  (optional, default: 1.0) — pausa entre descargas
"""

import importlib
import json
import logging
import time
from pathlib import Path
from typing import Any, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

# Params consumidos por el fetcher, no pasados al script
_FETCHER_PARAMS = {
    "url_template", "pdf_dir", "ejercicio", "url_overrides",
    "script_module", "function_name", "link_selector", "delay_seconds",
    "num_workers", "max_retries", "retry_backoff", "timeout",
    "_staging_path", "_resume_state",
}


class PdfPageFetcher(BaseFetcher):
    """
    Fetcher genérico para colecciones de PDFs publicadas en una página web
    organizadas por ejercicio.

    Pipeline:
      fetch()     — resuelve URL, scrapea enlaces PDF, los descarga a pdf_dir
      parse()     — carga script_module, llama function_name(params), devuelve registros
      normalize() — garantiza serialización JSON
    """

    # ── Resolución de URL y directorio ────────────────────────────────────────

    def _resolve_url(self) -> str:
        ejercicio = self.params.get("ejercicio", "")
        overrides_raw = self.params.get("url_overrides", "{}")

        try:
            overrides = json.loads(overrides_raw) if isinstance(overrides_raw, str) else overrides_raw
        except json.JSONDecodeError:
            logger.warning("[PdfPageFetcher] url_overrides no es JSON válido; se ignora.")
            overrides = {}

        if ejercicio in overrides:
            url = overrides[ejercicio]
            logger.info(f"[PdfPageFetcher] URL override para {ejercicio}: {url}")
            return url

        template = self.params.get("url_template", "")
        if not template:
            raise ValueError("PdfPageFetcher requiere 'url_template'.")
        return template.format(ejercicio=ejercicio)

    def _resolve_pdf_dir(self) -> Path:
        ejercicio = self.params.get("ejercicio", "")
        pdf_dir = self.params.get("pdf_dir", "")
        if not pdf_dir:
            raise ValueError("PdfPageFetcher requiere 'pdf_dir'.")
        resolved = Path(pdf_dir.format(ejercicio=ejercicio))
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    # ── Descubrimiento y descarga de PDFs ─────────────────────────────────────

    def _discover_pdf_links(self, page_url: str) -> list[str]:
        """Extrae enlaces a PDF de la página usando el selector configurado."""
        selector = self.params.get("link_selector", "a[href$='.pdf']")
        response = self._request(None, "GET", page_url)
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for a in soup.select(selector):
            href = a.get("href", "")
            if not href:
                continue
            full_url = urljoin(page_url, href)
            links.append(full_url)

        logger.info(f"[PdfPageFetcher] {len(links)} PDFs descubiertos en {page_url}")
        return links

    def _download_pdfs(self, links: list[str], pdf_dir: Path) -> list[Path]:
        """Descarga los PDFs al directorio destino. Omite los ya existentes."""
        delay = float(self.params.get("delay_seconds", 1.0))
        downloaded = []

        for i, url in enumerate(links):
            filename = Path(urlparse(url).path).name
            dest = pdf_dir / filename

            if dest.exists():
                logger.info(f"[PdfPageFetcher] Ya existe, omitido: {filename}")
                downloaded.append(dest)
                continue

            response = self._request(None, "GET", url)
            dest.write_bytes(response.content)
            logger.info(f"[PdfPageFetcher] Descargado: {filename} ({len(response.content) // 1024} KB)")
            downloaded.append(dest)

            if i < len(links) - 1:
                time.sleep(delay)

        return downloaded

    # ── Carga del script externo ──────────────────────────────────────────────

    def _load_function(self):
        module_path = self.params.get("script_module")
        if not module_path:
            raise ValueError("PdfPageFetcher requiere 'script_module'.")

        function_name = self.params.get("function_name", "run")

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ValueError(
                f"No se pudo importar '{module_path}': {e}"
            ) from e

        fn = getattr(module, function_name, None)
        if fn is None or not callable(fn):
            raise ValueError(
                f"'{module_path}' no expone la función callable '{function_name}'."
            )

        logger.info(f"[PdfPageFetcher] Script: {module_path}.{function_name}()")
        return fn

    def _script_params(self, pdf_dir: Path) -> dict:
        """Params que se pasan al script: los del Resource más pdf_dir resuelto."""
        return {
            k: v for k, v in self.params.items()
            if k not in _FETCHER_PARAMS
        } | {"pdf_dir": str(pdf_dir)}

    # ── Pipeline BaseFetcher ──────────────────────────────────────────────────

    def fetch(self) -> RawData:
        """
        1. Resuelve URL y pdf_dir interpolando {ejercicio}
        2. Descubre y descarga PDFs
        3. Llama al script con pdf_dir resuelto
        """
        url = self._resolve_url()
        pdf_dir = self._resolve_pdf_dir()

        logger.info(f"[PdfPageFetcher] Scrapeando: {url}")
        links = self._discover_pdf_links(url)

        if not links:
            logger.warning(f"[PdfPageFetcher] Ningún PDF encontrado en {url}")
            return []

        self._download_pdfs(links, pdf_dir)

        fn = self._load_function()
        script_params = self._script_params(pdf_dir)

        result = fn(script_params)

        if result is None:
            return []
        if not isinstance(result, list):
            raise TypeError(
                f"El script debe devolver list[dict], devolvió {type(result).__name__}."
            )

        logger.info(f"[PdfPageFetcher] {len(result)} registros obtenidos.")
        return result

    def parse(self, raw: RawData) -> ParsedData:
        """Valida que los registros sean dicts."""
        clean, skipped = [], 0
        for item in raw:
            if isinstance(item, dict):
                clean.append(item)
            else:
                skipped += 1
        if skipped:
            logger.warning(f"[PdfPageFetcher] {skipped} registros descartados (no son dicts).")
        return clean

    def normalize(self, parsed: ParsedData) -> DomainData:
        """Garantiza serialización JSON de todos los valores."""
        normalized = []
        for record in parsed:
            norm = {}
            for k, v in record.items():
                if v is None or isinstance(v, (str, int, float, bool)):
                    norm[k] = v
                else:
                    norm[k] = str(v)
            normalized.append(norm)
        return normalized
