#!/bin/bash
# overpass_entrypoint.sh — Entrypoint personalizado para wiktorn/overpass-api.
#
# El script original (init_osm3s.sh) solo acepta osm.bz2.
# Este entrypoint usa osmium (ya incluido en la imagen) para convertir
# el PBF descargado directamente a osm y lo importa sin pasar por bz2.

set -e

DB_DIR="/db"
EXEC_DIR="/app/bin"
PBF_URL="${OVERPASS_PLANET_URL:-http://osm-updater:8080/spain-latest.osm.pbf}"
TMP_PBF="/tmp/planet.osm.pbf"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [overpass-init] $*"; }

# ── Si la BD ya existe, arrancar directamente ─────────────────────────────────
if [ -f "$DB_DIR/osm_base_data" ]; then
    log "Base de datos existente detectada. Saltando importación."
else
    log "Base de datos no encontrada. Iniciando importación desde PBF..."
    log "Descargando: $PBF_URL"

    mkdir -p "$DB_DIR"
    wget -q --show-progress "$PBF_URL" -O "$TMP_PBF"
    log "Descarga completa: $(( $(stat -c %s $TMP_PBF) / 1024 / 1024 )) MB"

    log "Importando con osmium → update_database (puede tardar 30-90 min)..."
    osmium cat "$TMP_PBF" -o - --output-format osm \
        | "$EXEC_DIR/update_database" --db-dir="$DB_DIR/" --compression=none

    rm -f "$TMP_PBF"
    log "Importación completada."
fi

# ── Arrancar el stack normal de overpass (supervisord) ────────────────────────
log "Iniciando servicios Overpass..."
exec /entrypoint.sh
