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
