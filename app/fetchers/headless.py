"""Especie HeadlessFetcher — renderizado JS con navegador headless (Playwright).

Para fuentes cuyo dato solo existe tras ejecutar JavaScript: correos ofuscados
(Joomla "email cloaking", Cloudflare data-cfemail, reensamblado por script),
listados cargados por AJAX, etc. NO sustituye al HTML genérico: se reserva para
lo que requests no puede ver. Cosecha sobre HTTP real simulando una visita de
navegador (es directorio público).

Itera sobre una o varias URLs (`url` | `urls` JSON | `pivot_values`+`url_template`)
y, opcionalmente, da UN salto a páginas internas del mismo dominio cuyo enlace
contenga palabras clave (contacto, directorio, curia, secretaría, delegaciones…),
donde suelen vivir los correos. Extrae correos de tres formas, deduplicados:
  · enlaces mailto: (lo más fiable)
  · atributos data-cfemail (Cloudflare email protection, hex-encoded)
  · regex sobre el texto renderizado (opcional, off por defecto: propenso a ruido)

Emite un registro por (url_semilla, email): {url, email, fuente}.

Modo alternativo `extract=fields`: aplica field_selectors CSS sobre el DOM ya
renderizado y emite un registro por URL (como html_generic pero con JS).

Params:
    url | urls (JSON list) | url_template + pivot_values   semillas
    extract            "emails" (def.) | "fields"
    wait_until         load | domcontentloaded | networkidle (def. networkidle)
    page_timeout_ms    timeout de navegación (def. 45000)
    follow_keywords    CSV de palabras en enlaces a seguir 1 nivel
                       (def. "contacto,contact,directorio,curia,secretaria,delegacion,equipo,organigrama")
    max_follow         máx. subpáginas por semilla (def. 6); 0 = no seguir
    same_domain_only   true (def.): solo seguir enlaces del mismo dominio
    text_emails        incluir regex sobre texto (def. false)
    field_selectors    JSON {campo: css}  (extract=fields)
    headers            JSON cabeceras extra
    block_assets       true (def.): bloquea imágenes/fuentes/css para acelerar
    delay              segundos entre semillas (def. 0.5)
    max_urls           límite de semillas (0 = sin límite)
"""
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers import navigation as nav

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_DEF_KEYWORDS = "contacto,contact,directorio,curia,secretaria,delegacion,equipo,organigrama"


def _parse_json(v, default):
    if v is None or v == "":
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def _decode_cfemail(hexstr: str) -> Optional[str]:
    """Decodifica el atributo data-cfemail de Cloudflare (XOR con el primer byte)."""
    try:
        b = bytes.fromhex(hexstr)
        key = b[0]
        return "".join(chr(c ^ key) for c in b[1:])
    except Exception:
        return None


def _clean_mailto(href: str) -> Optional[str]:
    if not href:
        return None
    addr = href[7:] if href.lower().startswith("mailto:") else href
    addr = addr.split("?")[0].strip().strip(".,;").lower()
    return addr if _EMAIL_RE.fullmatch(addr) else None


