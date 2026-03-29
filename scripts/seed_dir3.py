"""Registra el fetcher FileDownload y los tres resources DIR3 en BD."""
import sys
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models import Fetcher, Resource, ResourceParam
from uuid import uuid4

db = SessionLocal()

# 1. Fetcher FileDownload
fd = db.query(Fetcher).filter(Fetcher.code == "FileDownload").first()
if not fd:
    fd = Fetcher(
        id=uuid4(),
        code="FileDownload",
        description="Descarga ficheros XLSX, CSV o TSV desde URL directa y convierte filas en registros.",
        class_path="app.fetchers.file_download.FileDownloadFetcher",
    )
    db.add(fd)
    db.flush()
    print(f"✓ Fetcher FileDownload creado: {fd.id}")
else:
    print(f"  Fetcher FileDownload ya existe: {fd.id}")

# 2. Fetcher PaginatedRest (código real en BD)
pr = db.query(Fetcher).filter(Fetcher.code == "API REST Paginada").first()
if pr:
    print(f"  Fetcher 'API REST Paginada': {pr.id}")
else:
    print("  AVISO: Fetcher 'API REST Paginada' no encontrado")


def make_resource(name, fetcher, params):
    r = db.query(Resource).filter(Resource.name == name).first()
    if r:
        print(f"  Resource '{name}' ya existe")
        return
    r = Resource(
        id=uuid4(),
        name=name,
        publisher="MPTFP - Secretaria de Estado de Funcion Publica",
        fetcher_id=fetcher.id,
        active=True,
    )
    db.add(r)
    db.flush()
    for k, v in params.items():
        db.add(ResourceParam(id=uuid4(), resource_id=r.id, key=k, value=str(v)))
    print(f"✓ Resource '{name}' creado: {r.id}")


# DIR3 — XLSX (portal administracionelectronica.gob.es)
make_resource("DIR3 - Unidades Organicas (XLSX)", fd, {
    "url": "https://administracionelectronica.gob.es/ctt/resources/Soluciones/238/descargas/DIR3-USU-12101-provision-unidades.xlsx?idIniciativa=238&idElemento=2226",
    "format": "xlsx",
    "sheet": "0",
    "timeout": "120",
    "batch_size": "1000",
})

# DIR3 — CSV (datos.gob.es)
make_resource("DIR3 - Unidades Organicas (CSV)", fd, {
    "url": "https://datos.gob.es/es/catalogo/e05188501-directorio-comun-de-unidades-organicas-y-oficinas-dir3.csv",
    "format": "csv",
    "encoding": "utf-8-sig",
    "timeout": "120",
    "batch_size": "5000",
})

# DIR3 — REST API PAe
if pr:
    make_resource("DIR3 - Unidades Organicas (REST PAe)", pr, {
        "url": "https://administracionelectronica.gob.es/REA/ws/rest/unidades",
        "method": "GET",
        "content_field": "unidades",
        "page_param": "pagina",
        "page_size_param": "limite",
        "page_size": "1000",
        "id_field": "codigo",
        "timeout": "60",
    })

db.commit()
db.close()
print("Done.")
