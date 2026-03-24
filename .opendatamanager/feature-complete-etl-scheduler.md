# feature/complete-etl-scheduler — Aportaciones al proyecto

## Resumen

Esta rama introduce el pipeline ETL completo: ejecución parametrizada de recursos con cron, carga de datos en BD, versioning de datasets y notificaciones a aplicaciones suscritas.

---

## 1. Scheduler basado en cron por recurso

**Fichero:** `app/services/scheduler_service.py`

Sustituye el `scheduler.py` monolítico por un servicio con `APScheduler AsyncIOScheduler`. Al arrancar la aplicación, lee todos los `Resource` activos que tengan campo `schedule` (expresión cron) y registra un job por cada uno.

```
Resource.schedule = "0 2 * * *"  →  job que ejecuta el fetcher a las 2:00 AM
```

Integrado en `main.py` vía `@app.on_event("startup/shutdown")`.

---

## 2. DataLoaderService — carga en BD

**Fichero:** `app/services/data_loader_service.py`

Carga los datos normalizados por el fetcher en tablas PostgreSQL del schema `core`. Soporta dos modos:

- **`upsert`** — inserta o actualiza registros existentes (por PK).
- **`replace`** — borra todo e inserta desde cero.

Crea automáticamente la tabla destino si no existe, infiriendo el schema desde los datos (`schema_json` del Dataset).

También expone la función `stage_data()` para escritura previa en staging antes del commit final.

---

## 3. NotificationService — webhooks a apps suscritas

**Fichero:** `app/services/notification_service.py`

Tras cada ejecución exitosa, notifica a las `Application` suscritas al recurso mediante webhook HTTP POST firmado con HMAC-SHA256.

Incluye política de auto-upgrade configurable: `major`, `minor`, `patch` — controla si la app recibe la notificación según el tipo de cambio de versión del dataset.

---

## 4. Ejecución parametrizada de recursos

**Commits:** `732f9af feat: add parameterized resource execution`

La mutación `executeResource` ahora acepta `params` adicionales en tiempo de ejecución que sobreescriben o complementan los `ResourceParam` estáticos del recurso. Útil para lanzamientos manuales con parámetros distintos (ej. año concreto, rango de fechas).

---

## 5. AtomPagingFetcher — PLACSP

**Fichero:** `app/fetchers/atom_paging.py`

Fetcher especializado para feeds ATOM paginados (usado en PLACSP — Plataforma de Contratación del Sector Público). Itera automáticamente por todas las páginas hasta obtener todos los registros.

Sustituye al `atom.py` genérico anterior, que queda eliminado.

---

## 6. ArtifactBuilder / Dataset versioning

**Fichero:** `app/builders/artifact_builder.py`

Construye datasets versionados (major.minor.patch) tras cada ejecución. Persiste:
- Fichero `data.jsonl` con los registros
- Fichero `schema.json` con el schema inferido
- Fichero `models.py` con clases SQLAlchemy generadas automáticamente
- Fichero `metadata.json` con metadatos de la ejecución

---

## 7. Reorganización de módulos

| Antes | Después |
|---|---|
| `app/graphql_api/` | `app/graphql/` |
| `app/scheduler.py` | `app/services/scheduler_service.py` |
| `app/fetchers/atom.py` | `app/fetchers/atom_paging.py` |
| `app/fetchers/paginated_rest.py` | eliminado |
| `app/fetchers/powerbi.py` | eliminado |
| `app/fetchers/soap.py` | eliminado |

---

## 8. seed_data.py

Script para poblar la BD con recursos de ejemplo: AGE (Administración General del Estado) y datos por CCAA. Útil para desarrollo y demos.

---

## Dependencias añadidas

- `APScheduler>=3.10` — scheduling de jobs cron
- `xmltodict` — parsing de feeds ATOM/XML
