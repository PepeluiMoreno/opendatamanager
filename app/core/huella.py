"""Huella de identidad de un recurso.

La identidad de un Resource no es su `name` (etiqueta humana) sino *qué* trae:
el conjunto de pares (clave, valor) de sus `params`. Dos recursos con la misma
huella son el mismo recurso y NO deben duplicarse.

Reglas (acordadas con el dueño de ODM):
- Se hashea SOLO `params`. Los campos operativos del Resource (name, schedule,
  active, target_table, description) no son params y quedan fuera por construcción.
- Se prescinde del flag `is_external`: basta clave + valor. Para params externos,
  el `value` debe ser la REFERENCIA al secreto, nunca el secreto resuelto.
- Forma canónica determinista: pares ordenados por clave, valores como string,
  JSON compacto; SHA-256 en hexadecimal.

Esto es distinto de `Resource.manifest_hash` (hash del manifiesto canónico
completo, usado para versionado/detección de conflictos). La huella sirve para
*identidad/deduplicación*; el manifest_hash para *cambio de definición*.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Tuple


def huella_params(pares: Iterable[Tuple[str, object]]) -> str:
    """Calcula la huella SHA-256 de un conjunto de pares (clave, valor).

    `pares` es cualquier iterable de tuplas (key, value); por ejemplo,
    ``[(p.key, p.value) for p in input.params]`` o las filas de ResourceParam.
    """
    norm = sorted(
        ((str(k), "" if v is None else str(v)) for k, v in pares),
        key=lambda kv: kv[0],
    )
    canon = json.dumps(norm, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def params_bound(pares: Iterable[Tuple[str, object]]) -> bool:
    """¿Están todos los params estáticos *acotados* (con valor)?

    La identidad solo es resoluble cuando todos los params estáticos tienen valor.
    Un valor vacío indica un parámetro sin acotar (borrador/plantilla a rellenar):
    en ese caso NO se calcula huella todavía (params_hash = NULL) y el recurso no
    se deduplica hasta que se acote. Nota: un literal como ``{pivot}`` SÍ está
    acotado (es parte de la definición); lo que se resuelve en runtime es su valor,
    que viaja por execution_params y nunca entra aquí.
    """
    return all((v is not None and str(v).strip() != "") for _, v in pares)
