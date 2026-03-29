#!/bin/sh
# entrypoint.sh — osm-updater
# 1. Descarga el PBF si no existe o está incompleto.
# 2. Lo sirve por HTTP para que el contenedor overpass lo descargue.
# 3. Configura cron mensual de actualización.

set -e

PBF="/data/osm/spain-latest.osm.pbf"
PBF_URL="${OVERPASS_PBF_URL:-https://download.geofabrik.de/europe/spain-latest.osm.pbf}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [osm-updater] $*"; }

mkdir -p /data/osm /var/log

# ── Descarga inicial ──────────────────────────────────────────────────────────
PBF_SIZE=$(stat -c %s "$PBF" 2>/dev/null || echo 0)
if [ "$PBF_SIZE" -lt 700000000 ]; then
    log "PBF ausente o incompleto (${PBF_SIZE} bytes). Descargando España completa..."
    wget -q --show-progress -c "$PBF_URL" -O "${PBF}.tmp"
    DOWNLOADED=$(stat -c %s "${PBF}.tmp" 2>/dev/null || echo 0)
    if [ "$DOWNLOADED" -lt 700000000 ]; then
        log "ERROR: descarga incompleta (${DOWNLOADED} bytes). Reintentando..."
        rm -f "${PBF}.tmp"
        exit 1
    fi
    mv "${PBF}.tmp" "$PBF"
    log "Descarga completa: $(( DOWNLOADED / 1024 / 1024 )) MB"
else
    log "PBF encontrado: $(( PBF_SIZE / 1024 / 1024 )) MB."
fi

# ── Servidor HTTP ─────────────────────────────────────────────────────────────
log "Sirviendo PBF en http://osm-updater:8080/"
python3 -m http.server 8080 --directory /data/osm &

# ── Cron mensual ─────────────────────────────────────────────────────────────
CRON_ENV="OVERPASS_CONTAINER=${OVERPASS_CONTAINER} OVERPASS_PBF_URL=${OVERPASS_PBF_URL}"
echo "0 3 1 * * ${CRON_ENV} /update_osm_pbf.sh >> /var/log/osm_update.log 2>&1" | crontab -
log "Cron mensual configurado (día 1 a las 03:00)."

log "Iniciando crond..."
exec crond -f -l 6
