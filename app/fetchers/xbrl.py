"""
XbrlFetcher — Fetcher genérico para ficheros XBRL (eXtensible Business Reporting Language).

Descarga un ZIP que contiene uno o varios documentos XML en formato XBRL y los
aplana en registros tabulares: un registro por elemento numérico con contexto.

El formato XBRL es un estándar de reporting financiero/contable (IFRS, PGCP, etc.)
utilizado por organismos como Banco de España, Tribunal de Cuentas, CNMV, SEC, etc.

Estructura de un documento XBRL:
    <xbrl xmlns="http://www.xbrl.org/2003/instance">
        <context id="c1">
            <period><instant>2023-12-31</instant></period>
            <!-- o <startDate>/<endDate> para periodos -->
        </context>
        <unit id="u1"><measure>iso4217:EUR</measure></unit>
        <!-- Elemento de dato: tag=código de cuenta, atributos=contexto+precisión -->
        <ifrs-full:Assets contextRef="c1" decimals="0" unitRef="u1">150000000</ifrs-full:Assets>
        ...
    </xbrl>

El ZIP puede contener varios ficheros XBRL (uno por estado contable).
La clave de clasificación de cada fichero es configurable vía params.

Params configurables (ResourceParam):
    url                 — URL del fichero ZIP (obligatorio)
    method              — HTTP verb (default: GET)
    query_params        — Query string params como JSON, ej: '{"nif":"P1102900A","ejercicio":"2023"}'
    headers             — HTTP headers adicionales como JSON
    timeout             — Timeout HTTP en segundos (default: 120)
    batch_size          — Registros por chunk (default: 200)

    # Selección de ficheros dentro del ZIP
    xml_pattern         — Glob/substring para filtrar ficheros XML dentro del ZIP
                          vacío = todos los .xml
    entry               — Nombre exacto de un único fichero XML a procesar
                          Si vacío, procesa todos los que coincidan con xml_pattern

    # Clasificación de ficheros → campo "estado_contable"
    # JSON: {"palabraclave": "etiqueta", ...}
    # Se aplica al nombre del fichero XML (lowercased, sin extensión)
    file_classifier     — JSON map de palabra_clave → etiqueta
                          Ej: '{"balance":"balance","liquidacion":"liquidacion","tesoreria":"tesoreria"}'
                          Si ninguna palabra encaja, se usa el nombre del fichero como etiqueta

    # Contexto adicional que se añade a todos los registros
    context_fields      — JSON map de campo → valor fijo, ej: '{"nif_entidad":"P1102900A","ejercicio":"2023"}'

    # Filtrado de cuentas
    account_prefix      — Prefijo(s) de tag a incluir, separados por coma
                          Ej: "ifrs-full:,local:" — vacío = todos los tags
    exclude_tags        — Tags de infraestructura XBRL a ignorar (separados por coma)
                          Default: "context,unit,schemaRef,roleRef,arcroleRef,linkbaseRef"

Registros producidos (un registro por elemento numérico):
    {
        # Contexto adicional (de context_fields)
        nif_entidad, ejercicio, ...
        # Del fichero y del elemento XBRL
        estado_contable, fichero_origen,
        codigo_cuenta, valor, moneda,
        fecha_contexto, tipo_contexto,   # "instant" | "period"
        fecha_inicio, fecha_fin,         # solo para tipo_contexto="period"
    }
"""

from __future__ import annotations

import fnmatch
import io
import json
import logging
import re
import zipfile
from typing import Any, Dict, Generator, List, Optional
from xml.etree import ElementTree as ET

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData

logger = logging.getLogger(__name__)

_DEFAULT_EXCLUDE = {"context", "unit", "schemaRef", "roleRef", "arcroleRef", "linkbaseRef"}


def _strip_ns(tag: str) -> str:
    """Elimina el namespace URI de un tag: {http://...}nombre → nombre"""
    m = re.match(r"\{[^}]+\}(.+)", tag)
    return m.group(1) if m else tag


def _full_tag(tag: str) -> str:
    """Devuelve el tag completo con namespace abreviado: {http://...}nombre → prefijo:nombre"""
    m = re.match(r"\{([^}]+)\}(.+)", tag)
    if m:
        ns, local = m.group(1), m.group(2)
        # Intenta derivar un prefijo legible del último segmento del namespace
        prefix = ns.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        return f"{prefix}:{local}"
    return tag


def _classify_file(filename: str, classifier: dict) -> str:
    """Clasifica un nombre de fichero según el mapa de palabras clave."""
    base = filename.lower().replace(".xml", "").replace("_", "").replace("-", "")
    for keyword, label in classifier.items():
        if keyword.lower().replace("-", "").replace("_", "") in base:
            return label
    # Fallback: nombre del fichero sin extensión
    return re.sub(r"\.(xml|xbrl)$", "", filename.lower(), flags=re.I)


