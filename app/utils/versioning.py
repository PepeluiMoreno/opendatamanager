"""
Utilidades de versionado de datasets.

Versionado semántico basado en el diff de esquema JSON entre la versión previa
y la nueva. La política está documentada en docs/versionado_datasets.md.

Resumen de la política (determinista):
  - MAJOR (rotura): se elimina un campo, cambia el tipo de un campo, cambia su
    `format`, se estrecha un `enum` (se eliminan valores admitidos) o un campo
    deja de ser `required` (un consumidor podría dejar de encontrarlo).
  - MINOR (compatible hacia atrás): se añade un campo, se amplía un `enum`
    (nuevos valores) o un campo pasa a ser `required` (garantía más fuerte).
  - PATCH: sin cambios de esquema; solo cambian los datos.

El diff es recursivo: desciende en objetos anidados (`properties`) y en los
items de array (`items`), de modo que un cambio profundo ya no se clasifica por
error como PATCH.
"""
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:  # solo para anotaciones; evita arrastrar el engine de BD
    from app.models import Dataset


def compute_next_version(
    latest_dataset: "Optional[Dataset]",
    new_schema: Dict,
) -> Tuple[int, int, int]:
    """Compara esquemas y determina la siguiente versión (major, minor, patch)."""
    if not latest_dataset:
        return (1, 0, 0)

    old_schema = latest_dataset.schema_json or {}
    diff = compute_schema_diff(old_schema, new_schema)

    if diff["breaking_changes"]:
        return (latest_dataset.major_version + 1, 0, 0)
    elif diff["minor_changes"]:
        return (latest_dataset.major_version, latest_dataset.minor_version + 1, 0)
    else:
        return (
            latest_dataset.major_version,
            latest_dataset.minor_version,
            latest_dataset.patch_version + 1,
        )


def _props(schema: Dict) -> Dict:
    return (schema or {}).get("properties", {}) or {}


def _required(schema: Dict) -> set:
    return set((schema or {}).get("required", []) or [])


def _diff_field(path: str, old_field: Dict, new_field: Dict, acc: Dict) -> None:
    """Compara un campo (recursivo en objetos y arrays) y acumula cambios en `acc`."""
    old_field = old_field or {}
    new_field = new_field or {}

    old_type = old_field.get("type")
    new_type = new_field.get("type")
    if old_type != new_type:
        acc["type_changes"].append(path)
        return  # un cambio de tipo domina; no seguimos comparando estructura interna

    # Cambio de format (p. ej. date -> date-time)
    if old_field.get("format") != new_field.get("format"):
        acc["format_changes"].append(path)

    # Cambios de enum
    old_enum = old_field.get("enum")
    new_enum = new_field.get("enum")
    if old_enum is not None or new_enum is not None:
        old_set = set(old_enum or [])
        new_set = set(new_enum or [])
        if old_set - new_set:
            acc["enum_narrowed"].append(path)   # valores eliminados -> rotura
        if new_set - old_set:
            acc["enum_widened"].append(path)    # valores añadidos -> minor

    # Descenso recursivo en objetos anidados
    if new_type == "object" or "properties" in new_field:
        _diff_object(path, old_field, new_field, acc)

    # Descenso recursivo en items de array
    if new_type == "array":
        old_items = old_field.get("items", {})
        new_items = new_field.get("items", {})
        if isinstance(old_items, dict) and isinstance(new_items, dict):
            _diff_field(f"{path}[]", old_items, new_items, acc)


def _diff_object(prefix: str, old_obj: Dict, new_obj: Dict, acc: Dict) -> None:
    old_props = _props(old_obj)
    new_props = _props(new_obj)
    old_keys = set(old_props.keys())
    new_keys = set(new_props.keys())

    for name in sorted(new_keys - old_keys):
        acc["added_fields"].append(f"{prefix}.{name}" if prefix else name)
    for name in sorted(old_keys - new_keys):
        acc["removed_fields"].append(f"{prefix}.{name}" if prefix else name)

    for name in sorted(old_keys & new_keys):
        child_path = f"{prefix}.{name}" if prefix else name
        _diff_field(child_path, old_props[name], new_props[name], acc)

    # Cambios de obligatoriedad (requiredness)
    old_req = _required(old_obj)
    new_req = _required(new_obj)
    for name in sorted(old_req - new_req):
        if name in (old_keys & new_keys):
            acc["required_removed"].append(f"{prefix}.{name}" if prefix else name)
    for name in sorted(new_req - old_req):
        if name in (old_keys & new_keys):
            acc["required_added"].append(f"{prefix}.{name}" if prefix else name)


def compute_schema_diff(old_schema: Dict, new_schema: Dict) -> Dict:
    """Compara dos JSON Schema (recursivo) y devuelve el diff clasificado.

    Devuelve un dict con:
      added_fields, removed_fields, type_changes (compatibilidad con código previo)
      format_changes, enum_narrowed, enum_widened, required_added, required_removed
      breaking_changes (bool), minor_changes (bool)
    """
    acc: Dict[str, List[str]] = {
        "added_fields": [],
        "removed_fields": [],
        "type_changes": [],
        "format_changes": [],
        "enum_narrowed": [],
        "enum_widened": [],
        "required_added": [],
        "required_removed": [],
    }

    _diff_object("", old_schema or {}, new_schema or {}, acc)

    breaking = bool(
        acc["removed_fields"]
        or acc["type_changes"]
        or acc["format_changes"]
        or acc["enum_narrowed"]
        or acc["required_removed"]
    )
    minor = (not breaking) and bool(
        acc["added_fields"]
        or acc["enum_widened"]
        or acc["required_added"]
    )

    acc["breaking_changes"] = breaking
    acc["minor_changes"] = minor
    return acc


def version_satisfies_pin(version_string: str, pin: Optional[str]) -> bool:
    """¿La versión ``M.m.p`` satisface el pin de una suscripción?

    Formatos admitidos: "1.2.3" (exacto), "1.2.*" (cualquier patch de 1.2),
    "1.*" (cualquier minor de 1), "*"/None (cualquiera).
    """
    if not pin or pin.strip() == "*":
        return True
    v = version_string.split(".")
    p = pin.strip().split(".")
    for i, part in enumerate(p):
        if part == "*":
            return True
        if i >= len(v) or v[i] != part:
            return False
    return True
