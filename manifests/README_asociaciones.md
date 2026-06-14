# Colección «Asociaciones»

Productor **neutral**: ODM expone registros oficiales de asociaciones de España
*tal cual los publica cada fuente*. La clasificación, la tipología y el índice de
registros (caracterización con certeza) son responsabilidad del **consumidor**, no
de ODM.

## Estructura
- **Curados directos** (una ficha por registro oficial): 10 autonómicos con NIF
  (Andalucía, Asturias, Baleares, Canarias, Castilla-La Mancha, Cataluña, Galicia,
  Murcia, País Vasco, La Rioja), Aragón (3 bases provinciales, sin NIF pero con
  Temática que incluye «025 RELIGIOSAS»), y municipales (Madrid ciudad, Zaragoza,
  San Lorenzo de El Escorial).
- **Nodrizas (descubridoras)**: `aoc_asociaciones_municipales` (municipales
  catalanes >50k vía CKAN seu-e) y `catalogo_asociaciones_fundaciones` (catch-all
  DCAT sobre datos.gob.es para CCAA no curadas).

## Principios de ingesta
1. **Conservar TODAS las columnas nativas.** No recortar. Los **códigos internos
   del registro de origen** (nº de inscripción, código de registro) son la clave
   estable *dentro* de la fuente y sirven para la **puesta al día** (casar
   alta/baja/modificación al refrescar). El parser solo poda columnas
   enteramente vacías, que no llevan información.
2. **NIF/CIF = código externo** para cruce entre registros (BDNS, inmatriculaciones).
   **Código interno = clave de actualización** dentro de la fuente. No confundirlos.
3. Documentar en `description` qué señal aporta la fuente (NIF / fines en texto /
   clasificación nativa) — es metadato de contenido, neutral.

## Cómo añadir un registro nuevo (sin romper nada)
1. Crear `manifests/<fuente>_registro_asociaciones.json` con el fetcher adecuado
   (File Download / API REST / Compressed File / Catálogo DCAT…) y
   `"collection": "Asociaciones"`.
2. **Añadir el dominio de la fuente** al `drop_url_contains` del catch-all
   (`catalogo_asociaciones_fundaciones.json`) para que la nodriza no lo
   redescubra y duplique.
3. Rellenar `description` con la señal (NIF/fines/clasificación) y el código
   interno de origen.
4. Validar (`validate_manifest`) y desplegar.

> Sin NIF no es descarte: un registro entra si aporta NIF **y/o** señal de
> fines/clasificación. La señal de fines es la materia prima de la caracterización
> (lado cliente); el NIF es solo el join-key.
