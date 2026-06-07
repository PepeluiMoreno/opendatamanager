"""
Import/export de artefactos de ODM como manifiestos JSON declarativos.

Un manifiesto empaqueta lo necesario para levantar recursos: publisher + recursos
(fetcher por su `code`, schedule, params). Permite que quien construye una app
aporte fuentes y otras se beneficien.

REGLA DE SEGURIDAD INNEGOCIABLE: un manifiesto solo puede REFERENCIAR un fetcher
ya registrado (por `code`). Nunca acepta `class_path`, `fetcher_id`,
`publisher_id` ni `id`: importar no es ejecutar código arbitrario.

Política de gobernanza (opcional, soft-dependency): si el paquete de gobernanza
está disponible, se clasifica el origen y se exige que la clase esté admitida
(`ODM_ALLOWED_SOURCE_CLASSES`). Si no, el import funciona igual (rama independiente).
"""
import hashlib
import json
from typing import Any, Dict, List, Optional

MANIFEST_VERSION = 1

# Campos prohibidos en un recurso del manifiesto (evitan inyección de código/ids).
_FORBIDDEN_RESOURCE_KEYS = ("class_path", "fetcher_id", "publisher_id", "id")

# Soft-dependency con gobernanza: si existe, se aplica política de clases.
try:  # pragma: no cover - depende de si la rama de gobernanza está presente
    from app.governance.source_classification import admite as _admite, clasificar as _clasificar
except Exception:  # noqa: BLE001
    _admite = None
    _clasificar = None


def validate_manifest(manifest: Dict[str, Any], known_fetcher_codes) -> List[str]:
    """Valida un manifiesto. Devuelve lista de errores (vacía si es válido).

    Función pura: no toca BD. `known_fetcher_codes` es el conjunto de `code` de
    fetchers registrados.
    """
    errors: List[str] = []
    known = set(known_fetcher_codes or [])

    if not isinstance(manifest, dict):
        return ["El manifiesto debe ser un objeto JSON."]

    if manifest.get("odm_manifest_version") != MANIFEST_VERSION:
        errors.append(f"odm_manifest_version debe ser {MANIFEST_VERSION}.")

    pub = manifest.get("publisher")
    if not isinstance(pub, dict) or not pub.get("acronimo"):
        errors.append("Falta 'publisher.acronimo'.")

    resources = manifest.get("resources")
    if not isinstance(resources, list) or not resources:
        errors.append("'resources' debe ser una lista no vacía.")
        return errors

    for i, r in enumerate(resources):
        pref = f"resources[{i}]"
        if not isinstance(r, dict):
            errors.append(f"{pref}: debe ser un objeto.")
            continue
        if not r.get("name"):
            errors.append(f"{pref}: falta 'name'.")
        fcode = r.get("fetcher")
        if not fcode:
            errors.append(f"{pref}: falta 'fetcher' (code).")
        elif known and fcode not in known:
            errors.append(f"{pref}: fetcher '{fcode}' no está registrado.")
        if "preset" in r and not isinstance(r.get("preset"), str):
            errors.append(f"{pref}: 'preset' debe ser el código (string) de un perfil de la especie.")
        for forbidden in _FORBIDDEN_RESOURCE_KEYS:
            if forbidden in r:
                errors.append(f"{pref}: campo prohibido '{forbidden}' (no se inyecta código ni ids).")
        params = r.get("params", [])
        if params is not None and not isinstance(params, list):
            errors.append(f"{pref}: 'params' debe ser una lista.")
        else:
            for j, p in enumerate(params or []):
                if not isinstance(p, dict) or "key" not in p or "value" not in p:
                    errors.append(f"{pref}.params[{j}]: cada param necesita 'key' y 'value'.")
    return errors


