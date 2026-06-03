"""
Guard de unicidad de la capa de fetchers.

Tras unificar la capa de fetchers, la única fuente válida es app/fetchers/.
Estos tests fallan si reaparece un segundo fetchers_enum.py o el subpaquete
huérfano app/builders/fetchers/, evitando que vuelvan a divergir.
"""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_unico_fetchers_enum():
    encontrados = list(APP_DIR.rglob("fetchers_enum.py"))
    # Ignorar artefactos de bytecode
    encontrados = [p for p in encontrados if "__pycache__" not in p.parts]
    assert len(encontrados) == 1, (
        f"Debe existir un único fetchers_enum.py (canónico en app/fetchers/). "
        f"Encontrados: {[str(p) for p in encontrados]}"
    )
    assert encontrados[0] == APP_DIR / "fetchers" / "fetchers_enum.py", (
        f"El fetchers_enum.py canónico debe vivir en app/fetchers/. "
        f"Encontrado en: {encontrados[0]}"
    )


def test_sin_subpaquete_builders_fetchers():
    huerfano = APP_DIR / "builders" / "fetchers"
    assert not huerfano.exists(), (
        "app/builders/fetchers/ es código muerto y debe permanecer eliminado; "
        "la capa de fetchers vive en app/fetchers/."
    )
