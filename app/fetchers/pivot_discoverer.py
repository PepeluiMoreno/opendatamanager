"""PivotDiscovererFetcher — Cuarta estrategia de descubrimiento: el PIVOTE.

Descubre los valores de un parámetro de filtro (las opciones de un <select>:
provincia, confesión...) y emite UN RECURSO HIJO por valor —o por GRUPO de valores
cuando se declara un grano de agrupación—. Cada hijo es un searchloop (especie
"HTML (genérico)", navigation=searchloop) que **internaliza** los valores de su
grupo: el árbol queda al grano gobernable (p. ej. CCAA), y el pivote de acceso
(provincia) se esconde dentro de cada nodo.

Reutiliza la maquinaria del searchloop para DESCUBRIR los valores (sesión + form +
parseo del <select>): no la duplica.

Params:
  (todos los del searchloop que necesita el hijo: url, session_init_url,
   search_field_name, search_mode, rows_selector, detail_level, etc.)
  pivot_group_map   JSON {valor: grupo} o nombre de preset ("es_provincia_ccaa")
                    para agrupar (p. ej. provincias->CCAA). Vacío = 1 hijo por valor.
  child_fetcher     Especie-destino del hijo (def. "HTML (genérico)").

modos: ["descubrir"].
"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.fetchers.base import BaseDiscoverer

logger = logging.getLogger(__name__)

# Mapa INE provincia(código)->CCAA. Claves sin ceros a la izquierda (como vienen
# en los <select> de la administración: "1", "28", "7"...).
_ES_PROVINCIA_CCAA = {
    "1": "País Vasco", "2": "Castilla-La Mancha", "3": "Comunitat Valenciana",
    "4": "Andalucía", "5": "Castilla y León", "6": "Extremadura", "7": "Illes Balears",
    "8": "Cataluña", "9": "Castilla y León", "10": "Extremadura", "11": "Andalucía",
    "12": "Comunitat Valenciana", "13": "Castilla-La Mancha", "14": "Andalucía",
    "15": "Galicia", "16": "Castilla-La Mancha", "17": "Cataluña", "18": "Andalucía",
    "19": "Castilla-La Mancha", "20": "País Vasco", "21": "Andalucía", "22": "Aragón",
    "23": "Andalucía", "24": "Castilla y León", "25": "Cataluña", "26": "La Rioja",
    "27": "Galicia", "28": "Madrid", "29": "Andalucía", "30": "Región de Murcia",
    "31": "Navarra", "32": "Galicia", "33": "Asturias", "34": "Castilla y León",
    "35": "Canarias", "36": "Galicia", "37": "Castilla y León", "38": "Canarias",
    "39": "Cantabria", "40": "Castilla y León", "41": "Andalucía", "42": "Castilla y León",
    "43": "Cataluña", "44": "Aragón", "45": "Castilla-La Mancha", "46": "Comunitat Valenciana",
    "47": "Castilla y León", "48": "País Vasco", "49": "Castilla y León", "50": "Aragón",
    "51": "Ceuta", "52": "Melilla",
}
_PRESETS = {"es_provincia_ccaa": _ES_PROVINCIA_CCAA}

# Params que NO deben heredar los hijos (son de la fase de descubrimiento).
_DISCOVERY_ONLY = {"pivot_group_map", "child_fetcher", "navigation", "search_field_values", "pivot_form_url"}


class PivotDiscovererFetcher(BaseDiscoverer):

    def _group_map(self) -> Optional[Dict[str, str]]:
        raw = self.params.get("pivot_group_map")
        if not raw:
            return None
        if isinstance(raw, str):
            raw = raw.strip()
            if raw in _PRESETS:
                return _PRESETS[raw]
            return json.loads(raw)
        return raw

    def _child_params_base(self) -> Dict[str, str]:
        """Params del searchloop hijo = los del padre menos los de descubrimiento,
        forzando navigation=searchloop."""
        base = {k: v for k, v in self.params.items()
                if not k.startswith("_") and k not in _DISCOVERY_ONLY}
        base["navigation"] = "searchloop"
        return base

    def propose(self) -> List[Dict[str, Any]]:
        from app.fetchers.searchloop_html import SearchLoopHtmlFetcher
        # El <select> del pivote vive en la PÁGINA DEL FORMULARIO, no en el endpoint
        # de acción (POST). Para descubrir, apuntamos a pivot_form_url -> session_init_url
        # -> url. Los hijos conservan la 'url' de acción intacta.
        disc_params = dict(self.params)
        form_url = (self.params.get("pivot_form_url")
                    or self.params.get("session_init_url")
                    or self.params.get("url"))
        disc_params["url"] = form_url
        valores = SearchLoopHtmlFetcher(disc_params)._discover_search_values()
        logger.info(f"[pivote] {len(valores)} valores descubiertos en "
                    f"'{self.params.get('search_field_name')}' ({form_url}).")

        gmap = self._group_map()
        if gmap:
            grupos: Dict[str, List[str]] = {}
            sin_mapear = []
            for v in valores:
                g = gmap.get(str(v).lstrip("0") or "0") or gmap.get(str(v))
                if not g:
                    sin_mapear.append(v)
                    continue
                grupos.setdefault(g, []).append(v)
            if sin_mapear:
                logger.warning(f"[pivote] valores sin grupo (se omiten): {sin_mapear}")
        else:
            grupos = {str(v): [v] for v in valores}

        base = self._child_params_base()
        child = self.params.get("child_fetcher") or "HTML (genérico)"
        proposals = []
        for grupo, vals in sorted(grupos.items()):
            tp = dict(base)
            tp["search_field_values"] = ",".join(str(v) for v in vals)
            proposals.append({
                "suggested_name": grupo[:200],
                "matched_urls": [],
                "file_types": {},
                "confidence": 0.95,
                "target_fetcher_code": child,
                "target_params": tp,
            })
        self.profile_stats = {"total_files": len(proposals),
                              "grupos": len(grupos), "valores": len(valores)}
        logger.info(f"[pivote] {len(proposals)} grupo(s) -> {len(proposals)} hijo(s).")
        return proposals