def build_manifest(publisher, resources_with_fetchers) -> Dict[str, Any]:
    """Construye un manifiesto desde objetos del modelo (export). Función pura.

    `publisher`: objeto Publisher (o None).
    `resources_with_fetchers`: lista de (resource, fetcher, params_list).
    """
    res_out = []
    for resource, fetcher, params in resources_with_fetchers:
        res_out.append({
            "name": resource.name,
            "fetcher": fetcher.code if fetcher else None,
            "schedule": resource.schedule,
            "active": bool(resource.active),
            "params": [
                {"key": p.key, "value": p.value, "is_external": bool(getattr(p, "is_external", False))}
                for p in (params or [])
            ],
        })
    pub_out = None
    if publisher is not None:
        pub_out = {
            "acronimo": publisher.acronimo,
            "nombre": publisher.nombre,
            "nivel": publisher.nivel,
            "pais": getattr(publisher, "pais", None),
            "portal_url": getattr(publisher, "portal_url", None),
        }
    return {
        "odm_manifest_version": MANIFEST_VERSION,
        "publisher": pub_out,
        "resources": res_out,
    }


def template_manifest(fetcher_code, *, preset_code=None, preset_params=None,
                      locked_params=None, available_presets=None,
                      resource_name=None) -> Dict[str, Any]:
    """Esqueleto de manifiesto para que un humano lo rellene (export-as-template).

    Función pura: no toca BD. Toma el `code` del fetcher y, si se indica una
    variante, los params del preset (su bloque JSONB) y sus `locked_params`.
    Devuelve un manifiesto-plantilla con: publisher vacío, un recurso esqueleto,
    los params del preset como punto de partida (excluidos los bloqueados, que
    fija el propio preset) y un bloque `_plantilla` con instrucciones. El bloque
    `_plantilla` lo ignora el importador; el resto es importable una vez relleno.
    """
    preset_params = preset_params or {}
    locked = set(locked_params or [])

    def _val(v):
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)

    editable = [
        {"key": k, "value": _val(v), "is_external": False}
        for k, v in sorted(preset_params.items()) if k not in locked
    ]
    resource: Dict[str, Any] = {
        "name": resource_name or "<nombre único y descriptivo del recurso>",
        "fetcher": fetcher_code,
        "schedule": "<cron opcional, p. ej. 0 4 1 * *>",
        "active": True,
        "params": editable,
    }
    if preset_code:
        resource["preset"] = preset_code

    plantilla: Dict[str, Any] = {
        "fetcher": fetcher_code,
        "como_rellenar": [
            "Rellena 'publisher': 'acronimo' es obligatorio e identifica al organismo.",
            "Pon en el recurso un 'name' único por publisher.",
            "Completa los valores de 'params' (los presentes vienen del preset como "
            "punto de partida) y añade los que falten propios del recurso (p. ej. la URL raíz).",
            "Importa con la mutation importManifest; reimportar es idempotente "
            "(upsert por publisher+name).",
        ],
    }
    if preset_code:
        plantilla["preset"] = preset_code
    if locked:
        plantilla["params_fijados_por_preset"] = sorted(locked)
    if available_presets:
        plantilla["presets_disponibles"] = sorted(available_presets)
    plantilla["ver_tambien"] = (
        "query resourceManifest(id) exporta un recurso real como plantilla por ejemplo."
    )

    return {
        "odm_manifest_version": MANIFEST_VERSION,
        "_plantilla": plantilla,
        "publisher": {"acronimo": "", "nombre": "", "nivel": "MUNICIPAL",
                      "pais": "España", "portal_url": ""},
        "resources": [resource],
    }


def _policy_error(publisher_nivel: Optional[str], fetcher_code: Optional[str], clase_declarada: Optional[str]) -> Optional[str]:
    """Si la gobernanza está presente, devuelve un error si la clase no se admite."""
    if _admite is None:
        return None
    clase = clase_declarada
    if clase is None and _clasificar is not None:
        clase = _clasificar(publisher_nivel, fetcher_code)
    if not _admite(clase):
        return f"clase de origen '{clase}' no admitida por la política de la instancia."
    return None



