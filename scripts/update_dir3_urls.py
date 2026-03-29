"""Actualiza las URLs de los resources DIR3 con fuentes accesibles."""
import sys
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models import Resource, ResourceParam
from uuid import uuid4

db = SessionLocal()

updates = {
    "DIR3 - Unidades Organicas (CSV)": {
        "url": "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=csv",
        "format": "csv",
        "encoding": "utf-8",
        "timeout": "120",
        "batch_size": "5000",
    },
    "DIR3 - Unidades Organicas (REST PAe)": {
        "url": "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=json",
        "method": "GET",
        "content_field": "units",
        "id_field": "code",
        "timeout": "120",
    },
}

for resource_name, new_params in updates.items():
    r = db.query(Resource).filter(Resource.name == resource_name).first()
    if not r:
        print(f"  Resource '{resource_name}' no encontrado")
        continue
    # Borrar params existentes y recrear
    for p in list(r.params):
        db.delete(p)
    db.flush()
    for k, v in new_params.items():
        db.add(ResourceParam(id=uuid4(), resource_id=r.id, key=k, value=v))
    print(f"✓ '{resource_name}' actualizado")

# La URL XLSX del portal oficial la dejamos pero marcamos como pendiente de verificar
r_xlsx = db.query(Resource).filter(Resource.name == "DIR3 - Unidades Organicas (XLSX)").first()
if r_xlsx:
    # Actualizar a una URL alternativa conocida del portal SEAP
    for p in r_xlsx.params:
        if p.key == "url":
            p.value = "https://administracionelectronica.gob.es/ctt/resources/Soluciones/238/descargas/DIR3-USU-12101-provision-unidades.xlsx"
            break
    print(f"✓ URL XLSX actualizada (puede requerir acceso desde red española)")

db.commit()
db.close()
print("Done.")
