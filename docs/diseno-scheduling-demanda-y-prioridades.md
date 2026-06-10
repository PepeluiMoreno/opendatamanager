# Diseño: scheduling por demanda y gestión de prioridades/carga (ODM)

> **Estado**
> - **Parte A — frontera productor/consumidor + scheduling por demanda:** dirección acordada (a implementar).
> - **Parte B — prioridades + control de carga:** **DIFERIDO a una versión posterior de ODM.** Anotado aquí para no perderlo.

## Principio

ODM es el **productor neutral**. No decide políticas que correspondan al consumidor (mapeo a destino, frescura) ni se acopla a ningún consumidor concreto. El consumidor expresa **demanda**; el operador protege el **sistema** y las **fuentes**.

---

## A. Frontera productor / consumidor

Toda **creación y mutación del catálogo** vive en ODM (operador). El consumidor es consumo puro.

- **ODM (operador):** crear, editar, programar, ejecutar, **descubrir** (naves nodriza), promover/descartar candidatos, importar manifiestos, clonar, borrar recursos.
- **Consumidor:** **listar** el catálogo (incluidos los recursos ya descubiertos por ODM), **suscribirse / desuscribirse**, recibir datasets, republicar. Por cada suscripción, declarar la **caducidad** (ver A.2).
- **Se elimina del consumidor:** `create_webtree_resource`, `discover`, `resource_candidates`/`promote_candidate`/`discard_candidate_resource`, `import_manifest`, `manifest_template`, `execute_resource`, `delete_resource`, clonar. Y en el panel: el asistente "Nuevo recurso", "Proponer un recurso", los candidatos y los botones clonar/ejecutar/borrar.
- **RBAC:** revocar al rol `suscriptor` el permiso de crear fuentes (la apertura de la clase `scraping_publico` que se añadió para las propuestas). Crear fuentes pasa a exigir permiso de operador.

> "Descubrir" **no** se conserva en el cliente: lanzar una nave nodriza **crea** recursos. El cliente solo **lista** (lectura) lo que ODM ya descubrió.

## A.2. Scheduling por demanda (pull)

El cron desaparece. La cadencia se deriva de la demanda de los consumidores.

- **`ResourceSubscription.caducidad`** — edad máxima que ese cliente tolera para los datasets de ese recurso. Lo pone el **cliente**.
- **`Resource.ventana_permitida`** — **único parámetro de scheduling del operador**. Ventana en la que se permite refrescar (horaria y/o intervalo mínimo). Acota el ritmo: es el "suelo de cortesía" frente a la fuente (ToS, rate-limit, carga de crawl).
- **Motor:**
  - un dataset "caduca" para un suscriptor cuando `edad(dataset vigente) > su caducidad`;
  - al caducar para **≥1** suscriptor → se **encola** un refresco → se ejecuta en la primera ocasión **dentro de la ventana** del recurso;
  - cadencia efectiva del recurso = `min(caducidades de suscriptores activos)` — el más exigente marca el ritmo;
  - **sin suscriptores → recurso dormido** (no se toca).
- **Mecánica interna (NO son knobs del operador):**
  - medir la obsolescencia desde la **última comprobación con éxito** (`last_checked`), no desde la creación; un refresco que encuentra la fuente sin cambios **renueva `last_checked`** y no se redispara en cada barrido;
  - **backoff** ante fuente caída (no reintentar en bucle).
- **Descubridores (naves nodriza):** mantienen **cadencia de operador** (son catalogación, lado ODM). Solo las **hojas** (las que sirven datasets) van por demanda.

### UI del Schedule (parte ACTIVA)

La pantalla de Schedule **deja de ser un editor de cron**. Pasa a:

- por recurso, configurar la **ventana permitida** (único knob de scheduling del operador);
- **mostrar (derivado, solo lectura):** cadencia efectiva = `min(caducidades de suscriptores activos)`, próximo refresco dentro de la ventana, último fetch / `last_checked`, y estado (**debido** / **en ventana** / **dormido** por falta de suscriptores).

La **caducidad** se fija en la suscripción (lado Subscriber), no aquí. La vista demand-driven del Schedule es **parte activa**; **lo único aplazado (Parte B) es la política de priorización/carga**.
- **Relación con leases/retención:** `caducidad` = frescura del dataset **vigente** (cada cuánto re-comprobar). `DatasetLease`/`plazo` = cuánto **conservar** los antiguos. Son **ortogonales**; nombrarlas distinto. (Pendiente: revisar si `caducidad` reencuadra parte del modelo de leases.)

---

## B. Prioridades + control de carga — DIFERIDO a versión posterior

Objetivo: administrar la carga de ODM y resolver **colisiones de refresco** (dos necesidades compitiendo por capacidad finita → primero la prioritaria).

- **`ResourceSubscription.prioridad`** (recurso + cliente) — nivel de importancia.
  - **Gobernanza:** el cliente **expresa** urgencia; el operador asigna el **peso efectivo** (o por niveles capados). Si el cliente la fija libre, bajo contención todos serán "máxima" y pierde sentido.
- **Prioridad del job de un recurso** = `max(prioridad efectiva)` entre los suscriptores que lo demandan (los caducados). Un suscriptor urgente tira del recurso entero hacia delante.
- **Concurrencia acotada:** pool de **N workers** (semáforo contador). Cada refresco toma un permiso antes de tirar de la fuente y lo suelta al acabar. N = **"cuántos a la vez"**.
- **Cola de prioridad delante del pool:** los jobs caducados esperan ordenados por `(prioridad efectiva, antigüedad de la caducidad)`; al liberarse un permiso, el worker coge el de mayor prioridad. La cola = **"cuál primero"**.
- **Activación / desactivación por carga:** **N dinámico** según señales (RAM/CPU/nº en curso). Bajo presión, menos permisos → los pocos slots van a lo prioritario; lo demás espera (queda "desactivado" de hecho hasta que afloje). Compone con el pause/resume manual ya existente.
- **Anti-inanición:** **envejecimiento** — la prioridad efectiva sube con el tiempo que el dataset lleva caducado; lo urgente va primero, pero lo viejo acaba pasando.

### Semáforos: aclaración

Un semáforo da **concurrencia** ("cuántos a la vez"), **no prioridad** (reparte por orden de llegada). La prioridad la da la **cola** delante del pool. Juntos: **cola (cuál) + semáforo (cuántos)**.

### Nota de escala (importante)

A la escala actual (un consumidor, ~28 ítems, 24 GB) esto es **seguro**, no necesidad inmediata. Al implementarlo: montar primero las **costuras** (campo `prioridad` en la suscripción, cola de prioridad, pool acotado) con **política de carga trivial** (N fijo + un guardia de RAM/CPU). Hacer crecer el lazo de control **solo** si aparece contención real. No montar un sistema de control de carga antes de tener carga que controlar.