def _canonical_params(params_iterables) -> List[Dict[str, Any]]:
    out = []
    for p in (params_iterables or []):
        if isinstance(p, dict):
            out.append({"key": p["key"], "value": p["value"], "is_external": bool(p.get("is_external", False))})
        else:
            out.append({"key": p.key, "value": p.value, "is_external": bool(p.is_external)})
    return sorted(out, key=lambda d: d["key"])


def canonical_resource(name, fetcher_code, schedule, active, params, preset_code=None) -> Dict[str, Any]:
    """Forma canónica determinista de UN recurso (base del hash/versionado).
    La clave 'preset' solo se incluye si el recurso usa un perfil, para no alterar
    el hash de los recursos que no lo usan."""
    canon = {
        "name": name,
        "fetcher": fetcher_code,
        "schedule": schedule,
        "active": bool(active),
        "params": _canonical_params(params),
    }
    if preset_code:
        canon["preset"] = preset_code
    return canon


def manifest_hash(canonical: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _canonical_from_db(session, resource) -> Dict[str, Any]:
    from app.models import Fetcher, FetcherPreset, ResourceParam
    fetcher = session.get(Fetcher, resource.fetcher_id) if resource.fetcher_id else None
    preset = session.get(FetcherPreset, resource.preset_id) if getattr(resource, "preset_id", None) else None
    params = session.query(ResourceParam).filter(ResourceParam.resource_id == resource.id).all()
    return canonical_resource(resource.name, fetcher.code if fetcher else None,
                              resource.schedule, resource.active, params,
                              preset_code=preset.code if preset else None)


def registrar_version(session, resource, origin: str, author: Optional[str] = None) -> Optional[str]:
    """Recalcula el canónico del recurso; si cambió, bumpea versión, escribe
    historial y actualiza hashes (la BD pasa a ser la nueva base de sync).
    Devuelve el hash nuevo, o None si no hubo cambios reales."""
    from app.models import ResourceManifestVersion
    canon = _canonical_from_db(session, resource)
    h = manifest_hash(canon)
    if resource.manifest_hash == h:
        return None
    resource.manifest_version = (resource.manifest_version or 0) + 1
    resource.manifest_hash = h
    resource.last_synced_hash = h
    resource.origin = origin
    session.add(ResourceManifestVersion(
        resource_id=resource.id, version=resource.manifest_version,
        manifest_json=canon, hash=h, origin=origin, author=author,
    ))
    return h


def import_manifest(session, manifest: Dict[str, Any], *, source: str = "manifest") -> Dict[str, Any]:
    """Importa un manifiesto (upsert idempotente). Devuelve un resumen.

    - Publisher: upsert por `acronimo`.
    - Resource: upsert por (publisher, name). Fetcher SOLO por `code` (rechaza
      desconocido). Params: se reemplazan por los del manifiesto.
    - Política de gobernanza aplicada si está disponible.
    """
    from uuid import uuid4
    from app.models import Publisher, Resource, ResourceParam, Fetcher

    known_codes = {f.code for f in session.query(Fetcher).all()}
    errors = validate_manifest(manifest, known_codes)
    if errors:
        return {"ok": False, "errors": errors, "created": 0, "updated": 0}

    pub_data = manifest["publisher"]
    publisher = (
        session.query(Publisher).filter(Publisher.acronimo == pub_data["acronimo"]).first()
    )
    if publisher is None:
        publisher = Publisher(
            id=uuid4(),
            acronimo=pub_data["acronimo"],
            nombre=pub_data.get("nombre") or pub_data["acronimo"],
            nivel=pub_data.get("nivel") or "ESTATAL",
            pais=pub_data.get("pais") or "España",
            portal_url=pub_data.get("portal_url"),
        )
        session.add(publisher)
        session.flush()

    created = updated = 0
    skipped: List[str] = []
    conflicts: List[str] = []
    db_ahead: List[str] = []
    autor = f"manifest:{source}"

    def _aplicar_params(resource, r):
        session.query(ResourceParam).filter(ResourceParam.resource_id == resource.id).delete()
        for p in (r.get("params") or []):
            session.add(ResourceParam(
                id=uuid4(), resource_id=resource.id,
                key=p["key"], value=p["value"], is_external=bool(p.get("is_external", False)),
            ))

    for r in manifest["resources"]:
        fetcher = session.query(Fetcher).filter(Fetcher.code == r["fetcher"]).first()
        if fetcher is None:
            skipped.append(f"{r.get('name')}: fetcher '{r.get('fetcher')}' no registrado")
            continue

        perr = _policy_error(publisher.nivel, r["fetcher"], r.get("clase_fuente"))
        if perr:
            skipped.append(f"{r.get('name')}: {perr}")
            continue

        preset = None
        if r.get("preset"):
            from app.models import FetcherPreset
            preset = (session.query(FetcherPreset)
                      .filter(FetcherPreset.fetcher_id == fetcher.id,
                              FetcherPreset.code == r["preset"],
                              FetcherPreset.deleted_at.is_(None)).first())
            if preset is None:
                skipped.append(f"{r.get('name')}: preset '{r['preset']}' no existe bajo '{fetcher.code}'")
                continue

        file_canon = canonical_resource(
            r["name"], fetcher.code, r.get("schedule"), r.get("active", True), r.get("params"),
            preset_code=preset.code if preset else None,
        )
        file_hash = manifest_hash(file_canon)

        resource = (
            session.query(Resource)
            .filter(Resource.publisher_id == publisher.id, Resource.name == r["name"])
            .first()
        )

        # Alta: el recurso nace del manifiesto.
        if resource is None:
            resource = Resource(
                id=uuid4(), name=r["name"], publisher=publisher.nombre,
                publisher_id=publisher.id, fetcher_id=fetcher.id,
                active=bool(r.get("active", True)), schedule=r.get("schedule"),
                preset_id=preset.id if preset else None,
                auto_generated=True, origin="manifest",
            )
            session.add(resource)
            session.flush()
            _aplicar_params(resource, r)
            session.flush()
            registrar_version(session, resource, origin="manifest", author=autor)
            from app.services.eventos import registrar_evento
            registrar_evento(session, "recurso.alta", resource.name, resource,
                             {"fetcher": fetcher.code, "source": source})
            created += 1
            continue

        # Detección a tres bandas: base (last_synced) vs fichero vs BD.
        db_hash = manifest_hash(_canonical_from_db(session, resource))
        base = resource.last_synced_hash

        if file_hash == db_hash:
            if base != file_hash:                      # alinear base sin tocar nada
                resource.last_synced_hash = file_hash
            continue                                    # ya en sync

        if base is None:
            # Recurso heredado sin base común: no pisar; requiere revisión.
            conflicts.append(f"{r['name']}: sin base de sync (recurso preexistente); revisar")
            continue

        file_cambiado = file_hash != base
        db_cambiado = db_hash != base

        if file_cambiado and not db_cambiado:
            # Solo cambió el fichero → aplicar.
            resource.fetcher_id = fetcher.id
            resource.preset_id = preset.id if preset else None
            resource.active = bool(r.get("active", resource.active))
            resource.schedule = r.get("schedule", resource.schedule)
            _aplicar_params(resource, r)
            session.flush()
            registrar_version(session, resource, origin="manifest", author=autor)
            updated += 1
        elif db_cambiado and not file_cambiado:
            # Solo cambió la BD → el fichero está obsoleto; no tocar.
            db_ahead.append(r["name"])
        else:
            # Ambos divergen → conflicto: no se pisa nada.
            from app.services.eventos import registrar_evento
            registrar_evento(session, "recurso.conflicto", r["name"], resource,
                             {"motivo": "divergencia fichero/BD"})
            conflicts.append(r["name"])

    session.commit()
    return {
        "ok": True, "created": created, "updated": updated,
        "skipped": skipped, "db_ahead": db_ahead, "conflicts": conflicts, "errors": [],
    }
