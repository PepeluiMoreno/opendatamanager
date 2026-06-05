# Diseño: ciclo de vida de datasets — caché provisionada, arrendamientos y avisos

Estado: diseño consolidado, pendiente de implementar. Fecha: 2026-06-05.

## Motivación

Hoy los datasets (ficheros JSONL en `data_path` + metadatos en `dataset`) se
acumulan por ejecución y **nunca se purgan** → crecimiento ilimitado. Medido para
PLACSP, una ventana de 5 años (menores + licitaciones) son ~13 GB de descarga y
del orden de ~7 GB en disco. Hace falta gestionar el ciclo de vida.

## Idea central

Detrás de cada recurso hay la **extracción de una pipeline ETL re-ejecutable**.
Por tanto un dataset no es un activo que ODM custodia para siempre: es una
**caché provisionada bajo demanda**. Desalojar es barato porque (en general) se
puede volver a derivar de la fuente. Eso cambia retención por *política de caché*.

## Cuatro dimensiones de la política

1. **Demanda** — nº y peso de abonados (`DatasetSubscription`,
   `Application.subscribed_projects`) + acceso reciente/frecuente (a registrar).
   → prioridad.
2. **Re-derivabilidad** — ¿puede ODM recuperarlo de la fuente? **No es uniforme**:
   - ZIP anual de PLACSP = archivo estable → re-derivable.
   - Feed de novedades = ventana rodante → lo viejo **no** se recupera.
   El recurso necesita un flag *archival-estable vs efímero*.
3. **Arrendamiento (lease)** — el consumidor solicita el recurso con una retención;
   ODM concede un plazo; al expirar (y sin otros titulares) se borra.
4. **Coste de reconstrucción** — re-derivar un ZIP anual de licitaciones son ~2,2 GB
   y ~760k registros. Lo barato y re-derivable se desaloja sin pena; lo caro de
   rehacer merece retención generosa aunque sea re-derivable (no recomputar en bucle).

**Permanencia efectiva de un dataset** =
`max(leases activos, versiones fijadas (pinned), suelo de política)`.

## Respuesta a una solicitud de recurso

- **Concedido temporal**: "disponible hasta el jueves 12 a las 15:30"
  (`expira_en` formateado en la zona del titular; se guarda en UTC).
- **Concedido permanente**: "tu recurso está permanentemente disponible"
  (alta prioridad / pinned / política permanente; sin expiración).
- **Denegado**: "no podemos atender tu petición" (recurso efímero no materializado
  y no re-derivable, o límite de política/capacidad). No se promete lo que no se
  puede reclamar.

## Ciclo de vida del lease

- La solicitud lleva `retencion_solicitada`. ODM concede
  `min(solicitada, máximo_por_política)` y crea un lease
  (titular contactable, recurso+versión, `expira_en`, estado).
- **Provisión bajo demanda**: si el dataset no está materializado y el recurso es
  re-derivable → se dispara la pipeline, se materializa y se sirve durante la
  ventana. Si ya existía, se anota/renueva el lease.
- **Reference counting**: varios titulares pueden arrendar el mismo dataset con
  plazos distintos; vive mientras haya algún lease activo.
- **Liberación anticipada**: el titular —**proceso** (vía API, al terminar su ETL)
  **o usuario** (UI, "ya no lo necesito")— suelta el lease antes del plazo. Es
  decrementar el contador; si era el último y no hay candado ni suelo, el
  recolector desaloja de inmediato.
- **Expiración**: liberado el último lease, el recolector borra el JSONL y deja
  lápida "re-derivable" en los metadatos.

## Hilo de avisos por correo

Se apoya en lo existente (verificado): `services/mailer.enviar_email`,
`services/eventos.registrar_evento` con despacho a suscriptores, `Usuario.email` +
`Usuario.notificar_email`, `ApplicationNotification`. El aviso de lease es un tipo
de evento más, dirigido al titular:

- **Al conceder**: plazo concreto, o "permanentemente disponible", o el rechazo.
- **Recordatorio antes de expirar** (configurable, p. ej. 24 h): "expira mañana a
  las 15:30; renuévalo si aún lo necesitas". Convierte el plazo en contrato, no en
  hachazo.
