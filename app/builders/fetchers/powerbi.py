"""
PowerBIFetcher — fetcher para reports públicos de Power BI embebidos.

Extrae datos de cualquier visual de un report Power BI público usando la API
interna de querydata con paginación por restart tokens y decodificación DSR.

Params configurables via ResourceParam:
    resource_key   X-PowerBI-ResourceKey (del token embed, campo "k")
    model_id       ID numérico del modelo Power BI
    dataset_id     UUID del dataset
    report_id      UUID del report
    visual_id      ID del visual (cualquier ID válido del report)
    query_json     JSON string con el SemanticQuery completo:
                     {From:[...], Select:[...], Where:[...], OrderBy:[...]}
    projections    Índices de proyección separados por coma, ej: "0,1,2"
    field_mapping  JSON string mapeando Gn → nombre de campo,
                     ej: {"G0":"nombre","G1":"web","G2":"tipo"}
                     Si no se define, las claves son G0, G1, G2...
    page_size      Filas por página (default: 500)
    delay          Segundos de pausa entre páginas (default: 0.3)

Ejemplo de uso en config_rer.md / panel de administración:
    resource_key = 5a615f34-c120-4fed-bcc1-36363c54ff04
    model_id     = 2721370
    dataset_id   = 6f51204d-cbf7-43c8-ac29-dfc58aad4bef
    report_id    = b55dc753-a2c9-4bc1-9b3a-08a4e08f03b4
    visual_id    = 5db35b33b48d207fc294
    query_json   = {"From":[...],"Select":[...],...}
    projections  = 0,1,2
    field_mapping = {"G0":"nombre_confer","G1":"pagina_web","G2":"tipo_entidad"}
"""

import json
import logging
import time
from typing import Any, Dict, List

import requests

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData

logger = logging.getLogger(__name__)

_API_URL = (
    "https://wabi-west-europe-e-primary-api.analysis.windows.net"
    "/public/reports/querydata?synchronous=true"
)


# ── DSR decoder ───────────────────────────────────────────────────────────────

def _decode_dsr(ds: dict) -> list[dict]:
    """
    Decodifica el formato DSR (Data Shape Result) comprimido de Power BI.

    Estructura relevante:
      ds["ValueDicts"]       → {"D0":[...], "D1":[...], ...}
      ds["PH"][n]["DM0"]     → filas comprimidas
      ds["IC"]               → False = hay más datos (not complete)
      ds["RT"]               → restart token para siguiente página

    Cada fila puede tener:
      S  → schema de columnas [{N:"G0", T:1, DN:"D0"}, ...]
           T=1 → referencia a diccionario DN; T=0/4 → valor directo
      C  → valores comprimidos (índices o directos)
      R  → bitmask: columna i repite el valor anterior si bit i está activo
      Ø  → bitmask: columna i es nula si bit i está activo
    """
    value_dicts: dict = ds.get("ValueDicts", {})
    rows_out: list[dict] = []

    for group in ds.get("PH", []):
        schema: list = []
        prev_vals: dict = {}

        for row in group.get("DM0", []):
            if "S" in row:
                schema = row["S"]

            null_mask   = row.get("Ø", 0)
            repeat_mask = row.get("R", 0)
            c_values    = row.get("C", [])
            c_idx       = 0
            current: dict = {}

            for col_i, col_def in enumerate(schema):
                col_name  = col_def["N"]
                is_null   = bool(null_mask   & (1 << col_i))
                is_repeat = bool(repeat_mask & (1 << col_i))

                if is_null:
                    current[col_name] = None
                elif is_repeat:
                    current[col_name] = prev_vals.get(col_name)
                else:
                    if c_idx < len(c_values):
                        raw_val = c_values[c_idx]
                        c_idx += 1
                        if col_def.get("T") == 1:
                            d = value_dicts.get(col_def.get("DN", ""), [])
                            current[col_name] = (
                                d[raw_val]
                                if isinstance(raw_val, int) and raw_val < len(d)
                                else raw_val
                            )
                        else:
                            current[col_name] = raw_val
                    else:
                        current[col_name] = None

            prev_vals = {**prev_vals, **current}
            rows_out.append(dict(current))

    return rows_out


