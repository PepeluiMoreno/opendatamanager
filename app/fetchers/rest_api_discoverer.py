"""RestApiDiscovererFetcher — Descubre los datasets de una API REST leyendo su
OpenAPI y emite un recurso-hijo (API REST) por cada uno.

Pensado para SNPSAP/BDNS, pero parametrizado. Detecta los datasets por el patrón
`/{nombre}/busqueda` (endpoints paginados con envoltorio `content`) y emite un hijo
API REST configurado con la paginación correcta (page/pageSize, page=0). Opcional:
los catálogos lookup (GET de un solo segmento, arrays planos) como hijos pequeños.

Notas verificadas en vivo (no asumir):
  · `busqueda` (JSON estructurado, filtrable por nifCif/fecha) ≠ `exportar` (CSV de
    presentación): son proyecciones distintas. Por defecto se usa `busqueda`.
  · BDNS pagina con `pageSize` (no page_size) y empieza en page=0.
  · `vpd` es obligatorio (GE = estado general, o el portal de cada CCAA).
  · Los datasets son enormes (concesiones ~26M): el hijo necesita ventana temporal
    (fechaDesde/fechaHasta) — se deja al operador, no se fuerza en el descubridor.

modos: ["descubrir"].
"""
import json
import logging
import re
from typing import Any, Dict, List

import requests

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

_DEFAULT_SPEC = "https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json"
_DEFAULT_API_BASE = "https://www.infosubvenciones.es/bdnstrans/api"
# Endpoints de un solo segmento que NO son catálogos de datos (auth, microportal).
_LOOKUP_EXCLUDE = {"suscripciones", "vpd"}
_BUSQUEDA_RE = re.compile(r"^/(?P<name>[^/]+)/busqueda$")


class RestApiDiscovererFetcher(BaseFetcher):

    def _cfg(self) -> Dict[str, Any]:
        p = self.params
        return {
            "spec_url": p.get("openapi_url") or _DEFAULT_SPEC,
            "api_base": (p.get("api_base") or _DEFAULT_API_BASE).rstrip("/"),
            "vpd": p.get("vpd") or "GE",
            "page_size": str(p.get("page_size") or 100),
            "child": p.get("child_fetcher") or "API REST",
            "include_lookups": str(p.get("include_lookups", "")).lower() in ("1", "true", "sí", "si", "yes"),
        }

    def _dataset_child(self, cfg: Dict[str, Any], name: str) -> Dict[str, Any]:
        return {
            "url": f"{cfg['api_base']}/{name}/busqueda",
            "pagination": "page_number",
            "page_param": "page",
            "page_size_param": "pageSize",
            "page_size": cfg["page_size"],
            "start_page": "0",
            "content_field": "content",
            "query_params": json.dumps({"vpd": cfg["vpd"]}),
        }

    def _lookup_child(self, cfg: Dict[str, Any], name: str) -> Dict[str, Any]:
        return {
            "url": f"{cfg['api_base']}/{name}",
            "pagination": "none",
            "content_field": "",   # array en la raíz
            "query_params": json.dumps({"vpd": cfg["vpd"]}),
        }

    def propose(self) -> List[Dict[str, Any]]:
        cfg = self._cfg()
        logger.info(f"[rest-discover] Leyendo OpenAPI: {cfg['spec_url']}")
        spec = requests.get(cfg["spec_url"], headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                            timeout=int(self.params.get("timeout", 30))).json()
        paths = spec.get("paths", {})

        # Datasets: paths /{name}/busqueda
        datasets = {}
        for path, ops in paths.items():
            m = _BUSQUEDA_RE.match(path)
            if m and "get" in ops:
                name = m.group("name")
                tag = (ops["get"].get("tags") or [name])[0]
                datasets[name] = tag

        proposals: List[Dict[str, Any]] = []
        for name, tag in sorted(datasets.items()):
            proposals.append({
                "suggested_name": f"BDNS · {tag}"[:200],
                "matched_urls": [], "file_types": {}, "confidence": 0.95,
                "target_fetcher_code": cfg["child"],
                "target_params": self._dataset_child(cfg, name),
            })

        # Lookups (opcional): GET de un solo segmento sin /busqueda hermano.
        n_lookups = 0
        if cfg["include_lookups"]:
            for path, ops in paths.items():
                seg = path.strip("/").split("/")
                if len(seg) != 1 or "get" not in ops:
                    continue
                name = seg[0]
                if name in datasets or name in _LOOKUP_EXCLUDE:
                    continue   # tiene /busqueda (es un dataset por-id) o es auth/microportal
                tag = (ops["get"].get("tags") or [name])[0]
                proposals.append({
                    "suggested_name": f"BDNS lookup · {tag}"[:200],
                    "matched_urls": [], "file_types": {}, "confidence": 0.9,
                    "target_fetcher_code": cfg["child"],
                    "target_params": self._lookup_child(cfg, name),
                })
                n_lookups += 1

        self.profile_stats = {"total_files": len(proposals), "datasets": len(datasets), "lookups": n_lookups}
        logger.info(f"[rest-discover] {len(datasets)} dataset(s) + {n_lookups} lookup(s) -> {len(proposals)} hijo(s).")
        return proposals

    def fetch(self) -> RawData:
        raise NotImplementedError("La especie REST API (descubridor) solo opera en modo descubrir.")

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
