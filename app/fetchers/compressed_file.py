"""
CompressedFileFetcher — Descarga un archivo comprimido y convierte su contenido en registros.

Soporta:
    zip      — archivo ZIP (extrae una entrada concreta o la única disponible)
    tar      — archivo TAR sin compresión
    tar.gz   — archivo TAR comprimido con gzip
    tar.bz2  — archivo TAR comprimido con bzip2
    gz       — fichero único comprimido con gzip (no TAR)

El contenido extraído se parsea con los mismos parsers que FileDownloadFetcher:
    csv | tsv | xlsx

Params configurables (ResourceParam):
    url           URL directa al archivo comprimido                 (obligatorio)
    format        Formato del archivo: zip | tar | tar.gz | tar.bz2 | gz  (obligatorio)
    entry         Nombre del fichero a extraer del archivo           (opcional si hay uno solo)
    inner_format  Formato del fichero extraído: csv | tsv | xlsx     (opcional, se infiere de la extensión)
    skip_rows     Filas a saltar antes de la cabecera (default: 0)
    delimiter     Separador CSV/TSV (default: auto-detect)
    encoding      Codificación CSV/TSV (default: utf-8-sig)
    sheet         Hoja XLSX: nombre o índice 0-based (default: 0)
    timeout       Timeout HTTP en segundos (default: 120)
    headers       Headers HTTP adicionales como JSON string
    batch_size    Registros por chunk yield (default: 1000)

Flujo:
    1. GET → archivo comprimido en memoria (BytesIO, sin tocar disco).
    2. Extracción de la entrada seleccionada.
    3. Parse del contenido extraído (csv/tsv/xlsx).
    4. Normalización de columnas: strip → lowercase → espacios/guiones → _ → sin no-ASCII.
    5. Yield en batches de batch_size registros como List[Dict[str, str]].
"""

import gzip
import io
import json
import logging
import tarfile
import zipfile
from typing import Generator, List, Dict, Any

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.file_parsers import infer_file_format, parse_structured_file

logger = logging.getLogger(__name__)

# Extensiones reconocidas para inferir inner_format
_EXT_TO_FORMAT = {
    ".csv":  "csv",
    ".tsv":  "tsv",
    ".txt":  "tsv",   # Geonames usa .txt con tabuladores
    ".xlsx": "xlsx",
    ".xls":  "xls",
    ".pdf":  "pdf",
}

# Modos de apertura de tarfile según formato
_TAR_MODES = {
    "tar":     "r:",
    "tar.gz":  "r:gz",
    "tar.bz2": "r:bz2",
}


def _extract_zip(content: bytes, entry: str) -> tuple[bytes, str]:
    """Extrae una entrada de un ZIP. Si entry está vacío, usa la única disponible."""
    zf = zipfile.ZipFile(io.BytesIO(content))
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not entry:
        if len(names) == 1:
            entry = names[0]
        else:
            raise ValueError(
                f"El ZIP contiene {len(names)} ficheros — especifica 'entry'. "
                f"Disponibles: {names}"
            )
    if entry not in zf.namelist():
        raise ValueError(f"Entrada '{entry}' no encontrada en el ZIP. Disponibles: {names}")
    return zf.read(entry), entry


def _extract_tar(content: bytes, mode: str, entry: str) -> tuple[bytes, str]:
    """Extrae una entrada de un TAR. Si entry está vacío, usa el único fichero regular."""
    tf = tarfile.open(fileobj=io.BytesIO(content), mode=mode)
    members = [m for m in tf.getmembers() if m.isfile()]
    if not entry:
        if len(members) == 1:
            entry = members[0].name
        else:
            names = [m.name for m in members]
            raise ValueError(
                f"El TAR contiene {len(members)} ficheros — especifica 'entry'. "
                f"Disponibles: {names}"
            )
    member = tf.getmember(entry)
    f = tf.extractfile(member)
    if f is None:
        raise ValueError(f"No se pudo extraer '{entry}' del TAR")
    return f.read(), entry


def _extract_gz(content: bytes) -> tuple[bytes, str]:
    """Descomprime un fichero .gz individual (no TAR)."""
    return gzip.decompress(content), ""


def _infer_inner_format(entry_name: str) -> str:
    """Infiere el formato del fichero extraído a partir de su extensión."""
    inferred = infer_file_format(entry_name)
    return inferred or ""


