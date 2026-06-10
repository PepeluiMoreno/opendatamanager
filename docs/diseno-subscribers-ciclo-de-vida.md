# Diseño: Subscribers (antes Applications) — alta, ciclo de vida e IA

> **Estado:** dirección acordada (a implementar). Las partes que tocan **esquema GraphQL + BD** son contrato con el consumidor → cambios coordinados en los dos repos (lockstep).
> **Cross-ref scheduling:** `docs/diseno-scheduling-demanda-y-prioridades.md`

## 1. Renombrado: Application -> Subscriber

La entidad `Application` pasa a ser **Subscriber**: en el modelo nuevo es exactamente eso — un consumidor que se suscribe a recursos; ya no crea ni descubre catálogo.

- **Ortografía: "Subscriber" (inglés)**, no "Suscriber". El esquema ya es inglés (Application, Resource, Subscription); el híbrido cantaría. O todo inglés o todo español, no a medias.
- **Alcance por capas (por el coste):**
  - **UI / labels** (barra lateral, títulos, botones): renombrar libremente — riesgo cero, ganancia inmediata.
  - **Esquema GraphQL + BD + RBAC** (`Application`->`Subscriber`, `applications`->`subscribers`, arg `applicationId`->`subscriberId`, tabla y FK `application_id`, permisos `aplicaciones.*`): es **contrato con el consumidor + migración** -> cambio coordinado en lockstep. Decidir si compensa el churn o, de momento, solo la capa visible.

## 2. IA: una sola consola "Subscribers"; Approvals dentro

Desaparece **Approvals** como entrada de primer nivel (era un resto del flujo viejo de "solicitud de alta"). "Subscribers" tiene dos estados:

- **Pendientes** — esperando aprobación; aquí se **aprueba/rechaza** (la antigua Approvals).
- **Activos** — registrados; gestión de sus **suscripciones**.

## 3. Alta = primera suscripción (transacción monolítica)

El **alta del subscriber** y su **primera suscripción** son **una única transacción atómica**:

- el consumidor aporta su **identidad** (nombre + webhook + secreto + datos de admisión) **y** el **recurso** que quiere suscribir primero;
- **aprobar** = en una transacción: crear principal + token + Subscriber + la suscripción;
- **rechazar = no se crea nada** (ni alta ni suscripción). No existe el estado "registrado con cero suscripciones".
- **Suscripciones posteriores:** auto-servicio del propio subscriber (ya implementado), sin aprobación. **Solo la primera** es la puerta (vetting de entrada).

## 4. Estado de la consola del consumidor

- **Fuerza el formulario** cuando **nunca se le ha cursado ninguna suscripción** (cero concedidas jamás) = aún no registrado. No es "no hay peticiones", es "no se ha concedido ninguna".
- Registrado (>=1 concedida) -> consola de **CRUD de suscripciones + control de respuestas** (Recepciones / avisos de ODM).
- **Baja** (Subscriber borrado en ODM) -> la consola **vuelve al estado inicial** (formulario). Disparado por el push `anulada` + revalidación del cliente.

## 5. Borrado en cascada (soft-delete)

Borrar un Subscriber **arrastra sus suscripciones en cascada**, en **soft-delete** (no hard):

- requiere `ResourceSubscription.deleted_at` (columna nueva + migración idempotente, `ADD COLUMN IF NOT EXISTS`);
- filtrar `deleted_at IS NULL` en las queries de suscripciones;
- el borrado del Subscriber marca `deleted_at` en sus suscripciones en vez de borrar filas.
- Coherente con el soft-delete del propio Subscriber (que ya libera el nombre con `__del_<ts>`).

## 6. Consumidor reducido a consola de suscripciones

Se quita del consumidor toda **creación/mutación de catálogo**: `create_webtree_resource`, `discover`, candidatos (`resource_candidates`/`promote_candidate`/`discard_candidate_resource`), `import_manifest`, `manifest_template`, `execute_resource`, `delete_resource`, clonar; y en el panel: el asistente "Nuevo recurso", "Proponer recurso", los candidatos y los botones clonar/ejecutar/borrar.

Queda: **listar** el catálogo (incl. recursos descubiertos por ODM), **CRUD de suscripciones** (con su `caducidad`), y **control de respuestas**. RBAC: revocar al rol `suscriptor` el permiso de crear fuentes (apertura `scraping_publico`).

## Orden de implementación sugerido

1. **Consumidor:** poda de creación de recursos (independiente, ya acordado) -> consola de suscripciones.
2. **`ResourceSubscription.deleted_at`** + cascada soft-delete en el borrado del Subscriber.
3. **Alta atómica:** la solicitud lleva el recurso; aprobar crea todo-o-nada; rechazar no crea nada.
4. **IA:** fusionar Approvals dentro de Subscribers (estados pendiente/activo).
5. **Renombrado UI** Application->Subscriber (y, si se decide, esquema/BD/RBAC en lockstep con el consumidor).
6. **Scheduling por demanda** (`caducidad` + ventana + UI) — ver doc de scheduling. Priorización/carga: **aplazado**.
