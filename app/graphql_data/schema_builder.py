"""
schema_builder.py — Construye el schema GraphQL dinámico a partir de los datasets en BD.

Flujo:
    1. Se consultan todos los datasets con data_path válido (uno por resource: el más reciente).
    2. Por cada dataset se leen los primeros SAMPLE_SIZE registros del JSONL para inferir campos.
    3. Se genera un GraphQLObjectType por dataset y una query raíz con filtros y paginación.
    4. El schema resultante se pasa al engine para servir las peticiones GraphQL.

Convenciones de nombres:
    Resource name          → GraphQL type name     → GraphQL query name
    "PLACSP - Licitaciones"  → "PlacspLicitaciones"  → "placspLicitaciones"
    "BDNS - Concesiones"     → "BdnsConcesiones"      → "bdnsConcesiones"

Tipos de campo:
    Todos los campos son String por defecto. Los datos de los fetchers ya llegan
    normalizados como strings. En versiones futuras se puede inferir Int/Float
    inspeccionando los valores de la muestra.
"""

import json
import re
import os
from typing import Optional

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLArgument,
    GraphQLBoolean,
)

# Número de registros JSONL a leer para inferir el schema de un dataset.
# Un valor mayor da schemas más completos pero ralentiza el rebuild.
SAMPLE_SIZE = 200

# Campos que se excluyen del schema GraphQL por ser internos o demasiado grandes.
EXCLUDED_FIELDS = {"raw_xml_content", "raw_html", "_raw"}


def dataset_type_name(resource_name: str) -> str:
    """
    Convierte el nombre de un resource en un nombre de tipo GraphQL válido (PascalCase).

    Ejemplos:
        "PLACSP - Licitaciones Sector Público" → "PlacspLicitacionesSectorPublico"
        "BDNS - Concesiones de Subvenciones"   → "BdnsConcesionesDeSubvenciones"
    """
    # Normalizar: quitar acentos, separar por espacios/guiones/puntos
    name = resource_name
    # Reemplazar caracteres especiales comunes del español
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "ü": "u", "Ü": "U",
    }
    for src, dst in replacements.items():
        name = name.replace(src, dst)
    # Dividir en palabras
    words = re.split(r"[\s\-_./,;:]+", name)
    # PascalCase de cada palabra (saltando las vacías)
    return "".join(w.capitalize() for w in words if w)


def dataset_query_name(resource_name: str) -> str:
    """
    Convierte el nombre de un resource en un nombre de query GraphQL (camelCase).

    Ejemplos:
        "PLACSP - Licitaciones" → "placspLicitaciones"
        "BDNS - Concesiones"    → "bdnsConcesiones"
    """
    pascal = dataset_type_name(resource_name)
    if not pascal:
        return ""
    return pascal[0].lower() + pascal[1:]


def infer_fields(data_path: str) -> list[str]:
    """
    Lee los primeros SAMPLE_SIZE registros del JSONL y devuelve la lista de campos
    encontrados (en orden de aparición, sin duplicados, sin campos excluidos).

    Si el fichero no existe o está vacío devuelve lista vacía.
    """
    if not data_path or not os.path.exists(data_path):
        return []

    seen: dict[str, None] = {}  # dict mantiene orden de inserción (Python 3.7+)
    count = 0
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in record.keys():
                    if key not in EXCLUDED_FIELDS:
                        seen[key] = None
                count += 1
                if count >= SAMPLE_SIZE:
                    break
    except OSError:
        return []

    return list(seen.keys())


def _make_page_type(item_type: GraphQLObjectType) -> GraphQLObjectType:
    """
    Crea un tipo de paginación genérico para un item_type dado.

    Ejemplo: si item_type es "PlacspLicitaciones", devuelve "PlacspLicitacionesPage"
    con los campos:
        items  : [PlacspLicitaciones!]!   — registros de esta página
        total  : Int!                      — total de registros (sin aplicar limit/offset)
        limit  : Int!
        offset : Int!
    """
    return GraphQLObjectType(
        name=f"{item_type.name}Page",
        fields=lambda: {
            "items": GraphQLField(
                GraphQLNonNull(GraphQLList(GraphQLNonNull(item_type))),
                description="Registros de esta página.",
            ),
            "total": GraphQLField(
                GraphQLNonNull(GraphQLInt),
                description="Total de registros que cumplen los filtros (sin paginar).",
            ),
            "limit": GraphQLField(GraphQLNonNull(GraphQLInt)),
            "offset": GraphQLField(GraphQLNonNull(GraphQLInt)),
        },
    )


def _make_resolver(data_path: str, fields: list[str]):
    """
    Devuelve un resolver GraphQL para un dataset concreto.

    El resolver:
      1. Lee línea a línea el JSONL (sin cargarlo entero en memoria).
      2. Aplica filtros de igualdad (case-insensitive) para cada campo que
         se haya pasado como argumento en la query.
      3. Pagina con limit/offset.
      4. Devuelve un dict con {items, total, limit, offset}.

    Argumentos GraphQL disponibles:
        limit  : Int  (default 100, máximo 1000)
        offset : Int  (default 0)
        <campo>: String  por cada campo del dataset (filtro exacto, case-insensitive)
    """
    field_set = set(fields)

    def resolver(root, info, limit=100, offset=0, **filters):
        # Clamp limit para evitar respuestas gigantes
        limit = min(limit, 1000)
        offset = max(offset, 0)

        # Normalizar filtros: ignorar los None (campo no pasado)
        active_filters = {
            k: v.lower()
            for k, v in filters.items()
            if v is not None and k in field_set
        }

        matched = []
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Aplicar filtros
                    if active_filters:
                        match = all(
                            str(record.get(k, "") or "").lower() == v
                            for k, v in active_filters.items()
                        )
                        if not match:
                            continue

                    matched.append(record)
        except OSError:
            pass

        total = len(matched)
        page_items = matched[offset: offset + limit]

        # Proyectar solo los campos del schema (sin raw_xml_content etc.)
        projected = [
            {f: str(item.get(f) or "") for f in fields}
            for item in page_items
        ]

        return {"items": projected, "total": total, "limit": limit, "offset": offset}

    return resolver