class XbrlFetcher(BaseFetcher):
    """
    Fetcher genérico para ZIPs que contienen documentos XML en formato XBRL.
    Aplana los elementos numéricos con sus contextos en registros tabulares.
    """

    def fetch(self) -> RawData:
        url = self.params.get("url")
        if not url:
            raise ValueError("Param 'url' obligatorio para XbrlFetcher")

        method = self.params.get("method", "GET").upper()
        timeout = int(self.params.get("timeout", 120))
        headers = self._parse_json_param("headers", {"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"})
        query_params = self._parse_json_param("query_params", {})

        logger.info("[XBRL] Descargando ZIP desde %s", url)
        resp = self._request(None, method, url, params=query_params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        logger.info("[XBRL] Descargados %d bytes", len(resp.content))
        return resp.content  # bytes

    def parse(self, raw: RawData) -> ParsedData:
        """Extrae todos los XML del ZIP, filtra según params."""
        xml_pattern = self.params.get("xml_pattern", "").strip()
        entry = self.params.get("entry", "").strip()

        xml_files: Dict[str, bytes] = {}
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
            names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        except zipfile.BadZipFile as e:
            raise ValueError(f"Contenido no es un ZIP válido: {e}")

        for name in names:
            if entry and name != entry:
                continue
            if xml_pattern and not fnmatch.fnmatch(name.lower(), xml_pattern.lower()):
                continue
            xml_files[name] = zf.read(name)

        logger.info("[XBRL] %d ficheros XML seleccionados del ZIP (%d totales)", len(xml_files), len(names))
        return xml_files

    def normalize(self, parsed: ParsedData) -> DomainData:
        records = []
        for chunk in self._stream_parsed(parsed):
            records.extend(chunk)
        return records

    def stream(self) -> Generator[List[Dict], None, None]:
        raw = self.fetch()
        xml_files = self.parse(raw)
        yield from self._stream_parsed(xml_files)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stream_parsed(self, xml_files: Dict[str, bytes]) -> Generator[List[Dict], None, None]:
        batch_size = int(self.params.get("batch_size", 200))
        classifier = self._parse_json_param("file_classifier", {})
        context_fields = self._parse_json_param("context_fields", {})
        account_prefix_raw = self.params.get("account_prefix", "").strip()
        account_prefixes = [p.strip() for p in account_prefix_raw.split(",") if p.strip()] if account_prefix_raw else []
        exclude_raw = self.params.get("exclude_tags", ",".join(_DEFAULT_EXCLUDE))
        exclude_tags = {t.strip() for t in exclude_raw.split(",") if t.strip()}

        for filename, xml_bytes in xml_files.items():
            estado = _classify_file(filename, classifier)
            records = self._parse_xbrl_doc(
                xml_bytes, filename, estado, context_fields,
                account_prefixes, exclude_tags,
            )
            logger.info("[XBRL] %s → %s → %d registros", filename, estado, len(records))
            for i in range(0, len(records), batch_size):
                yield records[i:i + batch_size]

    def _parse_xbrl_doc(
        self,
        xml_bytes: bytes,
        filename: str,
        estado: str,
        context_fields: dict,
        account_prefixes: list,
        exclude_tags: set,
    ) -> List[Dict]:
        records: List[Dict] = []
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            logger.warning("[XBRL] XML parse error en %s: %s", filename, e)
            return records

        # ── Construir mapa de contextos ──────────────────────────────────────
        contexts: Dict[str, Dict] = {}
        for elem in root:
            local = _strip_ns(elem.tag)
            if local != "context":
                continue
            ctx_id = elem.get("id", "")
            ctx_info: Dict[str, Any] = {"tipo": "instant", "fecha": None, "fecha_inicio": None, "fecha_fin": None}
            for child in elem.iter():
                tag = _strip_ns(child.tag)
                if tag == "instant":
                    ctx_info["tipo"] = "instant"
                    ctx_info["fecha"] = (child.text or "").strip()
                elif tag == "startDate":
                    ctx_info["tipo"] = "period"
                    ctx_info["fecha_inicio"] = (child.text or "").strip()
                elif tag == "endDate":
                    ctx_info["fecha"] = (child.text or "").strip()
                    ctx_info["fecha_fin"] = (child.text or "").strip()
            contexts[ctx_id] = ctx_info

        # ── Extraer elementos numéricos ──────────────────────────────────────
        for elem in root:
            local = _strip_ns(elem.tag)
            if local in exclude_tags:
                continue

            ctx_ref = elem.get("contextRef", "")
            if not ctx_ref or not elem.text or not elem.text.strip():
                continue

            # Filtro opcional por prefijo de cuenta
            tag_full = _full_tag(elem.tag)
            if account_prefixes and not any(tag_full.startswith(p) for p in account_prefixes):
                continue

            try:
                raw_value = float(elem.text.strip())
            except ValueError:
                continue

            # Ajustar por decimals (factor de escala)
            decimals = elem.get("decimals", "0")
            try:
                dec = int(decimals)
                if dec != 0:
                    raw_value = raw_value * (10 ** dec)
            except (ValueError, TypeError):
                pass

            unit_ref = elem.get("unitRef", "")
            ctx = contexts.get(ctx_ref, {})

            record = {
                **context_fields,                         # campos fijos del resource
                "estado_contable": estado,
                "fichero_origen": filename,
                "codigo_cuenta": tag_full,
                "valor": raw_value,
                "moneda": unit_ref.replace("iso4217:", "") if unit_ref else "EUR",
                "fecha_contexto": ctx.get("fecha"),
                "tipo_contexto": ctx.get("tipo", "instant"),
                "fecha_inicio": ctx.get("fecha_inicio"),
                "fecha_fin": ctx.get("fecha_fin"),
            }
            records.append(record)

        return records

    # ── Utils ─────────────────────────────────────────────────────────────────

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
