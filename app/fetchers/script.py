"""
app/fetchers/script.py

Fetcher genérico que carga dinámicamente un módulo Python externo
y delega la extracción en una función configurable.

El fetcher no conoce el dominio. El Resource aporta ese conocimiento
via params:

  script_module   (required) — módulo importable, p.ej.
                               "ChoS_graphql.ETL.extract.parser_deportes"
  function_name   (optional) — nombre de la función a llamar (default: "run")
  [resto de params] — se pasan tal cual a la función como dict

Contrato de la función del script:
  def run(params: dict) -> list[dict]:
      ...
      return [{"campo": valor, ...}, ...]

  - Recibe el dict completo de params del Resource (excepto script_module
    y function_name, que consume el fetcher).
  - Devuelve una lista de dicts con registros planos y serializables a JSON.
  - Si no hay datos, devuelve lista vacía (nunca None).
"""

import importlib
import logging
from typing import Any, List

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


class ScriptFetcher(BaseFetcher):
    """
    Fetcher genérico que delega la extracción en una función de un
    módulo Python externo, inyectado como parámetro del Resource.
    """

    # Params que consume el fetcher y no pasa al script
    _FETCHER_PARAMS = {"script_module", "function_name",
                       "num_workers", "max_retries", "retry_backoff",
                       "timeout", "_staging_path", "_resume_state"}

    def _load_function(self):
        """Carga dinámicamente la función del script externo."""
        module_path = self.params.get("script_module")
        if not module_path:
            raise ValueError(
                "ScriptFetcher requiere el parámetro 'script_module' "
                "(ej: 'ChoS_graphql.ETL.extract.parser_deportes')"
            )

        function_name = self.params.get("function_name", "run")

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ValueError(
                f"No se pudo importar el módulo '{module_path}': {e}. "
                f"Asegúrate de que el paquete está instalado o en PYTHONPATH."
            ) from e

        fn = getattr(module, function_name, None)
        if fn is None:
            raise ValueError(
                f"El módulo '{module_path}' no expone la función '{function_name}'."
            )
        if not callable(fn):
            raise ValueError(
                f"'{module_path}.{function_name}' existe pero no es callable."
            )

        logger.info(f"[ScriptFetcher] Cargado: {module_path}.{function_name}()")
        return fn

    def _script_params(self) -> dict:
        """Devuelve los params que se pasan al script (excluye los del fetcher)."""
        return {
            k: v for k, v in self.params.items()
            if k not in self._FETCHER_PARAMS
        }

    # ── Pipeline BaseFetcher ──────────────────────────────────────────────────

    def fetch(self) -> RawData:
        """Carga el módulo y ejecuta la función, devuelve los registros crudos."""
        fn = self._load_function()
        script_params = self._script_params()

        logger.info(f"[ScriptFetcher] Ejecutando con params: {list(script_params.keys())}")
        result = fn(script_params)

        if result is None:
            logger.warning("[ScriptFetcher] La función devolvió None; se usa lista vacía.")
            return []

        if not isinstance(result, list):
            raise TypeError(
                f"La función debe devolver una lista de dicts, "
                f"pero devolvió {type(result).__name__}."
            )

        logger.info(f"[ScriptFetcher] {len(result)} registros obtenidos.")
        return result

    def parse(self, raw: RawData) -> ParsedData:
        """
        El script ya devuelve datos estructurados.
        Validamos que sean dicts y descartamos los que no lo sean.
        """
        if not raw:
            return []

        clean = []
        skipped = 0
        for item in raw:
            if isinstance(item, dict):
                clean.append(item)
            else:
                skipped += 1

        if skipped:
            logger.warning(
                f"[ScriptFetcher] Se descartaron {skipped} registros "
                f"que no eran dicts."
            )

        return clean

    def normalize(self, parsed: ParsedData) -> DomainData:
        """
        Normalización de tipos para garantizar serialización JSON.
        Convierte None explícito, fechas y otros tipos a str/None.
        """
        normalized = []
        for record in parsed:
            norm = {}
            for k, v in record.items():
                if v is None:
                    norm[k] = None
                elif isinstance(v, (str, int, float, bool)):
                    norm[k] = v
                else:
                    # Fechas, enums, objetos custom → str
                    norm[k] = str(v)
            normalized.append(norm)
        return normalized


