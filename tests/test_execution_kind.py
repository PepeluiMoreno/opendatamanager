"""Procesos tipados: una ejecución es 'extraccion' por defecto; las de una
Colección que rastrea se etiquetan 'discovering'."""
from app.models import ResourceExecution


def test_kind_por_defecto_extraccion():
    e = ResourceExecution(resource_id=__import__("uuid").uuid4())
    # el default de columna se aplica al insertar; en memoria comprobamos el valor declarado
    assert ResourceExecution.kind.default.arg == "extraccion"


def test_kind_admite_discovering():
    e = ResourceExecution(resource_id=__import__("uuid").uuid4(), kind="discovering")
    assert e.kind == "discovering"
