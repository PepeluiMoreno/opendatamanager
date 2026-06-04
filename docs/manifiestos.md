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
