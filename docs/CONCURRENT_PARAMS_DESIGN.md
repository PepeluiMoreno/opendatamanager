# Diseño: Parámetros de Programación Concurrente

## Problema

Necesitamos controlar cómo los fetchers manejan:
- Concurrencia (múltiples requests simultáneas)
- Rate limiting (límite de requests por segundo)
- Reintentos (retry logic)
- Delays (espaciado entre requests)

## Solución: Dos niveles de configuración

### Nivel 1: Fetcher Type (Defaults globales)

Cada tipo de fetcher define parámetros opcionales con valores por defecto.

**Ventajas:**
- Defaults sensatos para todos los resources de ese tipo
- Se configuran una vez, aplican a todos
- Se pueden sobrescribir a nivel de resource

**Parámetros propuestos:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `max_concurrent_requests` | integer | 5 | Máximo de requests simultáneas |
| `rate_limit_per_second` | integer | 10 | Requests por segundo permitidas |
| `batch_size` | integer | 100 | Tamaño de lote para paginación |
| `request_delay_ms` | integer | 0 | Delay entre requests (milisegundos) |
| `retry_attempts` | integer | 3 | Intentos de reintento en caso de fallo |
| `retry_backoff_factor` | string | "2.0" | Factor de backoff exponencial |
| `timeout` | integer | 30 | Timeout por request (segundos) |
| `connection_pool_size` | integer | 10 | Tamaño del pool de conexiones |

### Nivel 2: Resource (Overrides específicos)

Cada resource puede sobrescribir estos valores según las necesidades de esa API específica.

**Ejemplo:**
```python
# Resource: BDNS (API tolerante)
params = {
    "url": "https://www.infosubvenciones.es/...",
    "method": "get",
    "query_params": "{...}",
    "rate_limit_per_second": "50",  # Override: API tolerante
    "max_concurrent_requests": "10",  # Override: permite más concurrencia
}

# Resource: INE (API restrictiva)
params = {
    "url": "https://servicios.ine.es/...",
    "method": "get",
    "rate_limit_per_second": "2",  # Override: API muy restrictiva
    "max_concurrent_requests": "1",  # Override: sin concurrencia
    "request_delay_ms": "1000",  # Override: 1s entre requests
}
```

## Implementación

### 1. Actualizar FetcherParams en base de datos

Los parámetros de concurrencia ya se definen en `type_fetcher_params`:

```sql
-- Ejemplo: Añadir parámetros de concurrencia al fetcher "API REST"
INSERT INTO opendata.type_fetcher_params (id, fetcher_id, param_name, data_type, required, default_value)
VALUES
    (gen_random_uuid(), '<fetcher_id>', 'max_concurrent_requests', 'integer', false, '5'),
    (gen_random_uuid(), '<fetcher_id>', 'rate_limit_per_second', 'integer', false, '10'),
    (gen_random_uuid(), '<fetcher_id>', 'batch_size', 'integer', false, '100'),
    (gen_random_uuid(), '<fetcher_id>', 'request_delay_ms', 'integer', false, '0'),
    (gen_random_uuid(), '<fetcher_id>', 'retry_attempts', 'integer', false, '3'),
    (gen_random_uuid(), '<fetcher_id>', 'retry_backoff_factor', 'string', false, '2.0'),
    (gen_random_uuid(), '<fetcher_id>', 'connection_pool_size', 'integer', false, '10');
```

### 2. Crear AsyncFetcher base

