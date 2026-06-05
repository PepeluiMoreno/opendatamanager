# Handoff de sesión — 2026-06-05

Para retomar en sesión nueva: clonar repo, leer este doc + los enlazados. Sandbox
con Postgres local funciona (usuario odm/odm, db odm); seeds y migraciones corren
en local. Push git bloqueado por proxy → usar API Git Data (patrón en historial).

## PRIMERO DE TODO
1. **Revocar el PAT de esta sesión y traer uno nuevo** (el de hoy viajó mucho).
2. Tarea acordada para abrir: **probar TODOS los recursos y arreglar los rotos**:
   arnés batch que recorre recursos vivos, instancia via factory (perfil incluido),
   ejecuta con `_preview_limit=3`, e informa OK/FALLA separando fuente caída /
   config rota / bug de fetcher. Luego arreglos uno a uno verificados en vivo.
   Sospechosos: RER (fuente rota, ver config_rer.md), ZIPs anuales (WAF exige
   User-Agent; throttling fuerte; el anual de licitaciones es pesado).

## Estado (todo en master, deploys verdes)
- Fusiones REST y HTML en especies genéricas con registros de estrategias;
  form_paged portado; modo ZIP en AtomFetcher (ventana desde/hasta).
- Modelo especie + **perfiles** (FetcherPreset bajo la especie; PLACSP CODICE
  migrado; catálogo solo especies). Power BI matriculado (38 especies).
- BDNS verificado contra spec oficial (archivado en docs/fuentes/bdns/).
- PLACSP: novedades por feed + **histórico anual 2022-2026** (10 recursos ZIP,
  desde/hasta externos, provincia en cada registro). Ficha: docs/fuentes/placsp.md.
- Historial de versiones reseteado (baseline v1).
- RBAC: rol **ejecutor** + scripts/crear_usuario.py (Miguel pendiente de crear EN
  PROD: `ODM_USER=Miguel ODM_PASSWORD=... python scripts/crear_usuario.py`).
- **Mis datos** en sidebar (perfil, contraseña, historial de leases con liberar).
- **Ciclo de vida**: diseño completo en docs/diseno_ciclo_vida_datasets.md;
  esqueleto desplegado (política en Resource, rastro de acceso en Dataset,
  DatasetLease, services/leases.py con gancho `plazo_concedible`).

## Pendientes ordenados
1. Probar/arreglar recursos (arriba).
2. Ciclo de vida, capas restantes: simulador de capacidad (consciencia de disco +
   curva de balance), recolector, provisión bajo demanda, avisos por correo, y
   seed de re-derivabilidad real (feed=efímero, zip=archivable, coste por familia).
3. RER vía Power BI: falta `query_json` (preguntar al usuario o reconstruir
   descubriendo el esquema del modelo). IDs verificados vivos en config_rer.md.
4. Usuario: aplicar deploy-healthcheck.patch a deploy.yml (editor web; el PAT no
   tenía scope workflow).
5. Deuda: módulos GraphQL duplicados (app/graphql vs app/graphql_api) — ya mordió
   tres veces. Reescribir descripciones de fetchers en lenguaje de usuario.
6. Aparcado con diseño: docs/PENDIENTE_recursos_derivados.md (cruce DIR3/BDNS/
   PLACSP, mapa de claves verificado).