class CompressedFileFetcher(BaseFetcher):
    """
    Fetcher para archivos comprimidos (ZIP, TAR, TAR.GZ, TAR.BZ2, GZ).
    Extrae una entrada y la parsea con los mismos parsers que FileDownloadFetcher.
    """

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio")

        fmt = self.params.get("format", "").lower().strip()
        if not fmt:
            # Inferir del nombre del fichero
            for ext in ("tar.gz", "tar.bz2", "tar", "zip", "gz"):
                if url.lower().endswith(f".{ext}") or f".{ext}?" in url.lower():
                    fmt = ext
                    break
        if not fmt:
            raise ValueError("El parámetro 'format' es obligatorio. Valores: zip | tar | tar.gz | tar.bz2 | gz")

        entry      = self.params.get("entry", "").strip()
        inner_fmt  = self.params.get("inner_format", "").lower().strip()
        timeout    = int(self.params.get("timeout", 120))
        batch_size = int(self.params.get("batch_size", 1000))

        http_headers = self.params.get("headers", {})
        if isinstance(http_headers, str):
            http_headers = json.loads(http_headers)

        logger.info(f"[CompressedFileFetcher] Descargando {fmt.upper()}: {url}")
        response = self._request(None, "GET", url, headers=http_headers, timeout=timeout)
        response.raise_for_status()
        logger.info(f"[CompressedFileFetcher] Descargado — {len(response.content):,} bytes")

        # ── Extracción ────────────────────────────────────────────────────────
        if fmt == "zip":
            raw, used_entry = _extract_zip(response.content, entry)
        elif fmt == "gz":
            raw, used_entry = _extract_gz(response.content)
        elif fmt in _TAR_MODES:
            raw, used_entry = _extract_tar(response.content, _TAR_MODES[fmt], entry)
        else:
            raise ValueError(f"Formato '{fmt}' no soportado. Valores: zip | tar | tar.gz | tar.bz2 | gz")

        logger.info(f"[CompressedFileFetcher] Extraído '{used_entry}' — {len(raw):,} bytes")

        # ── Inferir inner_format si no se especificó ──────────────────────────
        if not inner_fmt and used_entry:
            inner_fmt = _infer_inner_format(used_entry)
        if not inner_fmt:
            raise ValueError(
                "No se pudo inferir 'inner_format'. Especifícalo como parámetro: pdf | xls | xlsx | csv | tsv"
            )

        logger.info(f"[CompressedFileFetcher] Parseando como '{inner_fmt}'")

        records = parse_structured_file(raw, inner_fmt, self.params, source_name=used_entry or url)

        total = len(records)
        logger.info(f"[CompressedFileFetcher] {total} registros parseados")

        for start in range(0, total, batch_size):
            yield records[start:start + batch_size]

        logger.info(f"[CompressedFileFetcher] Stream completado: {total} registros")

    def fetch(self) -> RawData:
        records = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    # ── Modo descubrir (Archivo como Colección) ───────────────────────────────
    _DATA_FORMATS = {"csv", "tsv", "xlsx", "xls", "json", "pdf"}

    def _resolve_fmt(self, url: str) -> str:
        fmt = self.params.get("format", "").lower().strip()
        if not fmt:
            for ext in ("tar.gz", "tar.bz2", "tar", "zip", "gz"):
                if url.lower().endswith(f".{ext}") or f".{ext}?" in url.lower():
                    fmt = ext
                    break
        if not fmt:
            raise ValueError("El parámetro 'format' es obligatorio. Valores: zip | tar | tar.gz | tar.bz2 | gz")
        return fmt

    def propose(self) -> List[Dict[str, Any]]:
        """Lista los miembros del archivo y emite un recurso-hijo por cada fichero
        de datos (csv/tsv/xlsx/xls/json/pdf). Cada hijo es un 'Compressed File' en
        modo extractor con su `entry` fijado. Salta directorios y ficheros no-datos
        (readmes, imágenes...). Un archivo de 1 solo miembro -> 1 candidato."""
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio")
        fmt = self._resolve_fmt(url)
        http_headers = self.params.get("headers", {})
        if isinstance(http_headers, str):
            http_headers = json.loads(http_headers)
        timeout = int(self.params.get("timeout", 120))

        logger.info(f"[CompressedFileFetcher] (descubrir) Descargando {fmt.upper()}: {url}")
        response = self._request(None, "GET", url, headers=http_headers, timeout=timeout)
        response.raise_for_status()
        content = response.content

        if fmt == "zip":
            members = [n for n in zipfile.ZipFile(io.BytesIO(content)).namelist() if not n.endswith("/")]
        elif fmt in _TAR_MODES:
            tf = tarfile.open(fileobj=io.BytesIO(content), mode=_TAR_MODES[fmt])
            members = [m.name for m in tf.getmembers() if m.isfile()]
        elif fmt == "gz":
            members = []   # gz = un único fichero, no es contenedor de varios
        else:
            raise ValueError(f"Formato '{fmt}' no soportado. Valores: zip | tar | tar.gz | tar.bz2 | gz")

        proposals: List[Dict[str, Any]] = []
        omitidos = 0
        for name in members:
            inner = _infer_inner_format(name)
            if inner not in self._DATA_FORMATS:
                omitidos += 1
                continue
            proposals.append({
                "suggested_name": name.rsplit("/", 1)[-1][:200],
                "matched_urls": [],
                "file_types": {inner: 1},
                "confidence": 0.95,
                "target_fetcher_code": "Compressed File",
                "target_params": {"url": url, "format": fmt, "entry": name, "inner_format": inner},
            })
        self.profile_stats = {"total_files": len(proposals), "miembros": len(members), "no_datos": omitidos}
        logger.info(f"[CompressedFileFetcher] (descubrir) {len(members)} miembro(s) -> "
                    f"{len(proposals)} de datos, {omitidos} omitidos.")
        return proposals

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
