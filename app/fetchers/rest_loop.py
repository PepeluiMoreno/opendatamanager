"""
rest_loop.py

RestLoopFetcher — Fetcher para APIs REST que requieren iterar sobre un conjunto
de valores (p. ej. códigos de provincia) enviando una petición por valor.

Parámetros de configuración (ResourceParam):
  url              — Endpoint REST (obligatorio)
  method           — Verbo HTTP: GET | POST (default: POST)
  payload_template — JSON template; usa "{pivot}" donde va el valor iterado.
                     Ej: {"codigoProvincia": "{pivot}", "nombre": ""}
  pivot_values     — JSON array de valores a iterar.
                     Ej: ["01","02","03",...,"52"]
  id_field         — Campo para deduplicar registros entre iteraciones (opcional).
                     Si no se indica, no se deduplica.
  delay            — Segundos de espera entre peticiones (default: 2)
  timeout          — Timeout HTTP por petición (default: 30)
  headers          — JSON object con cabeceras adicionales (opcional)

Ejemplo — notarías por provincia:
  url              = https://guianotarial.notariado.org/guianotarial/rest/buscar/notarios
  method           = POST
  payload_template = {"nombre":"","apellidos":"","direccion":"","codigoPostal":"",
                       "codigoProvincia":"{pivot}","municipio":"",
                       "codigoSituacionNotario":"","idiomaExtranjero":""}
  pivot_values     = ["01","02","03",...,"52"]
  id_field         = codigoNotaria
  delay            = 3
"""
import json
import time
import logging
from typing import Dict, Generator, List, Any, Set

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

# Códigos INE de las 52 provincias españolas
INE_PROVINCIAS = [
    "01","02","03","04","05","06","07","08","09","10",
    "11","12","13","14","15","16","17","18","19","20",
    "21","22","23","24","25","26","27","28","29","30",
    "31","32","33","34","35","36","37","38","39","40",
    "41","42","43","44","45","46","47","48","49","50",
    "51","52",
]


class RestLoopFetcher(BaseFetcher):
    """
    Itera sobre pivot_values enviando una petición REST por cada valor.
    Acumula y deduplica resultados; emite por bloques (un bloque por valor).
    """

    def _get_pivot_values(self) -> List[str]:
        raw = self.params.get("pivot_values", "")
        if not raw:
            return INE_PROVINCIAS
        if isinstance(raw, list):
            return raw
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return INE_PROVINCIAS

    def _build_payload(self, pivot: str) -> dict:
        template = self.params.get("payload_template", "{}")
        if isinstance(template, dict):
            filled = json.dumps(template).replace("{pivot}", pivot)
        else:
            filled = str(template).replace("{pivot}", pivot)
        return json.loads(filled)

    def _extra_headers(self) -> dict:
        raw = self.params.get("headers", {})
        if isinstance(raw, str):
            return json.loads(raw) if raw.strip() else {}
        return raw or {}

    # ------------------------------------------------------------------
    # BaseFetcher interface
    # ------------------------------------------------------------------

    def fetch(self) -> RawData:
        """Not used directly — stream() overrides the pipeline."""
        return None

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed

    def stream(self) -> Generator[List[Dict], None, None]:
        url      = self.params["url"]
        method   = self.params.get("method", "POST").upper()
        delay    = float(self.params.get("delay", 2))
        timeout  = int(self.params.get("timeout", 30))
        id_field = self.params.get("id_field", "")
        preview_limit = int(self.params.get("_preview_limit", 0))

        # Resume state
        resume_state = self.params.get("_resume_state") or {}
        if isinstance(resume_state, str):
            resume_state = json.loads(resume_state)
        start_index = int(resume_state.get("pivot_index", 0))

        base_headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent":   "Mozilla/5.0",
            "Accept":       "application/json, text/plain, */*",
        }
        base_headers.update(self._extra_headers())

        pivot_values = self._get_pivot_values()

        # Rebuild seen set from existing staging file (avoids re-processing on resume)
        seen: Set[str] = set()
        if start_index > 0 and id_field:
            staging_path = self.params.get("_staging_path", "")
            if staging_path and os.path.exists(staging_path):
                logger.info(f"[RestLoop] Rebuilding seen-IDs from existing staging file…")
                with open(staging_path, encoding="utf-8") as sf:
                    for line in sf:
                        try:
                            rec = json.loads(line)
                            key = str(rec.get(id_field, ""))
                            if key:
                                seen.add(key)
                        except Exception:
                            pass
                logger.info(f"[RestLoop] Restored {len(seen)} seen IDs — resuming from pivot index {start_index}")

        total_emitted = 0

        for i, pivot in enumerate(pivot_values):
            if i < start_index:
                continue  # skip already-processed pivots
            if preview_limit and total_emitted >= preview_limit:
                break

            logger.info(f"[RestLoop] {i+1}/{len(pivot_values)} pivot={pivot!r}")

            # --- request with 429 backoff ---
            data = None
            max_retries = 4
            for attempt in range(max_retries):
                try:
                    if method == "GET":
                        resp = self._request(None, "GET", url,
                                             params={"pivot": pivot},
                                             headers=base_headers,
                                             timeout=timeout)
                    else:
                        payload = self._build_payload(pivot)
                        resp = self._request(None, method, url,
                                             json=payload,
                                             headers=base_headers,
                                             timeout=timeout)
                    data = resp.json()
                    break  # success
                except Exception as exc:
                    is_429 = "429" in str(exc)
                    if is_429 and attempt < max_retries - 1:
                        wait = delay * (4 ** attempt)  # 3s, 12s, 48s
                        logger.warning(f"[RestLoop] pivot={pivot!r} 429 — waiting {wait:.0f}s before retry {attempt+1}/{max_retries-1}")
                        time.sleep(wait)
                    else:
                        logger.warning(f"[RestLoop] pivot={pivot!r} error: {exc}")
                        break

            if data is None:
                # Always wait delay even after errors so we don't hammer the server
                if i < len(pivot_values) - 1:
                    time.sleep(delay)
                continue

            # Normalize to list
            if isinstance(data, dict):
                records = data.get("results", data.get("data", [data]))
            elif isinstance(data, list):
                records = data
            else:
                records = []

            if not records:
                if i < len(pivot_values) - 1:
                    time.sleep(delay)
                continue

            # Deduplicate
            chunk = []
            for rec in records:
                if id_field and isinstance(rec, dict):
                    key = str(rec.get(id_field, ""))
                    if key and key in seen:
                        continue
                    if key:
                        seen.add(key)
                chunk.append(rec)

            if chunk:
                if preview_limit:
                    remaining = preview_limit - total_emitted
                    chunk = chunk[:remaining]
                # Set state BEFORE yield — if FetcherManager breaks at the yield point,
                # the generator won't resume so code after yield never runs.
                self.current_state = {"pivot_index": i + 1}
                yield chunk
                total_emitted += len(chunk)
            else:
                # No data for this pivot but still advance the savepoint
                self.current_state = {"pivot_index": i + 1}

            if i < len(pivot_values) - 1:
                time.sleep(delay)