def _build_dataset_info_type() -> GraphQLObjectType:
    """
    Tipo auxiliar DatasetInfo que expone metadatos de cada dataset disponible.
    Útil para que los consumidores descubran qué queries existen sin leer el SDL.
    """
    return GraphQLObjectType(
        name="DatasetInfo",
        description="Metadatos de un dataset disponible en la API.",
        fields={
            "queryName": GraphQLField(
                GraphQLNonNull(GraphQLString),
                description="Nombre de la query GraphQL para consultar este dataset.",
            ),
            "typeName": GraphQLField(
                GraphQLNonNull(GraphQLString),
                description="Nombre del tipo GraphQL de los registros.",
            ),
            "resourceName": GraphQLField(
                GraphQLNonNull(GraphQLString),
                description="Nombre del resource origen en ODMGR.",
            ),
            "recordCount": GraphQLField(
                GraphQLInt,
                description="Número de registros en el dataset.",
            ),
            "fields": GraphQLField(
                GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString))),
                description="Lista de campos disponibles para filtrar y proyectar.",
            ),
            "dataPath": GraphQLField(
                GraphQLString,
                description="Ruta al fichero JSONL en el servidor (solo para admins).",
            ),
        },
    )


def build_schema(db) -> tuple[GraphQLSchema, list[dict]]:
    """
    Construye el GraphQLSchema completo a partir de los datasets en BD.

    Algoritmo:
      - Para cada resource con al menos un dataset completado, toma el más reciente.
      - Infiere los campos del JSONL.
      - Genera un GraphQLObjectType + tipo paginación + resolver.
      - Añade la query raíz con todos los datasets + la query `datasets` de descubrimiento.

    Returns:
        (schema, dataset_registry)
        schema           — GraphQLSchema listo para ejecutar queries.
        dataset_registry — Lista de dicts con metadatos de cada dataset expuesto.
                          Se usa para servir la query `datasets`.

    Si no hay datasets disponibles devuelve un schema mínimo con solo la query `datasets`.
    """
    from app.models import Dataset, Resource

    # Un dataset por resource: el más reciente con data_path válido
    latest_by_resource: dict[str, Dataset] = {}
    all_datasets = (
        db.query(Dataset)
        .filter(Dataset.data_path.isnot(None))
        .order_by(Dataset.created_at.desc())
        .all()
    )
    for ds in all_datasets:
        rid = str(ds.resource_id)
        if rid not in latest_by_resource:
            latest_by_resource[rid] = ds

    dataset_info_type = _build_dataset_info_type()
    query_fields: dict[str, GraphQLField] = {}
    registry: list[dict] = []

    for rid, dataset in latest_by_resource.items():
        resource = db.query(Resource).filter(Resource.id == dataset.resource_id).first()
        if not resource:
            continue

        fields = infer_fields(dataset.data_path)
        if not fields:
            continue

        type_name = dataset_type_name(resource.name)
        query_name = dataset_query_name(resource.name)
        if not type_name or not query_name:
            continue

        # Tipo de item (todos los campos como String)
        item_type = GraphQLObjectType(
            name=type_name,
            description=f"Registro de '{resource.name}'.",
            fields={
                field: GraphQLField(
                    GraphQLString,
                    description=f"Campo '{field}' del dataset.",
                )
                for field in fields
            },
        )

        page_type = _make_page_type(item_type)
        resolver = _make_resolver(dataset.data_path, fields)

        # Argumentos de la query: limit, offset + un filtro por cada campo
        args = {
            "limit": GraphQLArgument(
                GraphQLInt,
                default_value=100,
                description="Número máximo de registros a devolver (máx. 1000).",
            ),
            "offset": GraphQLArgument(
                GraphQLInt,
                default_value=0,
                description="Número de registros a saltar (para paginación).",
            ),
        }
        for field in fields:
            args[field] = GraphQLArgument(
                GraphQLString,
                default_value=None,
                description=f"Filtro exacto (case-insensitive) por '{field}'.",
            )

        query_fields[query_name] = GraphQLField(
            GraphQLNonNull(page_type),
            args=args,
            resolve=resolver,
            description=(
                f"Consulta los registros de '{resource.name}'. "
                f"Filtra combinando cualquier campo como argumento."
            ),
        )

        registry.append({
            "queryName": query_name,
            "typeName": type_name,
            "resourceName": resource.name,
            "recordCount": dataset.record_count,
            "fields": fields,
            "dataPath": dataset.data_path,
        })

    # Query de descubrimiento: lista todos los datasets disponibles
    registry_snapshot = list(registry)  # captura para el closure del resolver
    query_fields["datasets"] = GraphQLField(
        GraphQLNonNull(GraphQLList(GraphQLNonNull(dataset_info_type))),
        description=(
            "Lista todos los datasets disponibles en esta API, con sus campos y "
            "el nombre de query para consultarlos."
        ),
        resolve=lambda root, info: registry_snapshot,
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name="Query",
            description="API GraphQL dinámica de OpenDataManager. Cada dataset extraído genera su propia query.",
            fields=query_fields,
        )
    )

    return schema, registry
