# OpenDataManager — Manual de la consola

Guía de manejo de la aplicación web de OpenDataManager (ODM) para el operador. Describe qué hace cada vista y cómo se usan las operaciones habituales. (Para *integrar* una aplicación que consume ODM por API/webhook, ver `manual_usuario.md`.)

## Qué es ODM

ODM es un **motor de cosecha y normalización de datos abiertos**. Define orígenes de datos (recursos), los extrae mediante *fetchers* re-ejecutables, versiona el resultado como *datasets* y lo sirve a aplicaciones cliente, que pueden **suscribirse** y recibir avisos por *webhook* cuando hay datos nuevos. Sobre todo ello hay control de acceso (RBAC), gobernanza de fuentes y gestión del ciclo de vida de los datos.

## Conceptos

- **Publisher**: el organismo que publica los datos (Ayuntamiento, INE, Junta…). Tiene nombre, acrónimo, nivel (municipal/provincial/autonómico/estatal) y portal.
- **Recurso (Resource)**: un origen de datos concreto y su pipeline de extracción. Es la pieza central. Tiene un publisher, un *fetcher*, parámetros y, opcionalmente, una programación.
- **Fetcher: especie y variante**. La **especie** es la clase que sabe *cómo* hablar con un tipo de origen (ATOM/RSS, API REST, HTML, Web Tree, WFS/WMS, descarga de ficheros, OSM…). Una **variante** (lo que en la UI eliges como «preset») es esa misma especie con un bloque de parámetros que encapsula las peculiaridades de una *familia* de fuentes; así un recurso solo aporta lo verdaderamente suyo (p. ej. la URL). Cambiar el comportamiento de toda una familia = editar la variante una sola vez.
- **Ejecución (Process)**: cada vez que se corre la extracción de un recurso. Tiene estado (en curso / completada / fallida), tiempos y registros cargados.
- **Dataset y versiones**: el resultado de las ejecuciones. ODM versiona los datos y entiende el dataset como una **caché provisionada**, no como un archivo a custodiar para siempre: se puede volver a derivar de la fuente, así que su permanencia se gestiona (ver *Ciclo de vida*).
- **Candidato**: un sub-origen detectado automáticamente al explorar (*discover*) un recurso; se **promueve** a recurso si interesa.
- **Aplicación cliente**: una app externa registrada en ODM que consume datos, por API GraphQL y/o por webhook, y que se **suscribe** a recursos.
- **Suscripción**: vínculo aplicación↔recurso; ODM avisa a la app cuando el recurso carga datos nuevos.
- **Gobernanza**: cada origen se clasifica por *clase de fuente* (api_abierta, publicacion_abierta, scraping_publico, scraping_privado…); la instancia admite solo ciertas clases.

## Las vistas

### Dashboard

Vista de entrada. Estadísticas de extracción por recurso, recursos activos y el pulso general del sistema. Punto de partida para ver qué está corriendo y qué ha cargado recientemente.

### Resources

El catálogo de recursos y la vista de trabajo principal.

- **Filtros**: búsqueda por nombre/publisher, **Type** (especie de fetcher), **Publisher**, **Level**, **Status** (activos/inactivos), **Origen** (quién lo generó: usuario / aplicación / sistema) y **Used by** (qué aplicación está suscrita: «Anyone» o una concreta).
- **Columnas**: nombre (con un *badge* de origen — usuario / aplicación / sistema), publisher, **Apps** (número de aplicaciones suscritas; el tooltip las nombra), tipo y estado.
- **Acciones por recurso**:
  - **Discover** — explora el origen y propone *candidatos* (sub-recursos) para promover.
  - **Run** — lanza una ejecución (extracción) ahora.
  - **Test** — prueba la extracción sin consolidar, para validar la configuración.
  - **Edit** — modifica el recurso. Si tiene suscripciones activas, los cambios que alteran su «contrato» (fetcher, variante, parámetros) se **bloquean** por el guardia de integridad; la salida es clonar.
  - **Clone** — copia el recurso como punto de partida editable.
  - **Delete** — lo manda a la papelera (borrado lógico).

### Candidates / Discovering

Tras un *Discover*, aquí ves los sub-orígenes detectados y los **promueves** a recursos. *Discovering* muestra el progreso de una exploración en curso.

### Fetchers

Catálogo de fetchers (especies) y sus **variantes**. Aquí se crean/editan las variantes: el bloque de parámetros que comparte una familia de fuentes. Editar una variante cambia el comportamiento de todos los recursos que la usan, de una vez.

### Processes (Ejecuciones)

