# Resource Bundle Import

## Problema que resuelve

Las aplicaciones cliente que usan opendatamanager como backend de datos necesitan declarar qué Resources quieren crear. La solución obvia —un script de seed en opendatamanager— acopla ambos proyectos: el seed conoce el dominio de la aplicación cliente y opendatamanager acaba sabiendo de JerezBudgetAPI, ChoS_graphql, etc.

La alternativa correcta es que cada aplicación cliente declare sus Resources en un fichero `resources.json` en su propio repositorio, y que opendatamanager los importe a través de su UI reutilizando las mutations GraphQL que ya existen.

---

## Cómo funciona

### 1. La aplicación cliente declara sus Resources

Cada aplicación cliente incluye un fichero `resources.json` en la raíz de su repositorio. El formato es una lista de objetos compatibles con `CreateResourceInput` — el mismo tipo que ya usa el formulario de creación manual en opendatamanager:

```json
[
  {
    "name": "nombre-unico-del-resource",
    "description": "Descripción legible",
    "fetcherCode": "Portal Documental",
    "active": true,
    "params": [
      { "key": "start_url", "value": "https://example.es/datos" },
      { "key": "file_link_selector", "value": "a[href$='.xlsx'], a[href$='.pdf']" }
    ]
  }
]
```

El campo `fetcherCode` es el código legible del fetcher (p.ej. `Portal Documental`, `File Download`, `API REST`). El UI lo resuelve a `fetcherId` usando los fetchers que ya tiene cargados en memoria.

### 2. El usuario importa desde el UI de opendatamanager

En la vista **Resources** hay un botón **"↑ Importar"**. Al pulsarlo:

1. Se abre el selector de fichero — el usuario elige `resources.json`
2. El UI parsea el JSON y resuelve `fetcherCode → fetcherId` localmente
3. Se abre un **modal de previsualización** con los resources que se van a crear, sus params y el fetcher resuelto. Si algún `fetcherCode` no existe en el sistema, se marca en rojo antes de confirmar
4. El usuario pulsa **"Importar"** — el UI llama a la mutation `createResource` por cada resource, en secuencia
5. El modal muestra el resultado: ✅ creado / ⏭ omitido (ya existía) / ❌ error

### 3. Idempotencia

Si un resource con el mismo `name` ya existe, se omite sin error. La importación puede ejecutarse varias veces de forma segura.

---

## Por qué no hay endpoint nuevo

El UI reutiliza la mutation GraphQL `createResource` que ya existe. No hay ningún endpoint específico de importación en opendatamanager — la lógica vive íntegramente en el frontend en `Resources.vue`. Esto significa:

- opendatamanager no conoce ningún formato de bundle propio
- No hay acoplamiento con ninguna aplicación cliente
- El mecanismo funciona con cualquier `resources.json` que siga el esquema de `CreateResourceInput`

---

## Formato completo de resources.json

```json
[
  {
    "name":        "string (required, único en opendatamanager)",
    "fetcherCode": "string (required, ej: Portal Documental, File Download, API REST)",
    "description": "string (optional)",
    "active":      "boolean (optional, default: true)",
    "publisherId": "uuid (optional, si el publisher ya existe en opendatamanager)",
    "params": [
      { "key": "string", "value": "string" }
    ]
  }
]
```

---

## Relación con los scripts de seed existentes

Los scripts de seed en `opendatamanager/scripts/` que crean Resources de dominio concreto (p.ej. `seed_osm.py`, `seed_fiscal.py`, `seed_dir3.py`) pueden migrarse progresivamente a `resources.json` en sus respectivos repositorios. El criterio para decidir cuáles migrar:

- **Migrar a resources.json**: seeds que solo crean Resources con sus params — sin lógica de transformación de datos
- **Mantener como seed**: seeds que además crean datos de referencia en BD (municipios, clasificaciones, etc.) que no son Resources

---

## Ejemplo real: JerezBudgetAPI

El fichero `resources.json` en la raíz de JerezBudgetAPI declara tres Resources para el módulo financiero. El usuario los importa una sola vez tras instalar opendatamanager. Para ejecutarlos por año, pasa `ejercicio` como `execution_param` en la UI o vía GraphQL:

```graphql
mutation {
  executeResource(id: "<uuid>", params: { ejercicio: "2024" })
}
```
