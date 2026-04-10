"""
FotocasaFetcher — Scraper del directorio de agencias inmobiliarias de Fotocasa.

Fuente: https://www.fotocasa.es/buscar-agencias-inmobiliarias/{provincia}/todas-las-zonas/l

Pivota sobre las 52 provincias españolas, pagina automáticamente (rel="next")
y extrae TODOS los atributos data-agency-* de cada <article>, las estadísticas
de inmuebles y la URL de búsqueda de la agencia.

Campos extraídos:
    agency_id          — clientId numérico de Fotocasa  ← clave idempotente
    nombre             — nombre de la agencia
    provincia          — slug de provincia (ej. "madrid-provincia")
    url_busqueda       — URL de búsqueda de inmuebles de la agencia
    inmuebles_zona     — inmuebles publicados en la zona (número)
    inmuebles_total    — inmuebles publicados en total
    precio_minimo      — precio mínimo publicado (texto con €)
    posicion_pagina    — posición ordinal en el listado (útil para rankings)
    + cualquier otro data-agency-* que Fotocasa añada en el futuro

Parámetros del resource:
    provinces              — JSON array de slugs de provincia (default: 52 provincias)
    delay_between_pages    — segundos entre páginas de una provincia (default: 1.5)
    delay_between_provinces — segundos entre provincias (default: 2.0)
    max_pages              — máximo de páginas por provincia (default: 500)
    timeout                — timeout HTTP en segundos (default: 30)
"""

import html as html_lib
import json
import logging
import re
import time
from typing import Dict, Generator, List, Any

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fotocasa.es/buscar-agencias-inmobiliarias/{province}/todas-las-zonas/l"

ALL_PROVINCES = [
    "a-coruna-provincia", "albacete-provincia", "alicante-provincia",
    "almeria-provincia", "araba-alava-provincia", "asturias-provincia",
    "avila-provincia", "badajoz-provincia", "barcelona-provincia",
    "bizkaia-provincia", "burgos-provincia", "caceres-provincia",
    "cadiz-provincia", "cantabria-provincia", "castellon-provincia",
    "ceuta-provincia", "ciudad-real-provincia", "cordoba-provincia",
    "cuenca-provincia", "gipuzkoa-provincia", "girona-provincia",
    "granada-provincia", "guadalajara-provincia", "huelva-provincia",
    "huesca-provincia", "illes-balears-provincia", "jaen-provincia",
    "la-rioja-provincia", "las-palmas-provincia", "leon-provincia",
    "lleida-provincia", "lugo-provincia", "madrid-provincia",
    "malaga-provincia", "melilla-provincia", "murcia-provincia",
    "navarra-provincia", "ourense-provincia", "palencia-provincia",
    "pontevedra-provincia", "salamanca-provincia",
    "santa-cruz-de-tenerife-provincia", "segovia-provincia",
    "sevilla-provincia", "soria-provincia", "tarragona-provincia",
    "teruel-provincia", "toledo-provincia", "valencia-provincia",
    "valladolid-provincia", "zamora-provincia", "zaragoza-provincia",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.fotocasa.es/buscar-agencias-inmobiliarias/",
}

# Texto esperado en las 3 estadísticas de cada card (orden fijo en el HTML)
_STAT_KEYS = ["inmuebles_zona", "inmuebles_total", "precio_minimo"]


def _unescape(text: str) -> str:
    return html_lib.unescape(text or "").strip()


def _clean_number(text: str) -> str:
    """Devuelve solo el primer token numérico (elimina separadores de miles)."""
    m = re.match(r"[\d.,]+", text.replace(".", "").replace(",", "."))
    return m.group(0) if m else text.strip()


