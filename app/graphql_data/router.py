"""
router.py — FastAPI router para el endpoint /graphql/data.

Monta un endpoint GraphQL estándar (compatible con GraphiQL y cualquier cliente
Apollo/urql/fetch) sobre el schema dinámico gestionado por `engine.py`.

Endpoints registrados:
    POST /graphql/data   — Ejecuta una query GraphQL (JSON body estándar)
    GET  /graphql/data   — Sirve GraphiQL (playground interactivo)

Formato de la petición POST:
    Content-Type: application/json
    {
        "query": "{ datasets { queryName fields } }",
        "variables": {},          # opcional
        "operationName": null     # opcional
    }

Formato de la respuesta:
    {
        "data":   { ... },        # resultado si no hay errores fatales
        "errors": [ ... ]         # lista de errores GraphQL (si los hay)
    }

Notas de diseño:
    - No usa Strawberry ni ningún framework de alto nivel — graphql-core puro.
    - El schema se lee de `engine.get_schema()` en cada petición, por lo que
      los cambios producidos por `engine.rebuild()` son inmediatos.
    - Se devuelve HTTP 200 incluso con errores parciales de GraphQL (convención
      estándar de la especificación GraphQL).
    - HTTP 503 si el schema no ha sido construido aún (arranque en frío).
    - HTTP 400 si la petición no tiene campo `query`.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.graphql_data import engine

router = APIRouter()

# ── GraphiQL HTML (playground ligero, sin dependencias CDN críticas) ──────────

_GRAPHIQL_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>GraphiQL — OpenDataManager Datasets</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { height: 100%; margin: 0; overflow: hidden; }
    #graphiql { height: 100vh; }
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphiql@3/graphiql.min.css" />
</head>
<body>
  <div id="graphiql">Loading...</div>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/react-dom@18/umd/react-dom.production.min.js"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/graphiql@3/graphiql.min.js"></script>
  <script>
    const fetcher = GraphiQL.createFetcher({ url: window.location.href });
    ReactDOM.createRoot(document.getElementById('graphiql')).render(
      React.createElement(GraphiQL, { fetcher })
    );
  </script>
</body>
</html>"""


# ── Rutas ─────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def graphiql():
    """Sirve el playground GraphiQL para explorar el schema de datasets."""
    return HTMLResponse(_GRAPHIQL_HTML)


@router.post("")
@router.post("/")
async def graphql_endpoint(request: Request):
    """
    Punto de entrada GraphQL estándar para consultas sobre datasets.

    El schema se reconstruye automáticamente después de cada ejecución completada,
    por lo que siempre refleja los datasets más recientes sin reiniciar el servidor.

    Ejemplo de query de descubrimiento:
        { datasets { queryName resourceName fields recordCount } }

    Ejemplo de query de datos (sustituir 'placspLicitaciones' por el queryName real):
        {
          placspLicitaciones(limit: 10, estado: "ADJ") {
            total
            items { expediente estado organo objeto presupuesto_sin_iva }
          }
        }
    """
    schema = engine.get_schema()
    if schema is None:
        return JSONResponse(
            status_code=503,
            content={"errors": [{"message": "Schema de datos no disponible. El servidor está arrancando."}]},
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"errors": [{"message": "El cuerpo de la petición debe ser JSON válido."}]},
        )

    query = body.get("query")
    if not query:
        return JSONResponse(
            status_code=400,
            content={"errors": [{"message": "El campo 'query' es obligatorio."}]},
        )

    variables = body.get("variables") or {}
    operation_name = body.get("operationName")

    result = engine.execute(query, variables=variables)

    response: dict = {}
    if result.data is not None:
        response["data"] = result.data
    if result.errors:
        response["errors"] = [
            {"message": str(e), "locations": _fmt_locations(e), "path": getattr(e, "path", None)}
            for e in result.errors
        ]

    # HTTP 200 siempre (convención GraphQL spec) — los errores van en el body
    return JSONResponse(status_code=200, content=response)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_locations(error) -> list[dict] | None:
    locs = getattr(error, "locations", None)
    if not locs:
        return None
    return [{"line": loc.line, "column": loc.column} for loc in locs]
