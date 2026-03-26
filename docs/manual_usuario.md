# OpenDataManager — Manual de usuario

## ¿Qué es OpenDataManager?

OpenDataManager (ODMGR) es una plataforma de extracción y publicación de datos abiertos oficiales. Su función es conectarse periódicamente a fuentes de datos públicas —portales de contratación, bases de datos de subvenciones, registros administrativos— y transformar esa información heterogénea en datasets normalizados y accesibles.

Como consumidor de datos, lo que te interesa saber es esto: ODMGR hace el trabajo sucio de descarga, parseo y normalización por ti. Tú recibes los datos limpios, estructurados y siempre actualizados, sin necesidad de conocer los formatos originales ni los mecanismos de paginación de cada fuente.

---

## Conceptos básicos

**Resource** — una fuente de datos configurada en ODMGR. Por ejemplo, "PLACSP - Licitaciones" o "BDNS - Convocatorias de Subvenciones". Cada resource se extrae periódicamente según su programación.

**Dataset** — el resultado de una extracción. Cada vez que ODMGR ejecuta un resource, genera un dataset nuevo: un fichero con todos los registros normalizados, versionado y con metadatos. Los datasets son inmutables; las actualizaciones generan versiones nuevas.

**Application** — tu aplicación registrada en ODMGR. Registrarte como aplicación te permite suscribirte a resources y recibir notificaciones automáticas cuando hay datos nuevos.

---

## Dos formas de consumir datos

ODMGR ofrece dos mecanismos de consumo. Puedes elegir uno o usar ambos.

### Opción A — API GraphQL de datos

El endpoint `/graphql/data` expone todos los datasets disponibles como queries GraphQL. Es la forma más directa de consultar, filtrar y paginar datos sin necesidad de descargar ficheros completos.

#### Descubrir qué datasets hay disponibles

```graphql
{
  datasets {
    queryName
    resourceName
    recordCount
    fields
  }
}
```

La respuesta lista todos los datasets activos con el nombre de query que debes usar para consultarlos y los campos disponibles para filtrar.

#### Consultar un dataset

Usa el `queryName` devuelto por la query anterior. Por ejemplo, para el dataset de convocatorias de subvenciones del BDNS:

```graphql
{
  bdnsConvocatoriasDeSubvenciones(limit: 20, offset: 0) {
    total
    limit
    offset
    items {
      id
      descripcion
      fechaRecepcion
      nivel1
      nivel2
    }
  }
}
```

#### Filtrar por campo

Todos los campos del dataset están disponibles como filtros de igualdad (insensible a mayúsculas):

```graphql
{
  bdnsConvocatoriasDeSubvenciones(nivel1: "ESTADO", limit: 50) {
    total
    items {
      id
      descripcion
      nivel2
      codigoInvente
    }
  }
}
```

Puedes combinar varios filtros a la vez. Todos se aplican como condición AND.

#### Paginación

Usa `limit` y `offset` para paginar. El campo `total` siempre devuelve el número de registros que cumplen los filtros, independientemente de la paginación.

```graphql
{
  placspLicitaciones(limit: 100, offset: 200, estado: "ADJ") {
    total
    items {
      expediente
      organo
      objeto
      presupuesto_sin_iva
      importe_adjudicacion
      adjudicatario
    }
  }
}
```

El límite máximo por petición es **1000 registros**.

#### Playground interactivo

Abre `/graphql/data` en el navegador para acceder a GraphiQL, el playground interactivo donde puedes explorar el schema, autocompletar campos y probar queries directamente.

#### Desde código

```python
import requests

response = requests.post(
    "https://tu-odmgr/graphql/data",
    json={
        "query": """
        {
          bdnsConvocatoriasDeSubvenciones(limit: 100, nivel1: "CCAA") {
            total
            items { id descripcion nivel1 nivel2 fechaRecepcion }
          }
        }
        """
    }
)
data = response.json()["data"]["bdnsConvocatoriasDeSubvenciones"]
print(f"{data['total']} registros encontrados")
for item in data["items"]:
    print(item["descripcion"])
```

```javascript
const response = await fetch('https://tu-odmgr/graphql/data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: `{
      bdnsConvocatoriasDeSubvenciones(limit: 100, nivel1: "CCAA") {
        total
        items { id descripcion nivel1 nivel2 fechaRecepcion }
      }
    }`
  })
})
const { data } = await response.json()
```

---

### Opción B — Descarga de dataset completo (JSONL + webhook)

Si necesitas cargar el dataset completo en tu propia base de datos o sistema de archivos, ODMGR puede notificarte automáticamente cada vez que hay una nueva versión disponible y darte la URL de descarga.

#### Cómo funciona

1. Registras tu aplicación en ODMGR y configuras un endpoint receptor (webhook URL).
2. Te suscribes a los resources que te interesan.
3. Cada vez que ODMGR completa una extracción, envía un POST a tu endpoint con los metadatos del nuevo dataset y la URL de descarga.
4. Tu aplicación descarga el fichero `.jsonl` e importa los datos.

#### Formato del webhook

