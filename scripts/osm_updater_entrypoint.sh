#!/bin/sh
# osm_updater_entrypoint.sh
# Arranca el servicio osm-updater:
#   1. Si el PBF no existe o está incompleto → lo descarga automáticamente.
#   2. Configura el cron mensual para mantener los datos frescos.
#   3. Se queda corriendo como proceso de crond.
#
# El healthcheck de Docker marca el contenedor como "healthy" cuando el PBF
# supera 700 MB, lo que dispara el arranque automático de overpass (depends_on).

set -e

PBF="/data/osm/spain-latest.osm.pbf"
BZ2="/data/osm/spain-latest.osm.bz2"
PBF_URL="${OVERPASS_PBF_URL:-https://download.geofabrik.de/europe/spain-latest.osm.pbf}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [osm-updater] $*"; }

mkdir -p /data/osm /var/log

# ── Descarga inicial si el PBF no existe o está incompleto ────────────────────
PBF_SIZE=$(stat -c %s "$PBF" 2>/dev/null || echo 0)
if [ "$PBF_SIZE" -lt 700000000 ]; then
    log "PBF ausente o incompleto (${PBF_SIZE} bytes). Descargando España completa..."
    log "URL: $PBF_URL"
    wget -q --show-progress -c "$PBF_URL" -O "${PBF}.tmp"
    DOWNLOADED=$(stat -c %s "${PBF}.tmp" 2>/dev/null || echo 0)
    if [ "$DOWNLOADED" -lt 700000000 ]; then
        log "ERROR: descarga incompleta (${DOWNLOADED} bytes). Reintentando en el próximo arranque."
        rm -f "${PBF}.tmp"
        exit 1
    fi
    mv "${PBF}.tmp" "$PBF"
    log "Descarga completa: $(( DOWNLOADED / 1024 / 1024 )) MB"
else
    log "PBF encontrado: $(( PBF_SIZE / 1024 / 1024 )) MB."
fi

# ── Conversión PBF → osm.bz2 (formato que acepta wiktorn/overpass-api) ────────
# init_osm3s.sh usa bunzip2 directamente — solo acepta osm.bz2, no PBF.
BZ2_SIZE=$(stat -c %s "$BZ2" 2>/dev/null || echo 0)
if [ "$BZ2_SIZE" -lt 100000000 ]; then
    log "Convirtiendo PBF a osm.bz2 con osmium (puede tardar 30-60 min)..."
    osmium cat "$PBF" -o "${BZ2}.tmp" --overwrite
    mv "${BZ2}.tmp" "$BZ2"
    log "Conversión completa: $(( $(stat -c %s "$BZ2") / 1024 / 1024 )) MB"
else
    log "osm.bz2 encontrado: $(( BZ2_SIZE / 1024 / 1024 )) MB."
fi

# ── Configurar cron mensual ───────────────────────────────────────────────────
CRON_ENV="OVERPASS_CONTAINER=${OVERPASS_CONTAINER} OVERPASS_PBF_URL=${OVERPASS_PBF_URL}"
echo "0 3 1 * * ${CRON_ENV} /update_osm_pbf.sh >> /var/log/osm_update.log 2>&1" | crontab -
log "Cron mensual configurado (día 1 a las 03:00)."

# ── Servidor HTTP para que overpass descargue el osm.bz2 por red local ────────
log "Sirviendo datos en http://osm-updater:8080/"
python3 -m http.server 8080 --directory /data/osm &

log "Iniciando crond..."
exec crond -f -l 6