```python
# app/fetchers/async_fetcher.py

import asyncio
import time
from typing import List, Dict, Any
from abc import abstractmethod
import aiohttp
from app.fetchers.base import BaseFetcher, RawData, DomainData


class AsyncFetcher(BaseFetcher):
    """Base class for fetchers with concurrency control"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)

        # Concurrency params (with defaults)
        self.max_concurrent = int(params.get("max_concurrent_requests", 5))
        self.rate_limit = int(params.get("rate_limit_per_second", 10))
        self.batch_size = int(params.get("batch_size", 100))
        self.request_delay_ms = int(params.get("request_delay_ms", 0))
        self.retry_attempts = int(params.get("retry_attempts", 3))
        self.retry_backoff = float(params.get("retry_backoff_factor", 2.0))
        self.timeout = int(params.get("timeout", 30))

        # Rate limiting state
        self._request_times = []
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

    async def _rate_limit_wait(self):
        """Wait if necessary to respect rate limit"""
        now = time.time()

        # Remove old timestamps (older than 1 second)
        self._request_times = [t for t in self._request_times if now - t < 1.0]

        # If we've hit the limit, wait
        if len(self._request_times) >= self.rate_limit:
            sleep_time = 1.0 - (now - self._request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self._rate_limit_wait()

        self._request_times.append(now)

    async def _fetch_with_retry(self, session: aiohttp.ClientSession, url: str, **kwargs) -> str:
        """Fetch with retry logic and exponential backoff"""
        for attempt in range(self.retry_attempts):
            try:
                async with self._semaphore:
                    await self._rate_limit_wait()

                    # Add delay between requests if configured
                    if self.request_delay_ms > 0:
                        await asyncio.sleep(self.request_delay_ms / 1000.0)

                    async with session.get(url, timeout=self.timeout, **kwargs) as response:
                        response.raise_for_status()
                        return await response.text()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.retry_attempts - 1:
                    raise

                # Exponential backoff
                wait_time = (self.retry_backoff ** attempt)
                print(f"  ⚠️  Retry {attempt + 1}/{self.retry_attempts} after {wait_time:.1f}s: {str(e)[:100]}")
                await asyncio.sleep(wait_time)

    @abstractmethod
    async def fetch_async(self) -> RawData:
        """Async fetch implementation - must be implemented by subclasses"""
        pass

    def fetch(self) -> RawData:
        """Sync wrapper for async fetch"""
        return asyncio.run(self.fetch_async())
```

### 3. Actualizar RestFetcher para usar AsyncFetcher

```python
# app/fetchers/rest.py

import json
import aiohttp
from app.fetchers.async_fetcher import AsyncFetcher, RawData, ParsedData, DomainData


class RESTFetcher(AsyncFetcher):
    """Fetcher para APIs REST que devuelven JSON con soporte de concurrencia"""

    async def fetch_async(self) -> RawData:
        """Realiza el request HTTP con control de concurrencia"""
        url = self.params.get("url")
        method = self.params.get("method", "GET").upper()
        headers = self.params.get("headers", {})
        query_params = self.params.get("query_params", {})

        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")

        # Parse if JSON strings
        if isinstance(headers, str):
            headers = json.loads(headers)
        if isinstance(query_params, str):
            query_params = json.loads(query_params)

        # Async HTTP request with concurrency control
        async with aiohttp.ClientSession() as session:
            return await self._fetch_with_retry(
                session,
                url,
                headers=headers,
                params=query_params
            )

    def parse(self, raw: RawData) -> ParsedData:
        """Parsea el JSON"""
        return json.loads(raw)

    def normalize(self, parsed: ParsedData) -> DomainData:
        """Por defecto devuelve los datos tal cual"""
        return parsed


# Alias para compatibilidad
RestFetcher = RESTFetcher
```

### 4. Fetcher con paginación automática

```python
# app/fetchers/paginated_rest_fetcher.py

import asyncio
from typing import List, Dict, Any
import aiohttp
from app.fetchers.async_fetcher import AsyncFetcher, DomainData


class PaginatedRestFetcher(AsyncFetcher):
    """Fetcher REST con paginación automática y concurrencia"""

    async def fetch_async(self) -> List[Dict[str, Any]]:
        """Fetch all pages concurrently with rate limiting"""
        url = self.params.get("url")
        headers = self.params.get("headers", {})
        query_params = self.params.get("query_params", {})

        # Parse if JSON strings
        if isinstance(headers, str):
            import json
            headers = json.loads(headers)
        if isinstance(query_params, str):
            import json
            query_params = json.loads(query_params)

        # First request to get total pages
        async with aiohttp.ClientSession() as session:
            first_page = await self._fetch_with_retry(
                session, url, headers=headers, params=query_params
            )

            import json
            data = json.loads(first_page)

            # If not paginated, return as-is
            if 'totalPages' not in data:
                return data.get('content', data)

            total_pages = data['totalPages']
            all_records = data.get('content', [])

            print(f"  📄 Total pages: {total_pages}")

            # Fetch remaining pages concurrently
            if total_pages > 1:
                tasks = []
                for page in range(1, total_pages):
                    page_params = {**query_params, 'page': str(page)}
                    task = self._fetch_page(session, url, headers, page_params)
                    tasks.append(task)

                # Execute with concurrency limit
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect results
                for result in results:
                    if isinstance(result, Exception):
                        print(f"  ⚠️  Page fetch failed: {result}")
                    else:
                        all_records.extend(result.get('content', []))

            print(f"  ✅ Fetched {len(all_records)} total records from {total_pages} pages")
            return all_records

    async def _fetch_page(self, session, url, headers, params):
        """Fetch a single page"""
        text = await self._fetch_with_retry(session, url, headers=headers, params=params)
        import json
        return json.loads(text)

    def parse(self, raw):
        """Already parsed in fetch_async"""
        return raw

    def normalize(self, parsed):
        """Already normalized"""
        return parsed
```

