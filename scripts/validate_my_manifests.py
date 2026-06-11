
import json
import os
import sys

# Añadir el directorio raíz al path para poder importar app.services.manifests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.manifests import validate_manifest

# Códigos de fetchers conocidos en la aplicación (según la base de datos o lo esperado)
# 'Power BI' y 'API REST' son los que usamos en los manifiestos.
KNOWN_FETCHER_CODES = ["HTML (genérico)", "API REST", "Web Tree", "CKAN", "Power BI"]

def validate_file(filepath):
    print(f"Validando {filepath}...")
    try:
        with open(filepath, 'r') as f:
            manifest = json.load(f)
        
        errors = validate_manifest(manifest, KNOWN_FETCHER_CODES)
        if errors:
            print(f"  [ERROR] Se encontraron {len(errors)} errores:")
            for err in errors:
                print(f"    - {err}")
            return False
        else:
            print("  [OK] El manifiesto es válido.")
            return True
    except Exception as e:
        print(f"  [ERROR] Error al leer o procesar el archivo: {e}")
        return False

if __name__ == "__main__":
    manifests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../manifests'))
    my_manifests = ["rer_entidades.json", "rna_asociaciones.json", "lugares_culto.json"]
    
    all_ok = True
    for m in my_manifests:
        path = os.path.join(manifests_dir, m)
        if not validate_file(path):
            all_ok = False
    
    if all_ok:
        print("\nTodos los manifiestos han pasado la validación de estructura.")
        sys.exit(0)
    else:
        print("\nAlgunos manifiestos tienen errores.")
        sys.exit(1)
