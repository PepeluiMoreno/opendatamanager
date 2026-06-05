# Configuración para Entidades Religiosas RER con PaginatedHtmlFetcher

Nota: este documento es una guía de caso de uso. No forma parte del catálogo inicial de despliegue. Si necesitas registrar o ajustar un fetcher, hazlo por la API de administración GraphQL, no con SQL directo.

## 🎯 RESUMEN DE LA SOLUCIÓN

### 1. Fetcher Recomendado
- **Tipo:** HTML_PAGINATED
- **Clase:** app.fetchers.paginated_html.PaginatedHtmlFetcher

### 2. Parámetros Obligatorios para el Recurso RER
```json
{
  "url": "https://maper.mjusticia.gob.es/Maper/buscarRER.action",
  "method": "POST",
  "rows_selector": "table tr",
  "has_header": true,
  "pagination_type": "form",
  "page_size": 10,
  "max_pages": 1500,
  "delay_between_pages": 2.0
}
```

### 3. Parámetros Opcionales Recomendados
```json
{
  "total_text_selector": ".total-resultados, .result-count, .mostrando-registros",
  "next_form_selector": "form[name='paginationForm'], .paginacion-form",
  "page_param": "pagina",
  "headers": "{\"User-Agent\": \"Mozilla/5.0 (compatible; OpenDataManager/1.0)\"}",
  "timeout": 30,
  "max_retries": 3,
  "error_selectors": ".error-message, .pagina-error",
  "clean_html": true,
  "field_transformations": "{\"Número\": \"trim\", \"Nombre\": \"trim\"}"
}
```

## 🔧 PASOS PARA CONFIGURAR

### Paso 1: Registrar Fetcher
Ejecutar cuando tengas el entorno activo:
```bash
python scripts/setup_paginated_fetcher.py
```

O manualmente vía GraphQL:
```graphql
mutation {
  createFetcher(input: {
    name: "HTML Paginated"
    classPath: "app.fetchers.paginated_html.PaginatedHtmlFetcher"
    description: "Buscadores HTML con paginación automática y selectores configurables"
  }) {
    id
    name
  }
}
```

### Paso 2: Configurar Resource
GraphQL Mutation:
```graphql
mutation {
  createResource(input: {
    name: "Entidades Religiosas RER"
    publisher: "Ministerio Justicia"
    targetTable: "entidades_religiosas"
    fetcherId: "ID_DEL_FETCHER_PAGINATED"
    active: true
    params: [
      {key: "url", value: "https://maper.mjusticia.gob.es/Maper/buscarRER.action"},
      {key: "method", value: "POST"},
      {key: "rows_selector", value: "table tr"},
      {key: "has_header", value: "true"},
      {key: "pagination_type", value: "form"},
      {key: "page_size", value: "10"},
      {key: "max_pages", value: "1500"},
      {key: "delay_between_pages", value: "2.0"},
      {key: "total_text_selector", value: ".total-resultados, .result-count, .mostrando-registros"},
      {key: "next_form_selector", value: "form[name='paginationForm'], .paginacion-form"},
      {key: "page_param", value: "pagina"},
      {key: "headers", value: "{\"User-Agent\": \"Mozilla/5.0 (compatible; OpenDataManager/1.0)\"}"}
    ]
  }) {
    id
    name
  }
}
```

## 📋 DESCRIPCIÓN DE PARÁMETROS CLAVE

### Paginación
- **pagination_type**: "form" (RER usa forms para paginar)
- **page_param**: "pagina" (nombre del parámetro en el form)
- **next_form_selector**: Selector CSS del form de paginación
- **page_size**: 10 (registros por página de RER)

### Extracción
- **rows_selector**: "table tr" (selecciona filas de tablas)
- **has_header**: true (primera fila contiene encabezados)
- **clean_html**: true (limpia HTML automáticamente)

### Performance
- **delay_between_pages**: 2.0 (2 segundos entre peticiones)
- **max_pages**: 1500 (límite de seguridad: 14836/10 ≈ 1484 páginas)

## ✅ VENTAJAS

- ✅ **Agnóstico al contenido**: Funciona para cualquier buscador HTML
- ✅ **Paginación automática**: Maneja links o forms automáticamente  
- ✅ **Configurable**: Selectores CSS ajustables por cada sitio
- ✅ **Robusto**: Reintentos, delays, manejo de errores
- ✅ **Reutilizable**: Para otros buscadores gubernamentales

## 🚀 PARA PROBAR

1. Inspeccionar HTML real de RER para ajustar selectores exactos
2. Probar con max_pages = 3 para validación
3. Aumentar a 1500 para extracción completa
4. Ejecutar recurso y monitorear progreso

Este fetcher puede extraer los 14,836 registros automáticamente del buscador RER.

---

## ⚠️ ESTADO 2026-06-05 (verificado en vivo)

El buscador (`maper.mjusticia.gob.es`, Struts2-jQuery) **ya no responde a POSTs
programáticos**: el envío del formulario `formBusqRER` (con sesión, con todos los
inputs, con criterios, e incluso como XHR) devuelve siempre el buscador
re-renderizado, sin resultados. El flujo de este documento (y por tanto los
recursos históricos de HTML Forms / HTML Paginated) **no funciona contra el sitio
actual**; la rotura es del lado de la fuente y anterior a la fusión de fetchers.

**Vía recomendada: Power BI público del Ministerio** (PowerBIFetcher). Verificado
en vivo: la `resource_key` documentada en el docstring de
`app/fetchers/powerbi.py` sigue siendo válida (el endpoint `querydata` la acepta y
valida el cuerpo). Falta el `query_json` (SemanticQuery) completo para montar el
recurso: recuperarlo de la configuración original o reconstruirlo descubriendo el
esquema del modelo.

La especie `HTML (genérico)` incorpora de todos modos `navigation=form_paged`
(paginación por re-envío de formulario, portada fielmente del fetcher antiguo y
con su parte pura testeada) para otros buscadores de la misma escuela que sí
admitan envío programático.
