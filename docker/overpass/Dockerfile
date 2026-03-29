FROM wiktorn/overpass-api

# Entrypoint personalizado: convierte PBF a OSM con osmium (ya incluido en la
# imagen base) y lo importa directamente, sin pasar por bunzip2.
# Después delega en el entrypoint original para arrancar los servicios.
COPY overpass_entrypoint.sh /overpass_entrypoint.sh
RUN chmod +x /overpass_entrypoint.sh

ENTRYPOINT ["/bin/bash", "/overpass_entrypoint.sh"]