## UI: Configuración en frontend

### 1. En Fetcher Type modal (CreateEditFetcherModal.vue)

Los parámetros de concurrencia aparecen como parámetros opcionales:

```
Parameter Name: max_concurrent_requests
Data Type: integer
Required: ☐
Default Value: 5
```

### 2. En Resource modal (Resources.vue)

Cuando se crea un resource, estos parámetros aparecen como **Optional Parameters**.

El usuario puede:
- No añadirlos (usa defaults del fetcher type)
- Añadirlos y usar el default value (aparece automáticamente)
- Añadirlos y cambiar el valor (override)

## Casos de uso

### Caso 1: API pública sin restricciones (BDNS)

```python
# Fetcher Type defaults se usan
# No se añaden parámetros de concurrencia al resource
# Resultado: 5 concurrent requests, 10 req/s
```

### Caso 2: API con rate limit estricto (INE)

```python
# En el resource INE, se añaden overrides:
params = {
    "url": "https://servicios.ine.es/...",
    "rate_limit_per_second": "2",  # Solo 2 req/s
    "max_concurrent_requests": "1",  # Sin concurrencia
    "request_delay_ms": "500",  # 500ms entre requests
}
```

### Caso 3: API con paginación masiva (DIR3)

```python
# Resource DIR3 con paginación automática
params = {
    "url": "https://dir3.example.com/unidades",
    "max_concurrent_requests": "20",  # Muchas páginas en paralelo
    "rate_limit_per_second": "50",  # API tolerante
    "batch_size": "1000",  # 1000 registros por página
}
# Usa PaginatedRestFetcher que obtiene todas las páginas automáticamente
```

## Beneficios

1. **Flexibilidad:** Cada API puede tener su configuración óptima
2. **Defaults sensatos:** No hay que configurar nada si no es necesario
3. **Respeto a APIs:** Evita sobrecarga de servicios externos
4. **Robustez:** Retry automático con backoff exponencial
5. **Performance:** Concurrencia controlada para APIs que lo permiten
6. **UI friendly:** Se ve como cualquier otro parámetro

## Próximos pasos

1. ✅ Definir parámetros en FetcherParams (ya está el modelo)
2. ⬜ Implementar AsyncFetcher base
3. ⬜ Actualizar RestFetcher para heredar de AsyncFetcher
4. ⬜ Implementar PaginatedRestFetcher
5. ⬜ Añadir parámetros de concurrencia al fetcher "API REST" via UI
6. ⬜ Actualizar FetcherManager para usar async cuando esté disponible
7. ⬜ Tests de concurrencia y rate limiting
8. ⬜ Documentación de mejores prácticas por API

## Alternativa más simple (MVP)

Si prefieres empezar más simple, podemos implementar solo rate limiting básico:

```python
# app/fetchers/rest.py

import time
import requests
import json
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData


class RESTFetcher(BaseFetcher):
    """Fetcher para APIs REST que devuelven JSON"""

    def __init__(self, params):
        super().__init__(params)
        self._last_request_time = 0
        self.request_delay_ms = int(params.get("request_delay_ms", 0))

    def fetch(self) -> RawData:
        """Realiza el request HTTP con rate limiting básico"""
        url = self.params.get("url")
        method = self.params.get("method", "GET").upper()
        headers = self.params.get("headers", {})
        query_params = self.params.get("query_params", {})
        timeout = int(self.params.get("timeout", 30))

        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")

        # Parse if JSON strings
        if isinstance(headers, str):
            headers = json.loads(headers)
        if isinstance(query_params, str):
            query_params = json.loads(query_params)

        # Simple rate limiting: wait if needed
        if self.request_delay_ms > 0:
            elapsed = (time.time() - self._last_request_time) * 1000
            if elapsed < self.request_delay_ms:
                time.sleep((self.request_delay_ms - elapsed) / 1000)

        # Make request
        response = requests.request(
            method, url,
            headers=headers,
            params=query_params,
            timeout=timeout
        )
        response.raise_for_status()

        self._last_request_time = time.time()
        return response.text

    # ... parse y normalize igual
```

Esta versión solo añade `request_delay_ms` como parámetro opcional y es mucho más simple de implementar.