def _has_more(ds: dict) -> bool:
    """IC=False → datos incompletos (hay más páginas)."""
    return not ds.get("IC", True)


# ── Fetcher ───────────────────────────────────────────────────────────────────

class PowerBIFetcher(BaseFetcher):
    """Fetcher para reports públicos de Power BI con paginación DSR."""

    def _build_headers(self) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://app.powerbi.com",
            "Referer": "https://app.powerbi.com/",
            "X-PowerBI-ResourceKey": self.params["resource_key"],
        }

    def _build_payload(self, query: dict, projections: list[int],
                       restart_token: list | None, page_size: int) -> dict:
        window: dict = {"Count": page_size}
        if restart_token:
            window["RestartTokens"] = [restart_token]

        return {
            "version": "1.0.0",
            "queries": [{
                "Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
                    "Query": query,
                    "Binding": {
                        "Primary": {
                            "Groupings": [{"Projections": projections, "Subtotal": 1}],
                        },
                        "DataReduction": {
                            "DataVolume": 3,
                            "Primary": {"Window": window},
                        },
                        "Version": 1,
                        "ExecutionMetricsKind": 1,
                    },
                }}]},
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": self.params["dataset_id"],
                    "Sources": [{
                        "ReportId": self.params["report_id"],
                        "VisualId": self.params.get("visual_id", "powerbi_fetcher"),
                    }],
                },
            }],
            "cancelQueries": [],
            "modelId": int(self.params["model_id"]),
        }

    def fetch(self) -> RawData:
        """Pagina el endpoint querydata y devuelve todas las filas DSR decodificadas."""
        required = ("resource_key", "model_id", "dataset_id", "report_id", "query_json")
        for k in required:
            if not self.params.get(k):
                raise ValueError(f"PowerBIFetcher requiere el parámetro '{k}'")

        query: dict = json.loads(self.params["query_json"])

        proj_raw = self.params.get("projections", "")
        projections: list[int] = (
            [int(x.strip()) for x in proj_raw.split(",") if x.strip()]
            if proj_raw
            else list(range(len(query.get("Select", []))))
        )

        page_size = int(self.params.get("page_size", 500))
        delay     = float(self.params.get("delay", 0.3))
        timeout   = int(self.params.get("timeout", 60))

        headers  = self._build_headers()
        session  = requests.Session()
        all_rows: list[dict] = []
        restart_token: list | None = None
        page = 0

        while True:
            page += 1
            payload = self._build_payload(query, projections, restart_token, page_size)
            logger.info(f"PowerBIFetcher — página {page} (acumuladas: {len(all_rows)})")

            resp = session.post(_API_URL, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            try:
                ds = data["results"][0]["result"]["data"]["dsr"]["DS"][0]
            except (KeyError, IndexError) as exc:
                raise ValueError(
                    f"Respuesta Power BI inesperada: {str(data)[:300]}"
                ) from exc

            rows = _decode_dsr(ds)
            if not rows:
                logger.info("  Sin filas — fin de datos.")
                break

            all_rows.extend(rows)
            logger.info(f"  +{len(rows)} filas (total: {len(all_rows)})")

            if not _has_more(ds):
                logger.info("  IC=True — datos completos.")
                break

            rt = ds.get("RT")
            if not rt:
                logger.warning("  Sin restart token — fin de paginación.")
                break

            restart_token = rt[0]

            if delay > 0:
                time.sleep(delay)

        logger.info(f"PowerBIFetcher completado: {len(all_rows)} filas en {page} páginas")
        return all_rows

    def parse(self, raw: RawData) -> ParsedData:
        """
        Aplica field_mapping si está definido: renombra G0/G1/... a nombres semánticos.
        field_mapping: JSON string, ej: {"G0":"nombre","G1":"web"}
        """
        mapping_raw = self.params.get("field_mapping", "")
        if not mapping_raw:
            return raw

        mapping: dict = json.loads(mapping_raw) if isinstance(mapping_raw, str) else mapping_raw

        result = []
        for row in raw:
            mapped = {}
            for gkey, value in row.items():
                mapped[mapping.get(gkey, gkey)] = value
            result.append(mapped)
        return result

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
