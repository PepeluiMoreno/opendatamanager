# PLACSP — ficha de fuente (verificada)

**Regla**: todo lo de esta ficha está verificado en vivo (2026-06-05) o procede de
las páginas índice oficiales. Nada de memoria.

## Novedades (feeds de sindicación)

Cadenas ATOM con `rel_next` hacia atrás, formato CODICE 2.07:
- Licitaciones: `contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom`
- Contratos menores: `.../sindicacion_1143/contratosMenoresPerfilesContratantes.atom`
Cosecha incremental por marca de agua (perfil `PLACSP CODICE`); ventana
temporal `[desde, hasta]` como parámetros externos del recurso.

## Histórico (repositorio de ZIPs)

Índices oficiales (Hacienda → Gobierno Abierto → Datos Abiertos):
`licitacionescontratante.aspx` y `contratosmenores.aspx`. Los ZIPs viven en
`contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_{canal}/` y contienen
los mismos ficheros ATOM del feed:

- Licitaciones (canal 643): anuales `_2012.zip` … `_2026.zip` + mensuales del
  año en curso (`_YYYYMM.zip`).
- Contratos menores (canal 1143): anuales `_2018.zip` … `_2026.zip` + mensuales.

**Avisos verificados**: el WAF devuelve 403 o un HTML de redirección si no se
envía un `User-Agent` razonable (los recursos lo fijan en `headers`); un HEAD/GET
sin UA puede devolver 200 con HTML — comprobar siempre los bytes mágicos `PK`.
La transferencia es lenta (decenas de KB/s observados); los anuales pesan
decenas/cientos de MB.

## Recursos ODM

- Novedades: 6 recursos de feed (manifiestos `placsp_*.json`, `madrid_licitaciones.json`).
- Histórico: ventana rodante de **5 años** (2022–2026) por familia, un recurso por
  año sobre el ZIP anual con el modo archivo del AtomFetcher
  (`placsp_menores_historico.json`, `placsp_licitaciones_historico.json`).
  Ejecución bajo demanda (sin schedule); `desde/hasta` externos para acotar dentro
  del año. **Rotación**: al entrar un año nuevo, añadir su recurso al manifiesto y
  retirar el más antiguo (hoy manual; candidato a automatizarse).

## Dimensión provincial

El `field_map` CODICE extrae `provincia` y `provincia_codigo`
(CountrySubentity/Code). Verificado en el feed vivo de menores: ~82% de entradas
con provincia; el resto declara nivel país ("España"/"ES") — calidad de origen,
no de la cosecha. La segmentación física por provincia, si se quiere
materializada, es caso de uso de la especie de cruce/derivación aparcada
(`docs/PENDIENTE_recursos_derivados.md`).
