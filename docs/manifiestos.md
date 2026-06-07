# Manifiestos de recursos (import/export JSON)

Un **manifiesto** es un JSON declarativo que empaqueta un publisher y sus recursos
(fetcher por `code`, schedule, params), para que quien construye una aplicación
aporte fuentes de datos abiertos y otras aplicaciones se beneficien.

## Formato

```json
{
  "odm_manifest_version": 1,
  "publisher": {
    "acronimo": "INE",
    "nombre": "Instituto Nacional de Estadística",
    "nivel": "ESTATAL",
    "pais": "España",
    "portal_url": "https://www.ine.es"
  },
  "resources": [
    {
      "name": "España - Municipios (INE)",
      "fetcher": "API REST",
      "schedule": "0 4 1 1 *",
      "active": true,
      "clase_fuente": "api_abierta",
      "params": [
        { "key": "url", "value": "https://servicios.ine.es/...", "is_external": false }
      ]
    }
  ]
}
```

## Reglas

- **Seguridad (innegociable):** un manifiesto solo puede **referenciar un fetcher
  ya registrado** por su `code`. Está **prohibido** incluir `class_path`,
  `fetcher_id`, `publisher_id` o `id`: importar no inyecta código ni ids.
- **Idempotente:** el publisher se reconcilia por `acronimo`; cada resource por
  `(publisher, name)`. Re-importar actualiza en vez de duplicar; los params se
  reemplazan por los del manifiesto.
- **Gobernanza (opcional):** si el paquete de gobernanza está presente, se
  clasifica el origen y se exige que la clase esté admitida
  (`ODM_ALLOWED_SOURCE_CLASSES`); `clase_fuente` del manifiesto se usa para esa
  política. Si la gobernanza no está, el import funciona igual.

## API (en `/graphql`, protegida por la auth del endpoint admin)

- Import: `mutation { importManifest(manifest: {...}) }` → `{ ok, created, updated, skipped, errors }`.
- Export: `query { resourceManifest(id: "<uuid>") }` → manifiesto del recurso, listo para re-importar.

La lógica pura (validación y construcción) vive en `app/services/manifests.py` y
está cubierta por `tests/services/test_manifests.py`.

## Plantilla (¿quién ayuda a escribir el manifiesto?)

Nadie debería escribir un manifiesto de memoria. El **preset es la plantilla**:
es un bloque de params con nombre para una especie de fetcher, definido una vez
por quien registra el fetcher. ODM expone dos formas de partir de él:

- **Plantilla en blanco (scaffold):**
  `query { manifestTemplate(fetcherCode: "Web Tree", presetCode: "Extracción de datos") }`
  devuelve un manifiesto-esqueleto: `publisher` vacío para rellenar, un recurso
  con el `fetcher` y el `preset` ya correctos, los **params del preset como punto
  de partida** (excluidos los `locked_params`, que fija el preset) y un bloque
  `_plantilla` con instrucciones. Ese bloque lo **ignora el importador**; el
  resto es importable en cuanto rellenas `publisher.acronimo`, el `name` y los
  params propios del recurso (p. ej. la URL raíz). Sin `presetCode` lista los
  presets disponibles del fetcher.

- **Plantilla por ejemplo (export):**
  `query { resourceManifest(id: "<uuid>") }` exporta un recurso **real y
  conocido-bueno** como manifiesto importable, con su preset. La mejor plantilla
  suele ser un recurso que ya funciona: se exporta y se ajusta.

> Nota honesta: los fetchers aún no declaran un **esquema formal de params**
> (tipo/requerido/ayuda por campo), así que la plantilla autocompleta lo que el
> preset sabe, no los params propios del recurso. Añadir ese esquema enriquecería
> la plantilla y es trabajo aparte.
