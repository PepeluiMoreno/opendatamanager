from functools import lru_cache
import importlib
import importlib.util
from typing import Dict, Optional
from app.models import Resource
from app.fetchers.base import BaseSpecies


class FetcherFactory:
    """
    Factory dinámica: instancia fetchers usando el class_path de la BD.
    Fallback a mapping estático para compatibilidad.
    """

    # Fallback estático por si el fetcher no tiene class_path en BD
    _FALLBACK = {
        "API REST": "app.fetchers.rest.RestFetcher",
        "HTML (genérico)": "app.fetchers.html_generic.HTMLFetcher",
    }

    @staticmethod
    def is_implemented(class_path: Optional[str], fetcher_code: Optional[str] = None) -> bool:
        """Predicado 'la especie tiene implementación': su class_path (o el
        fallback de su code) resuelve a una clase importable. Cacheado: coste
        cero en listados. Es el campo calculado 'implemented' del catálogo —
        distingue especies operativas de las matriculadas de forma aspiracional,
        sin depender de fechas de creación ni listas blancas."""
        cp = class_path or FetcherFactory._FALLBACK.get(fetcher_code or "")
        if not cp:
            return False
        return FetcherFactory._resolves(cp)

    @staticmethod
    @lru_cache(maxsize=256)
    def _resolves(class_path: str) -> bool:
        modulo, _, clase = class_path.rpartition(".")
        if not modulo or not clase:
            return False
        try:
            spec = importlib.util.find_spec(modulo)
        except (ImportError, ValueError, ModuleNotFoundError):
            return False
        if spec is None:
            return False
        try:
            mod = importlib.import_module(modulo)
        except Exception:
            return False
        return isinstance(getattr(mod, clase, None), type)

    @staticmethod
    def create_from_resource(resource: Resource, execution_params: Optional[Dict] = None) -> BaseSpecies:
        if not resource.active:
            raise ValueError(f"Resource '{resource.name}' está desactivado")

        if not resource.fetcher:
            raise ValueError(f"Resource '{resource.name}' no tiene fetcher asignado")

        # Obtener class_path: primero desde BD, luego fallback estático
        class_path = resource.fetcher.class_path
        if not class_path:
            class_path = FetcherFactory._FALLBACK.get(resource.fetcher.code)
        if not class_path:
            raise ValueError(
                f"Fetcher '{resource.fetcher.code}' no tiene class_path definido"
            )

        # Importar dinámicamente
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            fetcher_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"No se pudo cargar el fetcher '{class_path}': {e}"
            )

        # Orden de resolución: defaults de la clase → perfil (preset) elegido por
        # el RECURSO → params del recurso → de ejecución. El perfil vive bajo la
        # especie (FetcherPreset); fetcher.preset_params queda como fallback
        # transitorio de filas-variante aún no migradas.
        params_dict = FetcherFactory._build_defaults_dict(resource.fetcher.params_def)
        # Defaults globales (Ajustes): para las claves de ejecución conocidas, si el
        # recurso no las fija, se hereda el valor configurado en AppConfig. Quedan por
        # encima de los defaults de clase y por debajo del preset/recurso/ejecución.
        params_dict.update(FetcherFactory._global_exec_defaults(resource))
        preset = getattr(resource, "preset", None)
        if preset is not None and getattr(preset, "deleted_at", None) is None and preset.params:
            params_dict.update(preset.params)
        elif resource.fetcher.preset_params:
            params_dict.update(resource.fetcher.preset_params)
        # Hijos promovidos de un crawler Web Tree: si nadie inyectó _matched_urls
        # (p. ej. el botón Test o el arnés, que no pasan por el FetcherManager),
        # leerlos de su ResourceCandidate. Mantiene una sola semántica en todas
        # las vías de construcción.
        if getattr(resource, "parent_resource_id", None) and execution_params is not None                 and "_matched_urls" not in execution_params:
            try:
                from sqlalchemy.orm import object_session
                sess = object_session(resource)
                if sess is not None:
                    from app.models import ResourceCandidate as _RC
                    cand = (sess.query(_RC)
                            .filter(_RC.promoted_resource_id == resource.id,
                                    _RC.deleted_at.is_(None))
                            .order_by(_RC.detected_at.desc())
                            .first())
                    if cand is not None:
                        execution_params = dict(execution_params)
                        execution_params["_matched_urls"] = list(cand.matched_urls or [])
                        execution_params["_dimensions"] = list(cand.dimensions or [])
                        execution_params["_path_template"] = cand.path_template
            except Exception:  # noqa: BLE001 — la inyección es best-effort; sin candidata, el fetcher fallará con su mensaje claro
                pass
        elif getattr(resource, "parent_resource_id", None) and execution_params is None:
            execution_params = {}
            # reintentar por la rama anterior con dict vacío
            return FetcherFactory.create_from_resource(resource, execution_params)

        # Candado selectivo (§6c): los valores que la variante marca como
        # inviolables no son pisables por el recurso ni por la ejecución.
        bloqueados = set()
        if preset is not None and getattr(preset, "deleted_at", None) is None:
            bloqueados = set(getattr(preset, "locked_params", None) or [])
        for k, v in FetcherFactory._build_params_dict(resource.params).items():
            if k not in bloqueados:
                params_dict[k] = v
        if execution_params:
            for k, v in execution_params.items():
                if k not in bloqueados or k.startswith("_"):
                    params_dict[k] = v
        return fetcher_class(params_dict)

    # Claves de ejecución que pueden tener un default global en Ajustes (AppConfig).
    EXEC_DEFAULT_KEYS = (
        "num_workers", "max_concurrent_requests", "rate_limit_per_second",
        "request_delay_ms", "retry_attempts", "batch_size",
    )

    @staticmethod
    def _global_exec_defaults(resource) -> Dict[str, str]:
        """Lee de AppConfig los defaults globales de ejecución (si están fijados)."""
        try:
            from sqlalchemy.orm import object_session
            from app.models import AppConfig
            sess = object_session(resource)
            if sess is None:
                return {}
            rows = (sess.query(AppConfig)
                    .filter(AppConfig.key.in_(FetcherFactory.EXEC_DEFAULT_KEYS))
                    .all())
            return {r.key: str(r.value) for r in rows if r.value not in (None, "")}
        except Exception:  # noqa: BLE001 — best-effort; sin config global no cambia nada
            return {}

    @staticmethod
    def _build_defaults_dict(params_def: list) -> Dict[str, str]:
        result = {}
        for p in params_def:
            if p.default_value is not None:
                result[p.param_name] = str(p.default_value)
        return result

    @staticmethod
    def _build_params_dict(params: list) -> Dict[str, str]:
        return {param.key: param.value for param in params}
