#!/bin/bash
# Bootstrap manual de la base de datos para ODMGR
set -e

if [[ "$ALLOW_DB_BOOTSTRAP" != "yes" ]]; then
  echo "Debes establecer ALLOW_DB_BOOTSTRAP=yes para ejecutar este script."
  exit 1
fi

# Cargar variables de entorno
if [[ -f "$1" ]]; then
  export $(grep -v '^#' "$1" | xargs)
fi

psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_DBNAME" -f ./scripts/init.sql

echo "Bootstrap de base de datos completado."
