# Feature: GraphQL API dinámica por Dataset

## Objetivo

Exponer cada dataset como un tipo GraphQL queryable con campos tipados, generado automáticamente a partir del schema inferido de los registros del dataset.

## Enfoque técnico

Endpoint separado `/graphql/data` basado en **`graphql-core`** (librería de bajo nivel sobre la que Strawberry está construido). No toca el endpoint `/graphql` existente (Strawberry, API de gestión).

## Arquitectura

```
/graphql        → Strawberry  (gestión: resources, executions, fetchers, etc.)
/graphql/data   → graphql-core (consulta de datasets, schema dinámico)
```

### Schema dinámico

Al crear/actualizar un dataset, se infiere el schema a partir de los primeros N registros del JSONL de staging:

```python
from graphql import GraphQLObjectType, GraphQLField, GraphQLString, GraphQLSchema, GraphQLList, GraphQLArgument, GraphQLInt

def build_dataset_type(dataset):
    fields = infer_fields(dataset)  # lee primeros 100 registros del JSONL
    return GraphQLObjectType(
        dataset.type_name,  # ej. "PlacspLicitaciones"
        {f: GraphQLField(GraphQLString) for f in fields}
    )

def build_schema(datasets):
    query_fields = {}
    for ds in datasets:
        ds_type = build_dataset_type(ds)
        query_fields[ds.query_name] = GraphQLField(
            GraphQLList(ds_type),
            args={
                'limit':  GraphQLArgument(GraphQLInt, default_value=100),
                'offset': GraphQLArgument(GraphQLInt, default_value=0),
                # filtros dinámicos por campo: organo, estado, anio...
            },
            resolve=make_resolver(ds)
        )
    return GraphQLSchema(GraphQLObjectType('Query', query_fields))
```

### Persistencia del schema

El SDL generado se guarda en la tabla `dataset` (columna `graphql_schema TEXT`) para no tener que reinferirlo en cada startup.

### Reconstrucción del schema

Cuando se completa una ejecución (`status=completed`), el `FetcherManager` llama a `DatasetSchemaBuilder.rebuild()` que actualiza el schema del endpoint dinámico.

## Campos de filtro

Cada tipo expone filtros por los campos presentes en sus registros. Ejemplo para PLACSP:

```graphql
query {
  placspLicitaciones(organo: "Ayuntamiento de Madrid", anio: "2025", limit: 50) {
    expediente
    estado
    objeto
    adjudicatario
    importe_adjudicacion
    fecha_adjudicacion
  }
}
```

## Implementación pendiente

1. `app/graphql_data/schema_builder.py` — inferencia de schema + construcción graphql-core
2. `app/graphql_data/resolvers.py` — resolvers genéricos que leen del JSONL con filtros
3. `app/graphql_data/router.py` — endpoint FastAPI `/graphql/data`
4. Migración: columna `graphql_schema` en tabla `dataset`
5. Hook en `FetcherManager.run()` post-completado para rebuild
6. Integración en `app/main.py`
