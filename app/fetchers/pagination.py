"""Categoría de variación: PAGINACIÓN.

Aísla "cómo se recorre el conjunto" como un vocabulario de estrategias con nombre,
compartido por cualquier fetcher sobre HTTP (REST, ATOM…). Una variante elige una
estrategia y aporta su sub-bloque de parámetros; el fetcher genérico la conduce.

Cada estrategia expone:
  first()      -> RequestSpec        (primera petición)
  following(*, last_batch_size, meta) -> RequestSpec | None   (siguiente o fin)

donde RequestSpec = {"url": str, "query": dict} y `meta` lleva señales de la última
respuesta (p. ej. {"next_link": ...} para rel_next, {"next_cursor": ...} para cursor).

El registro es PURO (no hace HTTP): decide qué pedir a continuación a partir del
estado y de las señales de la última respuesta. Esto lo hace testeable y reusable.
"""
from typing import Any, Dict, List, Optional

RequestSpec = Dict[str, Any]


class PaginationStrategy:
    name = "base"

    def __init__(self, url: str, params: Dict[str, Any]):
        self.url = url
        self.params = params or {}
        self.max_pages = int(self.params.get("max_pages", 0) or 0)
        self._page = 0

    def _limite_paginas(self) -> bool:
        return bool(self.max_pages and self._page >= self.max_pages)

    def first(self) -> RequestSpec:
        self._page = 1
        return {"url": self.url, "query": {}}

    def following(self, *, last_batch_size: int, meta: Optional[Dict[str, Any]] = None) -> Optional[RequestSpec]:
        return None


class NoPagination(PaginationStrategy):
    name = "none"


class QueryOffset(PaginationStrategy):
    """Offset/límite por query-params (start_index, page_size). Para cuando una
    página devuelve menos de `page_size` (última) o se alcanza `max_pages`."""
    name = "query_offset"

    def __init__(self, url, params):
        super().__init__(url, params)
        self.start_param = params.get("start_param", "start_index")
        self.size_param = params.get("page_size_param", "page_size")
        self.page_size = int(params.get("page_size", 50))
        self._offset = 0

    def first(self):
        self._page = 1
        self._offset = 0
        return {"url": self.url, "query": {self.start_param: 0, self.size_param: self.page_size}}

    def following(self, *, last_batch_size, meta=None):
        if last_batch_size < self.page_size:
            return None
        if self._limite_paginas():
            return None
        self._offset += self.page_size
        self._page += 1
        return {"url": self.url, "query": {self.start_param: self._offset, self.size_param: self.page_size}}


class PageNumber(PaginationStrategy):
    """Número de página incremental (page=N) hasta página vacía o `max_pages`."""
    name = "page_number"

    def __init__(self, url, params):
        super().__init__(url, params)
        self.page_param = params.get("page_param", "page")
        self.size_param = params.get("page_size_param", "page_size")
        self.page_size = int(params.get("page_size", 50))
        self._n = int(params.get("start_page", 1))

    def first(self):
        self._page = 1
        self._n = int(self.params.get("start_page", 1))
        return {"url": self.url, "query": {self.page_param: self._n, self.size_param: self.page_size}}

    def following(self, *, last_batch_size, meta=None):
        if last_batch_size == 0 or last_batch_size < self.page_size:
            return None
        if self._limite_paginas():
            return None
        self._n += 1
        self._page += 1
        return {"url": self.url, "query": {self.page_param: self._n, self.size_param: self.page_size}}


class RelNext(PaginationStrategy):
    """Sigue el enlace 'next' de la respuesta (rel=next en ATOM, o un campo 'next'
    en JSON). El fetcher pasa el enlace en meta['next_link']."""
    name = "rel_next"

    def following(self, *, last_batch_size, meta=None):
        nxt = (meta or {}).get("next_link")
        if not nxt or self._limite_paginas():
            return None
        self._page += 1
        return {"url": nxt, "query": {}}


class Cursor(PaginationStrategy):
    """Cursor/token: la respuesta entrega el token de la siguiente página en
    meta['next_cursor']; se reenvía como query-param."""
    name = "cursor"

    def __init__(self, url, params):
        super().__init__(url, params)
        self.cursor_param = params.get("cursor_param", "cursor")

    def following(self, *, last_batch_size, meta=None):
        token = (meta or {}).get("next_cursor")
        if not token or self._limite_paginas():
            return None
        self._page += 1
        return {"url": self.url, "query": {self.cursor_param: token}}


class PivotLoop(PaginationStrategy):
    """Una petición por cada valor de una lista (p. ej. códigos de provincia).
    No es paginación en sentido estricto, pero es el mismo eje: 'cómo se recorre'."""
    name = "pivot_loop"

    def __init__(self, url, params):
        super().__init__(url, params)
        self.pivot_param = params.get("pivot_param", "id")
        valores = params.get("pivot_values", [])
        if isinstance(valores, str):
            crudo = valores.strip()
            try:
                # Formato canónico: JSON array (fidelidad con el antiguo RestLoopFetcher)
                import json as _json
                parsed = _json.loads(crudo)
                valores = parsed if isinstance(parsed, list) else [parsed]
            except (ValueError, TypeError):
                # Tolerancia: lista separada por comas
                valores = [v.strip() for v in crudo.split(",") if v.strip()]
        self.valores: List[Any] = list(valores)
        self._i = 0

    def first(self):
        self._i = 0
        if not self.valores:
            # Antes (RestLoopFetcher) había un default implícito de provincias INE;
            # en la especie genérica eso es un error de configuración: mejor avisar
            # que enviar una petición con '{pivot}' sin sustituir.
            raise ValueError(
                "pagination=pivot_loop requiere el parámetro 'pivot_values' "
                "(lista de valores a iterar; p. ej. códigos de provincia)"
            )
        v = self.valores[0]
        return {"url": self.url, "query": {self.pivot_param: v}, "pivot": v}

    def following(self, *, last_batch_size, meta=None):
        self._i += 1
        if self._i >= len(self.valores):
            return None
        v = self.valores[self._i]
        return {"url": self.url, "query": {self.pivot_param: v}, "pivot": v}


REGISTRO = {
    "none": NoPagination,
    "query": QueryOffset,        # alias histórico
    "query_offset": QueryOffset,
    "page_number": PageNumber,
    "rel_next": RelNext,
    "cursor": Cursor,
    "pivot_loop": PivotLoop,
}


def build(nombre: Optional[str], url: str, params: Dict[str, Any]) -> PaginationStrategy:
    """Construye la estrategia por nombre. Desconocida o vacía → sin paginación."""
    cls = REGISTRO.get((nombre or "none").lower(), NoPagination)
    return cls(url, params)
