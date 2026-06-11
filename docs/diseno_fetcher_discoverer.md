# Separación Fetcher / Discoverer — diseño (vía 1: rol declarado)

## El problema
Un descubridor **no es un fetcher**: no extrae datos, su producto son
recursos-hijo (candidatos), no registros. Pero el modelo los metía a todos en una
sola entidad `Fetcher` con un flag `modos`, y los descubridores puros (Pivote,
Descubridor REST) fingían `fetch()` con `NotImplementedError`. "Un fetcher que no
fetchea" es el síntoma de dos responsabilidades forzadas en una clase. Agruparlos
en dos `<optgroup>` del selector "Fetcher Type" era maquillaje: por debajo seguían
siendo "tipos de Fetcher".

## Decisión: roles, no tipos (vía 1)
Una especie declara los **roles** que juega. `Fetcher` y `Discoverer` son roles
distintos, expuestos como conceptos separados en código y en UI, **compartiendo un
único registro** (la tabla de especies). Así se obtiene la separación conceptual
sin duplicar los duales.

- **Fetcher** (rol extraer): lee una fuente → produce *registros*.
- **Discoverer** (rol descubrir): lee un índice → produce *recursos-hijo (Fetchers)*.
- Entrada y salida distintas ⇒ son cosas distintas, aunque compartan tabla.

Descartadas: la vía 2 (dos jerarquías duras, duplica los duales) y la vía 3
(no resuelve del todo la pregunta).

## Capa de código — HECHO
`app/fetchers/base.py` reestructurado en tres niveles:
- `BaseSpecies(ABC)`: raíz común. Aporta `__init__(params)`, `_request()` (HTTP con
  reintentos/cortesía), `current_state`, `profile_stats`. Sin contrato de extracción
  ni de descubrimiento.
- `BaseFetcher(BaseSpecies)`: rol extraer. Abstractos `fetch/parse/normalize` +
  `stream/execute`.
- `BaseDiscoverer(BaseSpecies)`: rol descubrir. Abstracto `propose()`. **No tiene
  fetch/parse/normalize** — un descubridor no es un fetcher.

Migrados los descubridores puros a `BaseDiscoverer` (fuera el `fetch()` fingido):
`PivotDiscovererFetcher`, `RestApiDiscovererFetcher`.

Los **duales** (Catálogo DCAT, Web Tree, Compressed File) siguen como `BaseFetcher`
y definen además `propose()`. Más adelante pueden heredar explícitamente de ambas
bases (`class X(BaseFetcher, BaseDiscoverer)`) para declarar los dos roles a nivel
de clase; de momento se quedan como están (funciona, no urge).

`factory.create_from_resource` es duck-typed (importa por `class_path`, instancia
con `params`); su anotación de retorno pasó a `BaseSpecies`. Nadie hace
`isinstance(BaseFetcher)`, así que el corte no rompe instanciación.

## Qué pasa con `modos`
Se queda como **la declaración de roles** de la especie en la tabla Fetcher:
`extraer` ⇄ rol Fetcher, `descubrir` ⇄ rol Discoverer. Es la fuente de verdad de
en qué selector aparece cada especie. (Posible renombrar `modos`→`roles` en una
pasada posterior; no es bloqueante.)

## Capa UI/UX — PENDIENTE
Quitar el parche del `<optgroup>` y partir el alta de recurso en dos flujos:
- **Nuevo recurso de extracción** → elige un **Fetcher** (especies con rol extraer).
- **Nueva colección** → elige un **Discoverer** (especies con rol descubrir);
  marca `genera_colecciones`.
Los duales aparecen en ambas listas. Las vistas Collections/Discovering ya existen
y encajan como destino del segundo flujo.

## Manager — ya alineado
El branch ya es por intención: `quiere_descubrir = not is_child and es_coleccion`
→ `propose()`; si no → pipeline de extracción. Con los roles explícitos, queda como
"¿el recurso es de un Discoverer (y genera_colecciones)? descubre : extrae", sin
`hasattr(propose)`.

## Pasos restantes (ordenados)
1. (hecho) Bases separadas + migrar descubridores puros.
2. UI: partir el alta de recurso en los dos flujos; retirar el optgroup.
3. (opcional) Duales heredan de ambas bases explícitamente.
4. (opcional) Renombrar `modos`→`roles` en modelo + GraphQL + UI.
5. Catálogo de especies (Fetchers.vue): mostrar el rol como columna/badge.

## Migración
En PRUEBAS no hay retrocompat que respetar: se puede reestructurar libremente. El
cambio de bases no toca datos (la tabla de especies y `modos` siguen igual); es un
refactor de clases + UI. Sin migración Alembic.
