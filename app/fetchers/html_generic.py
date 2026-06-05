"""Especie genérica HTMLFetcher.

Una sola clase para scraping HTML sobre HTTP. Las peculiaridades se delegan en los
registros de categorías de variación:
  - navegación (`navigation`): single | paged | pivot | form_pivot
  - extracción (`extraction`):  fields | table   (dialecto de selectores CSS)
  - construcción de la petición (`request`): query | form_submit
Absorbe HTML Forms (single), HTML Paginated (paged) y URL Loop HTML (pivot+paged).
La recursión por niveles y el árbol de directorios quedan como especies propias
(searchloop / web_tree): son tecnologías de descubrimiento genuinamente distintas.
"""
import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers import navigation as nav
from app.fetchers.html_extraction import extract_html
from app.fetchers.request_building import build_request

logger = logging.getLogger(__name__)


class HTMLFetcher(BaseFetcher):
    def fetch(self) -> RawData:
        mode = (self.params.get("navigation") or "single").lower()
        if mode == "form_pivot":
            return self._form_pivot()
        if mode == "form_paged":
            return self._form_paged()
        if mode == "pivot":
            return self._over_pivots(self._pivots())
        if mode == "paged":
            return self._over_pivots([None])
        return self._extract(self._get(self.params["url"]))

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed

    # --- helpers ---
    def _headers(self):
        h = self.params.get("headers", {})
        if isinstance(h, str):
            import json
            h = json.loads(h) if h.strip() else {}
        return {"User-Agent": "Mozilla/5.0 (ODM HTMLFetcher)", **h}

    def _get(self, url, pivot=None, method=None):
        rq = build_request(self.params.get("request", "query"), self.params, pivot=pivot)
        kwargs = {"headers": {**self._headers(), **rq.get("headers", {})},
                  "timeout": int(self.params.get("timeout", 30))}
        if rq.get("data") is not None:
            kwargs["data"] = rq["data"]
        if rq.get("json") is not None:
            kwargs["json"] = rq["json"]
        resp = self._request(None, method or rq["method"], url, **kwargs)
        resp.raise_for_status()
        return resp.text

    def _extract(self, html):
        return extract_html(self.params.get("extraction", "fields"), html, self.params)

    def _pivots(self):
        q = self.params.get("pivot_source_odmgr_query")
        if q:
            from app.fetchers.pivot_sources import pivots_from_odmgr
            return pivots_from_odmgr(self.params)
        return nav.pivot_values(self.params)

    def _over_pivots(self, pivots):
        template = self.params.get("url_template") or self.params.get("url")
        next_sel = self.params.get("next_page_selector")
        next_attr = self.params.get("next_page_attr", "href")
        max_pages = int(self.params.get("max_pages", 500))
        delay = float(self.params.get("delay_between_pages", self.params.get("delay", 1.0)) or 0)
        max_records = int(self.params.get("max_records", 0) or 0)
        preview = int(self.params.get("_preview_limit", 0) or 0)
        paged_template = "{page}" in (template or "")
        all_records = []
        for value in pivots:
            page = int(self.params.get("start_page", 1))
            url = nav.build_url(template, value=value, page=page) if (value is not None or paged_template) else template
            visited = 0
            while url and visited < max_pages:
                html = self._get(url, pivot=value)
                batch = self._extract(html)
                all_records.extend(batch)
                visited += 1
                if (preview and len(all_records) >= preview) or (max_records and len(all_records) >= max_records):
                    return all_records[:preview] if preview else all_records
                nxt = None
                if next_sel:
                    nxt = nav.next_link(html, next_sel, attr=next_attr, base_url=url)
                    if nxt == url:
                        nxt = None
                elif paged_template and batch:
                    page += 1
                    nxt = nav.build_url(template, value=value, page=page)
                if nxt and delay:
                    time.sleep(delay)
                url = nxt
        return all_records

    def _form_pivot(self):
        landing = self._get(self.params["url"], method="GET")
        soup = BeautifulSoup(landing, "html.parser")
        form = soup.select_one(self.params.get("form_selector", "form")) or soup
        hidden = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name and (inp.get("type") in ("hidden", None) or inp.get("type") == "hidden"):
                hidden[name] = inp.get("value", "") or ""
        action = form.get("action") if hasattr(form, "get") else None
        from urllib.parse import urljoin
        target = urljoin(self.params["url"], action) if action else self.params["url"]
        params = {**self.params, "form_hidden": hidden, "request": "form_submit"}
        all_records = []
        for value in self._pivots():
            rq = build_request("form_submit", params, pivot=value)
            resp = self._request(None, rq["method"], target,
                                 headers=self._headers(), data=rq["data"],
                                 timeout=int(self.params.get("timeout", 30)))
            resp.raise_for_status()
            all_records.extend(self._extract(resp.text))
            d = float(self.params.get("delay", 0) or 0)
            if d:
                time.sleep(d)
        return all_records


    def _form_paged(self):
        """Paginación por re-envío de formulario con sesión (cookies/estado).
        Fiel al antiguo PaginatedHtmlFetcher pagination_type=form: primera petición
        con el método configurado; después, POST del formulario de paginación con
        page_param incrementado hasta agotar formulario, páginas vacías o max_pages."""
        import requests as _rq
        url = self.params["url"]
        session = _rq.Session()
        method = (self.params.get("method", "GET") or "GET").upper()
        timeout = int(self.params.get("timeout", 30))
        max_pages = int(self.params.get("max_pages", 500))
        delay = float(self.params.get("delay_between_pages", self.params.get("delay", 1.0)) or 0)
        page_param = self.params.get("page_param", "pagina")
        selectors = self.params.get("next_form_selector") or "form"
        max_records = int(self.params.get("max_records", 0) or 0)
        preview = int(self.params.get("_preview_limit", 0) or 0)
        headers = self._headers()

        resp = self._request(session, method, url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        all_records = []
        page = 1
        while True:
            batch = self._extract(resp.text)
            all_records.extend(batch)
            if preview and len(all_records) >= preview:
                return all_records[:preview]
            if max_records and len(all_records) >= max_records:
                return all_records
            if page >= max_pages or (page > 1 and not batch):
                break
            siguiente = nav.form_next(resp.text, selectors, page_param=page_param, base_url=url)
            if not siguiente:
                break
            destino, inputs = siguiente
            if delay:
                time.sleep(delay)
            resp = self._request(session, "POST", destino or url, data=inputs,
                                 headers=headers, timeout=timeout)
            resp.raise_for_status()
            page += 1
        return all_records


HtmlGenericFetcher = HTMLFetcher