class FotocasaFetcher(BaseFetcher):

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

    # ------------------------------------------------------------------
    # Parámetros
    # ------------------------------------------------------------------

    def _get_provinces(self) -> List[str]:
        raw = self.params.get("provinces", "")
        if raw:
            if isinstance(raw, str):
                if raw.strip().startswith("["):
                    return json.loads(raw)
                return [v.strip() for v in raw.split(",") if v.strip()]
            return list(raw)
        return ALL_PROVINCES

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str) -> BeautifulSoup:
        resp = self._request(
            self.session, "GET", url,
            timeout=int(self.params.get("timeout", 30)),
        )
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # Extracción
    # ------------------------------------------------------------------

    def _extract_agencies(self, soup: BeautifulSoup, province: str) -> List[Dict[str, Any]]:
        """
        Extrae todos los <article data-agency-id> de la página.

        Para cada artículo se capturan:
          - TODOS los atributos data-agency-* (clave = nombre sin "data-", con guiones → _)
          - Las 3 estadísticas visibles (inmuebles_zona, inmuebles_total, precio_minimo)
          - La URL de búsqueda de la agencia (data-promiseref del primer botón)
          - El slug de provincia del pivot actual
        """
        records = []
        for article in soup.select("article[data-agency-id]"):
            record: Dict[str, Any] = {}

            # 1. Todos los atributos data-agency-*
            for attr, val in article.attrs.items():
                if attr.startswith("data-agency-"):
                    key = attr[len("data-"):].replace("-", "_")   # data-agency-id → agency_id
                    record[key] = _unescape(val) if isinstance(val, str) else val

            if not record.get("agency_id"):
                continue

            # 2. Nombre limpio (por si tiene entidades HTML)
            record["nombre"] = _unescape(record.get("agency_name", ""))
            del record["agency_name"]   # renombramos a 'nombre'

            # 3. Provincia del pivot
            record["provincia"] = province

            # 4. Estadísticas de inmuebles (3 ítems, orden fijo)
            stat_items = article.select(".re-description-item")
            for i, key in enumerate(_STAT_KEYS):
                if i < len(stat_items):
                    label_el = stat_items[i].select_one("label")
                    record[key] = _unescape(label_el.get_text()) if label_el else None
                else:
                    record[key] = None

            # 5. URL de búsqueda de inmuebles de la agencia
            btn = article.select_one("[data-promiseref]")
            record["url_busqueda"] = btn["data-promiseref"].strip() if btn else None

            records.append(record)
        return records

    def _has_next_page(self, soup: BeautifulSoup) -> str | None:
        """URL de la siguiente página vía rel=next, o None."""
        link = soup.select_one('a[rel="next"]')
        if link and link.get("href"):
            href = link["href"]
            return ("https://www.fotocasa.es" + href) if href.startswith("/") else href
        return None

    # ------------------------------------------------------------------
    # Interfaz BaseFetcher
    # ------------------------------------------------------------------

    def stream(self) -> Generator[List[Dict], None, None]:
        provinces = self._get_provinces()
        delay_pages = float(self.params.get("delay_between_pages", 1.5))
        delay_provs  = float(self.params.get("delay_between_provinces", 2.0))
        max_pages    = int(self.params.get("max_pages", 500))
        preview_limit = int(self.params.get("_preview_limit", 0))
        total_yielded = 0

        # Resume support
        resume      = self.params.get("_resume_state", {})
        start_prov  = resume.get("province_index", 0)

        for prov_idx, province in enumerate(provinces):
            if prov_idx < start_prov:
                continue

            page_num = 1
            if prov_idx == start_prov:
                page_num = resume.get("page_num", 1)

            url = BASE_URL.format(province=province)
            if page_num > 1:
                url = f"{url}?pagina={page_num}"

            logger.info(
                f"[{prov_idx+1}/{len(provinces)}] {province} — pág. {page_num}"
            )

            while page_num <= max_pages:
                try:
                    soup = self._fetch_page(url)
                except Exception as exc:
                    logger.error(f"  Error fetching {url}: {exc}")
                    break

                records = self._extract_agencies(soup, province)
                logger.info(f"  pág. {page_num}: {len(records)} agencias")

                if not records:
                    break

                if preview_limit:
                    records = records[: preview_limit - total_yielded]

                if records:
                    yield records
                    total_yielded += len(records)

                self.current_state = {
                    "province_index": prov_idx,
                    "page_num": page_num,
                }

                if preview_limit and total_yielded >= preview_limit:
                    return

                next_url = self._has_next_page(soup)
                if not next_url:
                    break

                url      = next_url
                page_num += 1
                if delay_pages > 0:
                    time.sleep(delay_pages)

            if delay_provs > 0 and prov_idx < len(provinces) - 1:
                time.sleep(delay_provs)

    def fetch(self) -> RawData:
        all_records: List[Dict] = []
        for chunk in self.stream():
            all_records.extend(chunk)
        logger.info(f"Fotocasa total: {len(all_records)} agencias")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