```json
{
  "event": "dataset.published",
  "dataset": {
    "id": "4ca73f20-7b1f-4fa0-b2da-942c593fb311",
    "resource_name": "BDNS - Convocatorias de Subvenciones",
    "version": "3.0.0",
    "created_at": "2026-03-26T12:00:00",
    "record_count": 618709,
    "checksum": "sha256:abc123..."
  },
  "schema_diff": {
    "added_fields": [],
    "removed_fields": [],
    "breaking_changes": []
  },
  "download_urls": {
    "data":     "/api/datasets/{id}/data.jsonl",
    "schema":   "/api/datasets/{id}/schema.json",
    "models":   "/api/datasets/{id}/models.py",
    "metadata": "/api/datasets/{id}/metadata.json"
  }
}
```

El campo `schema_diff` indica si el schema ha cambiado respecto a la versión anterior: campos nuevos (minor), campos eliminados o renombrados (major). Esto te permite decidir si tu ETL necesita adaptarse antes de importar.

#### Fichero de datos: formato JSONL

El fichero `data.jsonl` contiene un registro JSON por línea:

```json
{"id":"125902","descripcion":"Concessió directa nominativa","fechaRecepcion":"2011-03-05","nivel1":"CCAA","nivel2":"GENERALITAT DE CATALUNYA"}
{"id":"125903","descripcion":"Programa de becas investigación","fechaRecepcion":"2011-03-06","nivel1":"ESTADO","nivel2":"MINISTERIO DE CIENCIA"}
```

```python
import json, requests

# Recibido en tu webhook:
download_url = "/api/datasets/4ca73f20.../data.jsonl"

with requests.get(f"https://tu-odmgr{download_url}", stream=True) as r:
    for line in r.iter_lines():
        if line:
            record = json.loads(line)
            # importar a tu BD...
```

#### Verificación de integridad

El webhook incluye el checksum SHA-256 del fichero. Úsalo para verificar que la descarga es íntegra antes de importar:

```python
import hashlib

sha256 = hashlib.sha256()
with open("data.jsonl", "rb") as f:
    for chunk in iter(lambda: f.read(8192), b""):
        sha256.update(chunk)

assert sha256.hexdigest() == dataset["checksum"].replace("sha256:", "")
```

#### Versionado semántico

Cada dataset tiene versión `MAJOR.MINOR.PATCH`:

| Tipo | Cuándo ocurre | Qué implica |
|------|---------------|-------------|
| `PATCH` | Solo cambian los datos, no el schema | Importación directa, sin cambios en tu modelo |
| `MINOR` | Se añaden campos nuevos | Tu modelo puede ignorarlos o adoptarlos |
| `MAJOR` | Se eliminan o renombran campos | Revisa tu ETL antes de importar |

Puedes configurar la política `auto_upgrade` de tu suscripción para recibir notificaciones solo cuando el cambio supere un umbral: `patch` (solo cambios de datos), `minor` (datos + campos nuevos), o `major` (cualquier cambio).

---

## Registrar tu aplicación

1. Entra en la interfaz de ODMGR → sección **Applications**.
2. Crea una nueva aplicación con nombre, descripción y la ruta donde se generarán los modelos SQLAlchemy de cada dataset.
3. Elige el **modo de consumo**:
   - **webhook** — recibirás notificaciones push con URL de descarga del JSONL completo.
   - **graphql** — recibirás notificaciones ligeras indicando que hay datos nuevos en la API GraphQL.
   - **both** — recibirás ambos tipos de notificación.
4. Si usas webhook, configura tu `webhook_url` y `webhook_secret` (usado para verificar la firma HMAC de los mensajes).
5. Ve a **Resources** y suscríbete a los datasets que necesitas.

### Verificación de firma HMAC

Cada webhook lleva la cabecera `X-ODM-Signature` con un HMAC-SHA256 del cuerpo. Verifica siempre la firma antes de procesar el mensaje:

```python
import hmac, hashlib, json

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# En tu endpoint receptor:
@app.post("/webhook/odmgr")
async def receive(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-ODM-Signature", "")
    if not verify_signature(body, sig, ODMGR_WEBHOOK_SECRET):
        raise HTTPException(status_code=401)
    payload = json.loads(body)
    # procesar...
```

---

## Comparativa rápida

| | GraphQL (`/graphql/data`) | Descarga JSONL (webhook) |
|---|---|---|
| **Cuándo usarlo** | Consultas dinámicas, filtros, búsquedas | Carga completa en BD propia, ETL batch |
| **Volumen por llamada** | Hasta 1000 registros paginados | Dataset completo (cientos de miles de registros) |
| **Actualización** | Siempre refleja el dataset más reciente | Notificación push en cada nueva versión |
| **Infraestructura requerida** | Solo HTTP | Endpoint receptor accesible desde ODMGR |
| **Ideal para** | Dashboards, APIs derivadas, búsquedas puntuales | Réplica local, análisis offline, ML |

---

## Recursos disponibles actualmente

Para obtener la lista actualizada de todos los datasets disponibles, consulta:

```graphql
{
  datasets {
    queryName
    resourceName
    recordCount
    fields
  }
}
```

O visita el playground en `/graphql/data`.
