#!/bin/sh
# update_osm_pbf.sh — Descarga un nuevo PBF de Geofabrik y fuerza la reimportación
# en el contenedor Overpass local.
#
# Variables de entorno esperadas:
#   OVERPASS_CONTAINER  — nombre del contenedor (default: odmgr_overpass)
#   OVERPASS_PBF_URL    — URL del PBF a descargar (default: spain-latest de Geofabrik)
#
# Cron: 0 3 1 * *  (día 1 de cada mes a las 3:00 AM)

set -e

CONTAINER="${OVERPASS_CONTAINER:-odmgr_overpass}"
PBF_URL="${OVERPASS_PBF_URL:-https://download.geofabrik.de/europe/spain-latest.osm.pbf}"
DEST="/data/osm/spain-latest.osm.pbf"
TEMP="${DEST}.tmp"
DB_DIR="/data/overpass_db"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Inicio de actualización OSM PBF ==="
log "Descargando: $PBF_URL"

# Descargar con reanudación (-c) por si se corta
wget -q --show-progress -c "$PBF_URL" -O "$TEMP"

# Verificar tamaño mínimo (el PBF de España supera 700 MB)
SIZE=$(wc -c < "$TEMP")
if [ "$SIZE" -lt 700000000 ]; then
    log "ERROR: archivo descargado demasiado pequeño (${SIZE} bytes). Abortando."
    rm -f "$TEMP"
    exit 1
fi

log "Descarga completada ($(( SIZE / 1024 / 1024 )) MB). Sustituyendo PBF..."
mv "$TEMP" "$DEST"

log "Deteniendo contenedor Overpass ($CONTAINER)..."
docker stop "$CONTAINER"

log "Limpiando base de datos Overpass..."
rm -rf "${DB_DIR:?}/"*

log "Reiniciando contenedor Overpass (comenzará reimportación)..."
docker start "$CONTAINER"

log "Reimportación iniciada. Tardará 30-90 minutos."
log "Sigue el progreso con: docker logs $CONTAINER -f"
log "=== Fin del script de actualización ==="
