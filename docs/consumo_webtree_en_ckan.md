# Cómo se consume un Web Tree en un CKAN

Este documento describe el camino completo desde que un crawler **Web Tree** de
OpenDataManager (ODM) descubre los ficheros de un portal hasta que esos datos
aparecen publicados en un **CKAN**, y reparte con precisión las
responsabilidades entre ambos lados.

## Principio rector: ODM produce, el consumidor mapea

ODM es un **productor neutro**. Produce recursos y datasets y los expone tal
cual. **No conoce CKAN** ni ningún otro destino: no guarda slugs de *package*,
ni organizaciones, ni grupos, ni temas, ni periodicidades CKAN, ni vocabularios
DCAT.

Todo el mapeo y la "traducción" al destino es responsabilidad **exclusiva de un
servicio de exportación que vive en el lado del consumidor** (para Jerez,
`ckan-jerez`). Ese servicio lee lo que ODM expone y se encarga de marear su
CKAN. La frontera es estricta: si algo es específico de CKAN, no entra en ODM.

Esto no es purismo: garantiza que un mismo recurso de ODM pueda ser consumido a
la vez por un CKAN, por un Socrata, por un portal NTI-RISP o por un proceso
analítico, cada uno con su propio mapeo, sin que el productor se acople a
ninguno.

## Lo que ODM produce a partir de un Web Tree

Dentro de ODM, la cadena es íntegramente neutral:

1. **Discover.** El crawler Web Tree recorre el árbol del portal y agrupa las
   URLs hoja en **candidatos**: cada candidato es una serie, descrita por un
   `pathTemplate` (`.../a06-contratos/b-convenios/{year}/14-urbanismo/{*}`) y sus
   **dimensiones** detectadas (`year`, etc.).
2. **Taxonomía al vuelo.** A partir de los `pathTemplate` se deriva el árbol de
   ramas del portal (segmentos de ruta constantes), sin persistir nada: es una
   vista para navegar y curar.
3. **Promoción.** Se promueve a recurso, bien candidato a candidato, bien por
   **rama entera** (`promover_rama`): las hojas de la rama se funden en un
   recurso y los segmentos que varían entre ellas se abren como **dimensiones
   columna** (p. ej. `year` + `tipo_convenio`).
4. **Ejecución.** Al ejecutarse, el recurso produce un **Dataset** cuya forma
   depende del `extract_mode`: `datos` (tabla de filas), `censo` (una fila por
   documento, índice documental) o `receta` (un dato limpio por fichero).

Lo que ODM expone de cada recurso/dataset es estrictamente descriptivo: nombre,
*publisher*, especie (fetcher), dimensiones, las filas de datos, y la
versión/hash de la entrega. Nada de esto presupone un destino.

## Cómo lo expone ODM (los contratos de consumo)

El consumidor dispone de dos mecanismos, ambos neutrales:

- **API GraphQL.** Consulta de recursos, datasets, dimensiones, versiones y
  estado. Es el canal de *pull*.
- **Suscripción + webhook.** Una `Application` (el exportador es una de ellas) se
  suscribe a los recursos que le interesan. Cuando un recurso publica una versión
  nueva, ODM **notifica por webhook** según el `consumption_mode` de la
  aplicación. El webhook es la señal; el exportador hace después el *pull* de la
  versión concreta.

ODM no empuja datos transformados: anuncia "hay versión nueva del recurso X" y
ofrece la API para traerla.

## El servicio de exportación (lado `ckan-jerez`)

Aquí vive **todo** el mapeo. Sus responsabilidades:

1. **Suscribirse** en ODM a los recursos relevantes.
2. **Reaccionar** al webhook (o a una sincronización periódica) trayendo la
   versión del dataset por la API.
3. **Mapear a CKAN**, que es la parte sustancial:
   - el *publisher* de ODM → **organización** CKAN;
   - la sección/rama de origen → **grupos y temas**, mapeados a un vocabulario
     controlado (**DCAT-AP-ES / NTI-RISP**, los sectores de datos.gob.es);
   - el recurso-rama → un **dataset** (*package*) CKAN;
   - las series y sus distribuciones → **resources** del *package* (CSV o el
     fichero original), o una tabla en el *datastore*;
   - las dimensiones (year, `tipo_convenio`…) → **campos** del diccionario de
     datos, y la dimensión temporal → la **periodicidad** DCAT.
4. **Mantener la identidad** del *package*: el exportador lleva su propia tabla
   de correspondencia `recurso-ODM ↔ package-CKAN`. El *slug* del *package* lo
   decide y gobierna **él**, no ODM.
5. **Publicar de forma idempotente**: `package_create`/`package_update` (upsert)
   y `datastore` para las tablas, de modo que reprocesar una versión no duplique.
6. **Auto-sanarse**: reconciliar divergencias, reintentar entregas fallidas y
   registrar el estado de sincronización.

## Modelo de mapeo recomendado para Jerez

| Concepto en el portal / ODM            | Destino en CKAN                          |
|----------------------------------------|------------------------------------------|
| Publisher (Ayto. de Jerez)             | Organización                             |
| Sección de transparencia (`a06`, `a07`)| Grupo / tema (vía DCAT-AP-ES / NTI-RISP) |
| Subsección o rama promovida            | Dataset (*package*)                      |
| Serie con `{year}`                     | Resource/distribución, o tabla datastore |
| Dimensiones derivadas (year, branch…)  | Campos del diccionario de datos          |
| Dimensión temporal (`year`)            | Periodicidad (frequency)                 |

La granularidad "subsección → dataset" suele ser el punto dulce, pero la decide
el exportador, no ODM.

## Identidad estable y cambios del portal

La ruta del portal (el `fileadmin` de TYPO3) es volátil. La continuidad **no**
se ancla en ella:

- La identidad del *package* CKAN la gestiona el **exportador**, en su tabla de
  correspondencia. Si el portal reorganiza sus carpetas, ODM vuelve a descubrir,
  el recurso de ODM conserva su identificador, y el exportador sigue publicando
  contra el mismo *package*.
- ODM, por su parte, sí vigila la **salud del descubrimiento** (concern legítimo
  suyo): si una rama que antes traía decenas de series cae a cero candidatos, eso
  es señal de que el portal cambió de sitio y debe avisar, en vez de propagar en
  silencio un dataset vacío hacia el consumidor.

## Secuencia de actualización

1. ODM ejecuta el recurso (programado) y produce una versión nueva del dataset.
2. ODM notifica a los suscriptores por webhook.
3. El exportador trae la versión por la API, la transforma a DCAT y hace *upsert*
   en CKAN (*package* + resources + datastore).
4. CKAN queda actualizado; el exportador registra la correspondencia y el estado.

## Lo que ODM NO hace (límites duros)

- No conoce *slugs*, organizaciones, grupos ni temas de CKAN.
- No transforma a DCAT-AP-ES ni a ningún esquema de destino.
- No almacena credenciales de CKAN ni habla con su API.

Todo eso es del servicio de exportación. ODM termina su trabajo en el dataset
neutro y su notificación.

## Resumen del flujo

```
Portal TYPO3
   │  (HTTP, árbol fileadmin)
   ▼
ODM  ── Web Tree discover → candidatos → taxonomía → promover_rama
        → recurso → Dataset (neutral)
   │  API GraphQL  +  webhook de suscripción
   ▼
Exportador (ckan-jerez)
   │  mapeo DCAT-AP-ES · package_create/update · datastore
   ▼
CKAN  ── organización / grupos / datasets / distribuciones
```
