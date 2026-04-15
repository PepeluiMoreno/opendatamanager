"""
JsonTimeseriesFetcher — Fetcher genérico para APIs JSON que devuelven series temporales.

Muchas APIs estadísticas devuelven datos con esta estructura:
    [
        {
            "<meta_container>": [
                {"<meta_code_field>": "M", "<meta_name_field>": "Hombres",
                 "<meta_dim_path>":   "SEX"}
            ],
            "<data_container>": [
                {"<period_field>": 2023, "<subperiod_field>": "1",
                 "<value_field>": 104215, "<secret_field>": false}
            ]
        },
        ...
    ]

El fetcher aplana cada elemento de la lista raíz en registros tabulares,
extrayendo las dimensiones de metadatos y los valores temporales.

Params configurables (ResourceParam):
    url                 — Endpoint completo (obligatorio)
    method              — HTTP verb (default: GET)
    query_params        — JSON de query string params, ej: '{"nult":"10","det":"2"}'
    headers             — JSON de headers adicionales
    timeout             — Timeout HTTP (default: 120)
    batch_size          — Registros por chunk (default: 500)

    # Estructura del JSON de respuesta
    root_path           — Key para acceder al array raíz, ej: "datos"
                          vacío o ausente = la respuesta ES el array raíz
    meta_container      — Key que contiene el array de metadatos por serie (ej: "MetaData")
    meta_code_field     — Key del código dentro de cada item de metadatos (ej: "Codigo")
    meta_name_field     — Key del nombre dentro de cada item de metadatos (ej: "Nombre")
    meta_dim_path       — Path (dot-notation) para obtener el nombre de la dimensión
                          desde cada item de metadatos. Ej: "Variable.Codigo"
    data_container      — Key que contiene el array de datos por serie (ej: "Data")
    period_field        — Key del periodo principal dentro de cada dato (ej: "Anyo")
    subperiod_field     — Key del subperiodo (ej: "Periodo"); vacío si no existe
    value_field         — Key del valor numérico (ej: "Valor")
    secret_field        — Key boolean para excluir datos secretos/suprimidos (ej: "Secreto")
    serie_name_field    — Key del nombre de la serie en el elemento raíz (ej: "Nombre")
                          Si existe, se añade como campo "serie_nombre"

    # Modo de salida
    flatten_mode        — "long" (default) | "wide"
                          long: una fila por (serie × periodo)
                          wide: una fila por serie, con columna por cada periodo
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Generator, List, Optional

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData

logger = logging.getLogger(__name__)


def _get_path(obj: dict, path: str) -> Any:
    """Accede a un valor anidado con dot-notation. Ej: 'Variable.Codigo'"""
    for key in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


class JsonTimeseriesFetcher(BaseFetcher):
    """
    Fetcher genérico para APIs que devuelven arrays de series temporales con metadatos.
    Aplana la estructura en registros tabulares listos para staging/loading.
    """

    def fetch(self) -> RawData:
        url = self.params.get("url")
        if not url:
            raise ValueError("Param 'url' obligatorio para JsonTimeseriesFetcher")

        method = self.params.get("method", "GET").upper()
        timeout = int(self.params.get("timeout", 120))
        headers = self._parse_json_param("headers", {})
        query_params = self._parse_json_param("query_params", {})

        logger.info("[JsonTS] Fetching %s (method=%s)", url, method)
        resp = self._request(None, method, url, params=query_params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        logger.info("[JsonTS] Received %d bytes", len(resp.content))
        return resp.text

    def parse(self, raw: RawData) -> ParsedData:
        if not raw or not raw.strip():
            raise ValueError("Respuesta vacía")
        data = json.loads(raw)

        root_path = self.params.get("root_path", "").strip()
        if root_path:
            for key in root_path.split("."):
                data = data.get(key)
                if data is None:
                    raise ValueError(f"root_path '{root_path}' no encontrado en la respuesta")

        if not isinstance(data, list):
            raise ValueError(f"Se esperaba lista, se obtuvo {type(data).__name__}")

        logger.info("[JsonTS] Parsed %d series", len(data))
        return data

    def normalize(self, parsed: ParsedData) -> DomainData:
        records = []
        for chunk in self._stream_parsed(parsed):
            records.extend(chunk)
        return records

    def stream(self) -> Generator[List[Dict], None, None]:
        raw = self.fetch()
        series_list = self.parse(raw)
        yield from self._stream_parsed(series_list)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stream_parsed(self, series_list: list) -> Generator[List[Dict], None, None]:
        batch_size = int(self.params.get("batch_size", 500))
        flatten_mode = self.params.get("flatten_mode", "long")

        meta_container  = self.params.get("meta_container",   "MetaData")
        meta_code_field = self.params.get("meta_code_field",  "Codigo")
        meta_name_field = self.params.get("meta_name_field",  "Nombre")
        meta_dim_path   = self.params.get("meta_dim_path",    "Variable.Codigo")
        data_container  = self.params.get("data_container",   "Data")
        period_field    = self.params.get("period_field",     "Anyo")
        subperiod_field = self.params.get("subperiod_field",  "")
        value_field     = self.params.get("value_field",      "Valor")
        secret_field    = self.params.get("secret_field",     "Secreto")
        serie_name_field = self.params.get("serie_name_field", "Nombre")

        batch: List[Dict] = []

        for serie in series_list:
            # ── Extraer dimensiones de metadatos ────────────────────────────
            meta: Dict[str, str] = {}
            if serie_name_field and serie_name_field in serie:
                meta["serie_nombre"] = serie[serie_name_field]

            for item in serie.get(meta_container, []):
                code = item.get(meta_code_field, "")
                name = item.get(meta_name_field, "")
                dim = _get_path(item, meta_dim_path) or "dim"
                dim_key = self._slug(dim)
                meta[f"{dim_key}_cod"]    = code
                meta[f"{dim_key}_nombre"] = name

            data_points = serie.get(data_container, [])

            if flatten_mode == "wide":
                record = {**meta}
                for pt in data_points:
                    if secret_field and pt.get(secret_field):
                        continue
                    period = str(pt.get(period_field, ""))
                    subp = str(pt.get(subperiod_field, "")).strip() if subperiod_field else ""
                    col = f"v_{period}_{subp}" if subp else f"v_{period}"
                    record[col] = pt.get(value_field)
                batch.append(record)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            else:
                # long — una fila por (serie, periodo)
                for pt in data_points:
                    if secret_field and pt.get(secret_field):
                        continue
                    record = {
                        **meta,
                        "periodo_principal": pt.get(period_field),
                        "valor": pt.get(value_field),
                    }
                    if subperiod_field:
                        record["subperiodo"] = pt.get(subperiod_field)
                    batch.append(record)
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []

        if batch:
            yield batch

    # ── Utils ────────────────────────────────────────────────────────────────

    def _parse_json_param(self, key: str, default: Any) -> Any:
        raw = self.params.get(key, "")
        if not raw:
            return default
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _slug(text: str) -> str:
        _MAP = str.maketrans("áéíóúÁÉÍÓÚñÑüÜ", "aeiouAEIOUnNuU")
        t = str(text).translate(_MAP).strip().lower()
        t = re.sub(r"[\s\-/\\\.()]+", "_", t)
        t = re.sub(r"[^\w]", "", t)
        return re.sub(r"_+", "_", t).strip("_") or "dim"