Historial y estado de las ejecuciones. Muestra la **concurrencia** (cuántos procesos corren en paralelo y el límite configurado) y permite seguir o detener ejecuciones. El número de procesos simultáneos y los límites por fetcher se ajustan en *Settings*.

### Schedule

Programación de recursos por **cron** (días, horas). Lo programado lo ejecuta el sistema automáticamente; esas ejecuciones no consumen cuota de usuario.

### Data Explorer

Inspección de los datos cargados: campos detectados por recurso y sus **versiones**, para ver qué hay realmente dentro de cada dataset y comparar versiones.

### Publishers

Alta y edición de organismos (nombre, acrónimo, nivel, país, portal). Los recursos cuelgan de un publisher.

### Applications

Aplicaciones cliente registradas. Por cada una: su **webhook**, su **modo de consumo** (webhook / graphql / both) y sus **suscripciones**. Es el reverso de la columna «Apps» de Resources: desde la aplicación ves sus recursos; desde el recurso ves sus aplicaciones. Requiere permiso de gestión de aplicaciones.

### Usuarios

Gestión de usuarios y **roles (RBAC)**. Roles de serie: *Lector* (solo lectura), *Operador* (define y prueba recursos), *Ejecutor* (lanza/para ejecuciones), *Suscriptor* (cuenta de servicio de aplicaciones: lectura + crear/editar recursos + lanzar ejecuciones + gestionar su aplicación y suscripciones) y *Administrador* (acceso total). Cada permiso gobierna una operación; asigna el rol más ajustado a cada cuenta.

### Settings

Parámetros de la instancia: **concurrencia** (cuántos procesos en paralelo) y **límites por fetcher**, y el **cooldown de refresco** (`execute_cooldown_minutes`): un recurso ejecutado con éxito hace menos de ese tiempo rechaza un nuevo refresco, para no abusar del proveedor. (Las **clases de fuente admitidas** por la gobernanza se fijan por entorno, `ODM_ALLOWED_SOURCE_CLASSES`.)

### Trash

Registros borrados lógicamente. Desde aquí se **restauran** o se **borran definitivamente**.

### Mis datos

Perfil del usuario y su historial de **solicitudes de recursos** (arrendamientos): qué pediste y hasta cuándo está disponible.

## Ciclo de vida de los datos

Un dataset es una caché re-derivable, no un archivo perpetuo. Su permanencia se decide por: la **demanda** (cuántas aplicaciones lo usan y con qué peso), la **re-derivabilidad** (un ZIP anual estable se recupera; un feed de novedades, no), el **coste de reconstrucción** y los **arrendamientos (leases)**. Cuando una aplicación solicita un recurso, ODM responde de tres formas: **concedido temporal** («disponible hasta el jueves a las 15:30»), **concedido permanente** (alta prioridad / fijado) o **denegado** (efímero no materializado y no re-derivable, o límite de capacidad). La permanencia efectiva es el máximo de los arrendamientos activos, las versiones fijadas y el suelo de política.

## Operaciones habituales

**Dar de alta un recurso.** En *Resources*, crea el recurso eligiendo publisher, fetcher y variante, y aportando solo sus parámetros propios (la variante pone el resto). Pruébalo con *Test* antes de programarlo.

**Importar un paquete de recursos (manifiesto).** Un manifiesto es un JSON declarativo que empaqueta un publisher y sus recursos (referenciando el fetcher por su nombre, nunca por id ni código interno). Es idempotente: reimportar actualiza en vez de duplicar (reconcilia el publisher por acrónimo y cada recurso por publisher+nombre). Útil para alta masiva y para portar definiciones entre instancias.

**Explorar y promover.** Para orígenes con sub-recursos, usa *Discover* y promueve los *candidatos* que interesen.

**Programar.** En *Schedule*, asigna una expresión cron al recurso para que se extraiga solo.

**Dar de alta una aplicación y suscribirla.** En *Applications*, registra la app, fija su webhook y su modo de consumo, y suscríbela a los recursos que necesite. A partir de ahí, cada carga nueva le llega por webhook.

**Refrescar a demanda.** *Run* lanza una ejecución. Si el recurso se ejecutó con éxito hace muy poco, el cooldown lo rechaza con un aviso: es protección, no error.

## Permisos en breve

Lecturas (ver recursos, ejecuciones, datos): basta estar autenticado con un rol de lectura. Crear/editar recursos: *Operador*. Lanzar/parar ejecuciones: *Ejecutor*. Gestionar aplicaciones y suscripciones: el permiso correspondiente (lo tienen *Suscriptor* y *Administrador*). Programación, ajustes y usuarios: permisos específicos, normalmente de administración.