class HeadlessFetcher(BaseFetcher):

    # ------------------------------------------------------------------
    def _seeds(self) -> List[str]:
        if self.params.get("urls"):
            urls = _parse_json(self.params["urls"], [])
        elif self.params.get("url"):
            urls = [self.params["url"]]
        else:
            tmpl = self.params.get("url_template", "")
            urls = [nav.build_url(tmpl, value=v) for v in nav.pivot_values(self.params)]
        urls = [u for u in (s.strip() for s in urls) if u.lower().startswith(("http://", "https://"))]
        mx = int(self.params.get("max_urls", 0) or 0)
        return urls[:mx] if mx else urls

    def _new_browser(self, p):
        return p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

    def _route_block(self, route):
        if route.request.resource_type in ("image", "media", "font", "stylesheet"):
            return route.abort()
        return route.continue_()

    def _emails_from_page(self, page, with_text: bool) -> Set[str]:
        found: Set[str] = set()
        for href in page.eval_on_selector_all(
                "a[href^='mailto:'], a[href^='MAILTO:']",
                "els => els.map(e => e.getAttribute('href'))") or []:
            m = _clean_mailto(href)
            if m:
                found.add(m)
        for hexv in page.eval_on_selector_all(
                "[data-cfemail]", "els => els.map(e => e.getAttribute('data-cfemail'))") or []:
            dec = _decode_cfemail(hexv or "")
            if dec and _EMAIL_RE.fullmatch(dec):
                found.add(dec.lower())
        if with_text:
            for m in _EMAIL_RE.findall(page.inner_text("body") or ""):
                found.add(m.lower())
        return found

    def _follow_targets(self, page, base: str, keywords: List[str], same_domain: bool, limit: int) -> List[str]:
        if limit <= 0 or not keywords:
            return []
        base_host = urlparse(base).netloc
        anchors = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.getAttribute('href'), text: (e.textContent||'')}))") or []
        out: List[str] = []
        seen: Set[str] = set()
        for a in anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            txt = (a.get("text") or "").lower()
            hay = href.lower()
            if not any(k in hay or k in txt for k in keywords):
                continue
            full = urljoin(base, href).split("#")[0]
            if same_domain and urlparse(full).netloc != base_host:
                continue
            if full in seen or full.rstrip("/") == base.rstrip("/"):
                continue
            seen.add(full)
            out.append(full)
            if len(out) >= limit:
                break
        return out

    def _harvest_emails_bfs(self, context, seed: str, *, keywords, same_domain, max_follow,
                            follow_depth, max_pages, wait_until, nav_timeout, text_emails) -> Set[str]:
        """Recorre en anchura desde la semilla siguiendo enlaces que casen con las
        palabras clave, hasta `follow_depth` niveles y `max_pages` páginas, y
        acumula los correos de cada página visitada."""
        emails: Set[str] = set()
        visited: Set[str] = set()
        queue: List[tuple] = [(seed, 0)]
        pages = 0
        while queue and pages < max_pages:
            url, depth = queue.pop(0)
            key = url.rstrip("/")
            if key in visited:
                continue
            visited.add(key)
            try:
                page = self._goto(context, url, wait_until, nav_timeout)
            except Exception:
                continue
            pages += 1
            try:
                emails |= self._emails_from_page(page, text_emails)
                if depth < follow_depth:
                    for t in self._follow_targets(page, url, keywords, same_domain, max_follow):
                        if t.rstrip("/") not in visited:
                            queue.append((t, depth + 1))
            finally:
                try:
                    page.close()
                except Exception:
                    pass
        return emails

    def _goto(self, context, url: str, wait_until: str, nav_timeout: int):
        """Abre una página nueva y navega de forma tolerante: documento cargado
        y, best-effort, espera a networkidle (para que el JS de cloaking inyecte
        los correos) sin colgarse si la web nunca queda inactiva."""
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
        if wait_until == "networkidle":
            try:
                page.wait_for_load_state("networkidle", timeout=min(8000, nav_timeout))
            except Exception:
                pass
        return page

    # ------------------------------------------------------------------
    def fetch(self) -> RawData:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "HeadlessFetcher requiere Playwright. Instala: "
                "pip install playwright && python -m playwright install chromium"
            ) from exc

        seeds = self._seeds()
        if not seeds:
            raise ValueError("HeadlessFetcher requiere 'url', 'urls' o 'url_template'+'pivot_values'")

        extract = (self.params.get("extract") or "emails").lower()
        wait_until = self.params.get("wait_until", "networkidle")
        nav_timeout = int(self.params.get("page_timeout_ms", 45000))
        keywords = [k.strip().lower() for k in str(self.params.get("follow_keywords", _DEF_KEYWORDS)).split(",") if k.strip()]
        max_follow = int(self.params.get("max_follow", 6) or 0)
        follow_depth = int(self.params.get("follow_depth", 1) or 1)
        max_pages = int(self.params.get("max_pages", 40) or 40)
        same_domain = str(self.params.get("same_domain_only", "true")).lower() not in ("false", "0", "no")
        text_emails = str(self.params.get("text_emails", "false")).lower() in ("true", "1", "yes", "si", "sí")
        block_assets = str(self.params.get("block_assets", "true")).lower() not in ("false", "0", "no")
        field_selectors = _parse_json(self.params.get("field_selectors"), {})
        ua = (self.params.get("headers") and _parse_json(self.params["headers"], {}).get("User-Agent")) or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        delay = float(self.params.get("delay", 0.5) or 0)
        preview = int(self.params.get("_preview_limit", 0) or 0)

        records: List[Dict[str, Any]] = []
        with sync_playwright() as p:
            browser = self._new_browser(p)
            context = browser.new_context(user_agent=ua)
            if block_assets:
                context.route("**/*", self._route_block)

            for i, seed in enumerate(seeds):
                if extract == "fields":
                    try:
                        page = self._goto(context, seed, wait_until, nav_timeout)
                    except Exception as exc:
                        logger.warning(f"[headless] no se pudo cargar {seed}: {str(exc)[:120]}")
                        if str(self.params.get("stop_on_error", "")).lower() in ("true", "1"):
                            raise
                        continue
                    rec = {"url": seed}
                    for field, sel in field_selectors.items():
                        try:
                            el = page.query_selector(sel)
                            rec[field] = (el.inner_text().strip() if el else None)
                        except Exception:
                            rec[field] = None
                    records.append(rec)
                    try:
                        page.close()
                    except Exception:
                        pass
                else:
                    emails = self._harvest_emails_bfs(
                        context, seed, keywords=keywords, same_domain=same_domain,
                        max_follow=max_follow, follow_depth=follow_depth, max_pages=max_pages,
                        wait_until=wait_until, nav_timeout=nav_timeout, text_emails=text_emails)
                    for em in sorted(emails):
                        records.append({"url": seed, "email": em, "fuente": "headless"})

                if preview and len(records) >= preview:
                    break
                if delay and i < len(seeds) - 1:
                    time.sleep(delay)

            context.close()
            browser.close()

        logger.info(f"[headless] {len(records)} registros de {len(seeds)} semillas")
        return records[:preview] if preview else records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
