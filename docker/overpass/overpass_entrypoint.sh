#!/bin/bash
# overpass_entrypoint.sh — Entrypoint personalizado para wiktorn/overpass-api.
#
# El script original (init_osm3s.sh) solo acepta osm.bz2.
# Este entrypoint usa osmium (ya incluido en la imagen) para convertir
# el PBF a OSM XML y lo importa directamente con update_database.

set -e

DB_DIR="/db"
EXEC_DIR="/app/bin"
PBF_URL="${OVERPASS_PLANET_URL:-http://osm-updater:8080/spain-latest.osm.pbf}"
# Guardado en el volumen persistente para sobrevivir reinicios del contenedor
TMP_PBF="$DB_DIR/.tmp_planet.osm.pbf"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [overpass-init] $*"; }

mkdir -p "$DB_DIR"

# ── Si la BD ya existe, arrancar directamente ─────────────────────────────────
if [ -f "$DB_DIR/osm_base_data" ]; then
    log "Base de datos existente detectada. Saltando importación."
else
    log "Base de datos no encontrada. Iniciando importación desde PBF..."

    # Reutilizar el PBF si ya se descargó (evita re-descarga en reinicios)
    PBF_SIZE=$(stat -c %s "$TMP_PBF" 2>/dev/null || echo 0)
    if [ "$PBF_SIZE" -lt 700000000 ]; then
        log "Descargando: $PBF_URL"
        wget -q --show-progress -c "$PBF_URL" -O "$TMP_PBF"
        log "Descarga completa: $(( $(stat -c %s "$TMP_PBF") / 1024 / 1024 )) MB"
    else
        log "PBF ya en disco: $(( PBF_SIZE / 1024 / 1024 )) MB. Saltando descarga."
    fi

    # --flush-size conservador: RAM/6, mínimo 1 GB, máximo 2 GB.
    # Con RAM/2 el OOM killer mataba el proceso en máquinas con ≤8 GB.
    RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    RAM_GB=$(( RAM_KB / 1024 / 1024 ))
    FLUSH_SIZE=$(( RAM_GB / 6 ))
    [ "$FLUSH_SIZE" -lt 1 ] && FLUSH_SIZE=1
    [ "$FLUSH_SIZE" -gt 2 ] && FLUSH_SIZE=2
    log "RAM detectada: ${RAM_GB} GB → --flush-size=${FLUSH_SIZE} GB"
    log "Importando con osmium → update_database (puede tardar 30-90 min)..."
    osmium cat "$TMP_PBF" -o - --output-format osm \
        | "$EXEC_DIR/update_database" --db-dir="$DB_DIR/" --compression-method=no --flush-size="${FLUSH_SIZE}"

    rm -f "$TMP_PBF"
    log "Importación completada."
fi

# ── Arrancar el stack normal de overpass (supervisord) ────────────────────────
log "Iniciando servicios Overpass..."
exec /entrypoint.sh
