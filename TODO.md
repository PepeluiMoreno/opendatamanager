# TODO

## Despliegue y CI/CD

- Migrar el despliegue de produccion a imagenes inmutables publicadas en `ghcr.io`, evitando `git pull` en el servidor.
- Separar claramente `build` y `deploy`:
  - CI construye y publica imagenes.
  - Produccion solo hace `docker compose pull` y `docker compose up -d`.
- Definir imagenes versionadas por tag y/o SHA de commit para facilitar rollback y trazabilidad.
- Cambiar `docker-compose.prod.yml` para usar `image:` en backend/frontend en lugar de `build:`.
- Mantener `.env.production` fuera del repo e inyectarlo solo como secreto en entorno de despliegue.
- Reducir el codigo presente en produccion al minimo necesario:
  - idealmente solo `compose`, `env` y volumenes persistentes.
- Evaluar si conviene un repositorio/stack de despliegue separado del repositorio de aplicacion.

## Endurecimiento adicional

- Revisar si el usuario de despliegue puede reducir permisos en host sin perder capacidad operativa.
- Mantener contenedores sin root donde sea posible.
- Documentar estrategia de rotacion de secretos y claves SSH.
- Documentar procedimiento de rollback de despliegue.

## Propuesta de siguiente fase

- Fase actual:
  - desplegar con el flujo endurecido ya preparado.
- Fase siguiente:
  - migrar completamente a GHCR como mecanismo principal de entrega para las ultimas fases del proyecto.