- **Al expirar/desalojar**:
  - re-derivable → "se ha liberado para ahorrar espacio; vuelve a solicitarlo
    cuando quieras y se regenera".
  - efímero → "a partir de ahora ya no estará disponible".

## Recolector (garbage collector)

Programado o disparado por presión de disco. Desaloja datasets que cumplan:
no pinned, por encima del suelo de versiones, sin lease activo, y prioriza por
`poco demandado ∧ re-derivable ∧ barato de rehacer`. Lo caro de rehacer se retiene
más aunque sea re-derivable.

## Esqueleto de datos propuesto

- `Resource`: `rederivable` (bool), `coste_rederivacion` (enum/score),
  `retencion_politica` (TTL base, versiones mínimas, prioridad base,
  permanente sí/no).
- `Dataset`: rastro de acceso (`last_served_at`, contador de accesos) —
  registrar en el endpoint de records y en las queries de datos.
- `DatasetLease` (nueva): titular (Usuario o Application con contacto resoluble a
  email), recurso/versión, `retencion_solicitada`, `retencion_concedida`,
  `expira_en`, `estado` (activo | liberado | expirado), timestamps.

## Salvedades a respetar

- El titular del lease **debe resolver a un correo** (Usuario, o Application con
  contacto). Sin destinatario, ODM concede plazos que no sabe comunicar.
- **No prometer lo irreclamable**: sobre recurso efímero solo se arrienda lo que
  está materializado ahora; el histórico efímero no se conjura.
- Formato humano de fechas en la zona del titular (almacenamiento en UTC).
- El coste de re-derivar es real (CPU/red): ponderarlo en el desalojo.

## Apoyo en lo existente (verificado 2026-06-05)

- Demanda: `DatasetSubscription` (con `pinned_version`),
  `Application.subscribed_projects`.
- Correo: `mailer`, `eventos`, `Usuario.notificar_email`, `ApplicationNotification`.
- Datos: datasets como JSONL en `data_path` + metadatos en `dataset` (semver).
- Falta por construir: retención, prioridad, TTL, leases, rastro de acceso y
  recolector (hoy no existe ninguno).

## Cálculo de la retención concedible (control de admisión por capacidad)

El "máximo por política" no es una constante: ODM **calcula** el plazo que puede
conceder a una nueva petición a partir del espacio disponible y de lo que los
recursos programados van a acumular durante la ventana.

El espacio libre es una **curva en el tiempo**. Sobre `[ahora, ahora+T]`:

```
libre(t) = libre_ahora
           − Σ acumulación_programada(t)     # cron × tamaño/ejecución × load_mode=append
           − tamaño_estimado_nuevo(t)         # lo que ocupará el recurso solicitado
           + Σ liberaciones_previstas(t)       # leases/TTL que expiran en la ventana
           (+ reclamable_bajo_presión)         # re-derivable ∧ barato ∧ poco demandado
```

**Plazo concedible** = el mayor `T` tal que `libre(t) ≥ margen_seguridad` para todo
`t` de la ventana. Resultado de la admisión:
- cabe entero → se concede el plazo pedido;
- cabe un tramo → se concede ese ("hasta el martes, no hasta el jueves");
- no cabe ni el mínimo → "no podemos atender tu petición".

**Ingredientes** (ya en el modelo, salvo el último):
- `Resource.schedule` (cron) y `Resource.load_mode` (`append` acumula, `replace`
  no) → qué recursos son acumulables y a qué ritmo.
- `Dataset.record_count` + tamaño en disco del JSONL histórico → tasa de
  crecimiento estimada por recurso.
- Leases activos y TTL → liberaciones previstas.
- **A construir**: consciencia del disco (espacio total asignado y libre) y el
  simulador del balance.

**Honestidades del cálculo**:
- El pronóstico es **estimación**, no profecía (el volumen de una fuente cambia con
  el tiempo) → margen de seguridad y re-evaluación periódica.
- Un plazo concedido es un **contrato**: si el pronóstico empeora, ODM **no recorta
  lo ya concedido**; reacciona desalojando primero lo re-derivable/barato y
  endureciendo o denegando las **nuevas** peticiones. Nunca incumple hacia atrás.
