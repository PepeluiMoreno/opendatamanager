FROM docker:27-cli

RUN apk add --no-cache wget python3

COPY entrypoint.sh /entrypoint.sh
COPY update_osm_pbf.sh /update_osm_pbf.sh
RUN chmod +x /entrypoint.sh /update_osm_pbf.sh

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
