# incidencias_batch.md — batería de fuentes "naturaleza religiosa"

Protocolo: las fuentes se VERIFICAN en vivo antes de manifestar (lección Manus).
Nada se commitea/despliega sin gatillo explícito (despliega / ejecuta / dale / sube).

## Estado

- [x] **RER (MAPER)** — OPERATIVO en master (4607391). manifests/rer_entidades.json.
      Especie HTML genérico, navigation=searchloop, pivote filtro.confesion.

- [x] **Fundaciones de competencia estatal** — DESPLEGADO. manifests/fundaciones_estatales.json
      Buscador: https://fundosbuscador.mjusticia.gob.es/fundosbuscador/
      Mecánica (probada en vivo 2026-06-11):
        · Sesión:     GET  cargaBuscador.action?lang=es_es  → JSESSIONID
        · Búsqueda:   POST buscarResultadoBusqueda.action   (pivote filtro.provincia, 52 prov.)
        · Paginación: GET  actualizarResultadoBusqueda.action?paginacion.index=N  (30/pág.)
        · Listado:    Nombre, Provincia, FINES (texto completo de fines — señal religiosa ya aquí)
        · Detalle:    DetalleFundacion.action?idFundacion=N  → fundadores, patronos, directivos
      Volumen: Madrid 3.089; total nacional ~ decenas de miles. Crawl mensual.
      Reutiliza el fetcher searchloop existente: SOLO manifiesto, sin código nuevo.
      Smoke test preview: 9.6s, NIF capturado (G…). Detalle trae NIF -> cruce directo con BDNS.

## Cola de fuentes por verificar (siguiente)

- [ ] Registros autonómicos de asociaciones (Madrid, CLM publican CSV — verificar URLs reales)
- [ ] BDNS — cruce para NIF (ancla letra R) por denominación normalizada RER/Fundaciones ↔ BDNS

## Notas de gobernanza ODM

- ODM es productor neutral: el manifiesto declara la fuente; el scoring de "naturaleza
  religiosa" (incl. filtrar por filtro.fines=religion) es del CONSUMIDOR, no de ODM.
  La cosecha neutral pivota por provincia y trae TODO; el filtrado por fines va aguas abajo.


## Nodriza de catálogo (DCAT) — DESPLEGADO

- [x] Especie "Catálogo DCAT" (CatalogFetcher): nave nodriza sobre datos.gob.es.
      modos=["extraer","descubrir"]. propose() emite 1 candidato autodescriptivo
      por distribución (target_fetcher_code + url + format). Verificado en vivo:
      51 candidatos asociaciones+fundaciones, 0 ruido.
- [x] Promoción heterogénea: ResourceCandidate gana target_fetcher_code/target_params
      (migración cand_target_1, IF NOT EXISTS). promote_candidate usa la especie-destino
      del candidato (padre DESCUBRE / hijo EXTRAE con File Download), no la del padre.
- [x] Hook propose() en el manager: descubridores de catálogo saltan infer()
      (que es agrupación por rutas, propia de Web Tree). Web Tree intacto.
- [x] Manifiesto madre: manifests/catalogo_asociaciones_fundaciones.json (genera_colecciones).

NOTA: esto SUPERSEDE manifestar a mano los 16 registros autonómicos: ahora se
      descubren. Tras desplegar: ejecutar la madre (discovering) y promover en UI
      los candidatos buenos (preferir CSV sobre JSON; Aragón trae 1 fichero/provincia).

## Diferido (siguiente fase)

- [ ] Recursión multinivel (meta-meta-recurso): relajar es_coleccion (hoy exige
      parent_resource_id IS NULL) a "raíz O nodo cualificado" + control de
      profundidad/ciclos en el discovering. El árbol (parent_resource_id) ya existe.

## Cola UI (pendiente, sin gatillo)

- [ ] Lista de recursos: la columna "Apps" (aplicaciones) debe etiquetarse "Subsc."
      (suscripciones). Coherente con el rename Application->Subscriber ya en master.
      Buscar el header de columna en el componente de la tabla de recursos del frontend.
