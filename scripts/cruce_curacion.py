"""Herramienta de CURACIÓN: cruce de datasets fuera del runtime de ODM.

Decisión de diseño (2026-06-06): los joins NO viven en la plataforma. ODM
publica las piezas — incluidos los puentes de identidad como datos de
referencia — y el ensamblaje analítico es de las aplicaciones consumidoras.
Este script es la herramienta offline para PRODUCIR esos puentes cuando
requieren resolución por denominación (con ambigüedades marcadas para
revisión humana), p. ej. el mapa órganos BDNS ↔ DIR3.

Uso:
  python scripts/cruce_curacion.py left.jsonl right.jsonl \
      --left-key descripcion --right-key C_DNM_UD_ORGANICA \
      --select dir3=C_ID_UD_ORGANICA --normalize --out mapa/

Salidas en --out: emparejados.jsonl, ambiguos.jsonl (varias parejas para la
misma denominación normalizada: a revisar a mano), sin_pareja.jsonl.
"""
import json
from typing import Any, Dict, List, Optional, Tuple



def _as_list(v) -> List[str]:
    if isinstance(v, str):
        v = json.loads(v) if v.strip() else []
    return list(v or [])


def _as_dict(v) -> Dict[str, str]:
    if isinstance(v, str):
        v = json.loads(v) if v.strip() else {}
    return dict(v or {})


def _names(v) -> List[str]:
    """'left_resource' admite un nombre o un JSON array de nombres."""
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            return [str(x) for x in json.loads(s)]
        return [s]
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _norm_key(v: Any) -> Any:
    """Normaliza una clave textual para cruces por denominación: mayúsculas,
    sin acentos, espacios colapsados. No-strings se devuelven tal cual."""
    if not isinstance(v, str):
        return v
    import unicodedata
    s = unicodedata.normalize("NFKD", v)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def cruzar(left: List[Dict], right: List[Dict], *, left_key: str, right_key: str,
           match: str = "eq", join: str = "enrich",
           select: Dict[str, str] | None = None,
           normalize_keys: bool = False) -> List[Dict[str, Any]]:
    """Núcleo puro del cruce. Índice del right por clave; con match=in_array la
    clave derecha es una lista y se indexa cada elemento. Con normalize_keys
    las claves textuales casan sin distinguir mayúsculas/acentos/espaciado
    (cruces por denominación). A igualdad de clave gana la última fila del
    right (datasets ya deduplicados aguas arriba)."""
    nk = _norm_key if normalize_keys else (lambda x: x)
    indice: Dict[Any, Dict] = {}
    for r in right:
        k = r.get(right_key)
        claves = k if (match == "in_array" and isinstance(k, list)) else [k]
        for c in claves:
            if c is not None:
                indice[nk(c)] = r

    if select:
        campos = select
    else:
        campos = {c: c for c in (right[0].keys() if right else []) if c != right_key}

    out: List[Dict[str, Any]] = []
    for l in left:
        pareja = indice.get(nk(l.get(left_key)))
        if pareja is None:
            if join == "inner":
                continue
            out.append(dict(l))
        else:
            fila = dict(l)
            for salida, origen in campos.items():
                fila[salida] = pareja.get(origen)
            out.append(fila)
    return out


def _cargar(path):
    import json as _j
    with open(path, encoding="utf-8") as f:
        return [_j.loads(l) for l in f if l.strip()]


def main():
    import argparse, json as _j, os
    ap = argparse.ArgumentParser(description="Cruce de curación con marcado de ambigüedades")
    ap.add_argument("left"); ap.add_argument("right")
    ap.add_argument("--left-key", required=True); ap.add_argument("--right-key", required=True)
    ap.add_argument("--select", default="", help="salida=campo_del_right, separadas por comas")
    ap.add_argument("--match", default="eq", choices=["eq", "in_array"])
    ap.add_argument("--normalize", action="store_true")
    ap.add_argument("--out", default="cruce_out")
    a = ap.parse_args()
    left, right = _cargar(a.left), _cargar(a.right)
    select = dict(p.split("=", 1) for p in a.select.split(",") if "=" in p) or None

    # Ambigüedades: claves del right que colisionan tras normalizar
    nk = _norm_key if a.normalize else (lambda x: x)
    conteo = {}
    for r in right:
        k = nk(r.get(a.right_key))
        if k is not None:
            conteo[k] = conteo.get(k, 0) + 1
    ambiguas = {k for k, n in conteo.items() if n > 1}

    filas = cruzar(left, right, left_key=a.left_key, right_key=a.right_key,
                   match=a.match, join="enrich", select=select, normalize_keys=a.normalize)
    os.makedirs(a.out, exist_ok=True)
    salidas = {n: open(os.path.join(a.out, f"{n}.jsonl"), "w", encoding="utf-8")
               for n in ("emparejados", "ambiguos", "sin_pareja")}
    marca = set(select or {}) or None
    n = {"emparejados": 0, "ambiguos": 0, "sin_pareja": 0}
    for f in filas:
        con_pareja = any(f.get(c) is not None for c in (marca or f.keys()))
        clave = nk(f.get(a.left_key))
        destino = ("ambiguos" if (con_pareja and clave in ambiguas)
                   else "emparejados" if con_pareja else "sin_pareja")
        salidas[destino].write(_j.dumps(f, ensure_ascii=False) + "\n")
        n[destino] += 1
    for fh in salidas.values():
        fh.close()
    print(f"[cruce_curacion] {n['emparejados']} emparejados, {n['ambiguos']} ambiguos (revisar), "
          f"{n['sin_pareja']} sin pareja → {a.out}/")


if __name__ == "__main__":
    main()
