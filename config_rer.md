# Configuración para Entidades Religiosas RER con PaginatedHtmlFetcher

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

O manualmente:
```sql
INSERT INTO opendata.fetcher (id, code, class_path, description)
VALUES (
  gen_random_uuid(),
  'HTML_PAGINATED',
  'app.fetchers.paginated_html.PaginatedHtmlFetcher',
  'Buscadores HTML con paginación automática y selectores configurables'
);
```

### Paso 2: Configurar Resource
GraphQL Mutation:
```graphql
mutation {
  createResource(input: {
    name: "Entidades Religiosas RER"
    publisher: "Ministerio Justicia"
    targetTable: "entidades_religiosas"
    FetcherId: "ID_DEL_FETCHER_PAGINATED"
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