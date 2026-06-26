"""Estrategia de extracción `geo_ine_jerarquia`.

Construye la jerarquía territorial completa de España (País → Comunidad Autónoma →
Provincia → Municipio) a partir de un ÚNICO fichero del INE: la «Relación de
municipios y códigos por provincias» (`codmun/NNcodmun.xlsx`), cuyas filas traen
`CODAUTO` (cód. CCAA), `CPRO` (cód. provincia), `CMUN` (cód. municipio) y `NOMBRE`
(nombre del municipio). Los nombres de CCAA y provincia (que ese fichero NO trae)
se completan con el nomenclátor oficial del INE embebido aquí (19 CCAA + 52
provincias; datos de referencia estables).

Salida: una fila por nodo, con el mismo contrato jerárquico que `tree_flatten`
(`nivel`, `padre_id`, `padre_descripcion`, `ruta`) más `codigo_ine`, `nombre` y
`tipo` ∈ {pais, comunidad, provincia, municipio}. El consumidor reconstruye el
árbol casando `padre_id` → `codigo_ine` (padre_id del país es null).
"""
from typing import Any, Dict, List, Optional


# Nomenclátor oficial INE — Comunidades Autónomas (CODAUTO de 2 dígitos)
CCAA_NOMBRES: Dict[str, str] = {
    "01": "Andalucía",
    "02": "Aragón",
    "03": "Asturias, Principado de",
    "04": "Balears, Illes",
    "05": "Canarias",
    "06": "Cantabria",
    "07": "Castilla y León",
    "08": "Castilla - La Mancha",
    "09": "Cataluña",
    "10": "Comunitat Valenciana",
    "11": "Extremadura",
    "12": "Galicia",
    "13": "Madrid, Comunidad de",
    "14": "Murcia, Región de",
    "15": "Navarra, Comunidad Foral de",
    "16": "País Vasco",
    "17": "Rioja, La",
    "18": "Ceuta",
    "19": "Melilla",
}

# Nomenclátor oficial INE — Provincias (CPRO de 2 dígitos)
PROV_NOMBRES: Dict[str, str] = {
    "01": "Araba/Álava",
    "02": "Albacete",
    "03": "Alicante/Alacant",
    "04": "Almería",
    "05": "Ávila",
    "06": "Badajoz",
    "07": "Balears, Illes",
    "08": "Barcelona",
    "09": "Burgos",
    "10": "Cáceres",
    "11": "Cádiz",
    "12": "Castellón/Castelló",
    "13": "Ciudad Real",
    "14": "Córdoba",
    "15": "Coruña, A",
    "16": "Cuenca",
    "17": "Girona",
    "18": "Granada",
    "19": "Guadalajara",
    "20": "Gipuzkoa",
    "21": "Huelva",
    "22": "Huesca",
    "23": "Jaén",
    "24": "León",
    "25": "Lleida",
    "26": "Rioja, La",
    "27": "Lugo",
    "28": "Madrid",
    "29": "Málaga",
    "30": "Murcia",
    "31": "Navarra",
    "32": "Ourense",
    "33": "Asturias",
    "34": "Palencia",
    "35": "Palmas, Las",
    "36": "Pontevedra",
    "37": "Salamanca",
    "38": "Santa Cruz de Tenerife",
    "39": "Cantabria",
    "40": "Segovia",
    "41": "Sevilla",
    "42": "Soria",
    "43": "Tarragona",
    "44": "Teruel",
    "45": "Toledo",
    "46": "Valencia/València",
    "47": "Valladolid",
    "48": "Bizkaia",
    "49": "Zamora",
    "50": "Zaragoza",
    "51": "Ceuta",
    "52": "Melilla",
}


def _pad(value: Any, width: int) -> Optional[str]:
    """Normaliza un código a string de ancho fijo con ceros a la izquierda.
    Tolera int/float (lo que devuelve openpyxl) y strings con espacios."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    if s.endswith(".0"):  # float de openpyxl ('1.0')
        s = s[:-2]
    return s.zfill(width)


def geo_ine_jerarquia(payload: Any, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aplana la relación de municipios del INE en la jerarquía territorial completa."""
    f_codauto = params.get("codauto_field", "CODAUTO")
    f_cpro = params.get("cpro_field", "CPRO")
    f_cmun = params.get("cmun_field", "CMUN")
    f_nombre = params.get("nombre_field", "NOMBRE")
    pais_codigo = params.get("pais_codigo", "ES")
    pais_nombre = params.get("pais_nombre", "España")
    sep = params.get("path_separator", " > ")

    rows = payload if isinstance(payload, list) else _records(payload, params.get("content_field"))

    out: List[Dict[str, Any]] = []

    # Raíz: País. `codigo` es la CLAVE ÚNICA de enlace (los códigos INE de CCAA y
    # provincia son ambos de 2 dígitos y colisionan: CCAA 01=Andalucía vs provincia
    # 01=Álava), por eso se prefija por tipo (ES / CA## / PR## / MU#####).
    # `codigo_ine` conserva el código natural del INE para mostrar/almacenar.
    out.append({
        "codigo": pais_codigo, "codigo_ine": pais_codigo, "nombre": pais_nombre, "tipo": "pais",
        "nivel": 0, "padre_id": None, "padre_descripcion": None, "ruta": pais_nombre,
    })

    ccaa_vistas: Dict[str, str] = {}   # codauto -> nombre
    prov_vistas: Dict[str, str] = {}   # cpro -> nombre (emitida)
    prov_de_ccaa: Dict[str, str] = {}  # cpro -> codauto

    municipios: List[Dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        ca = _pad(row.get(f_codauto), 2)
        cp = _pad(row.get(f_cpro), 2)
        cm = _pad(row.get(f_cmun), 3)
        nombre_mun = (str(row.get(f_nombre)).strip() if row.get(f_nombre) is not None else "")
        if not ca or not cp or not cm or not nombre_mun:
            continue

        if ca not in ccaa_vistas:
            ccaa_vistas[ca] = CCAA_NOMBRES.get(ca, ca)
        prov_de_ccaa.setdefault(cp, ca)

        municipios.append({"ca": ca, "cp": cp, "codigo": cp + cm, "nombre": nombre_mun})

    # Comunidades Autónomas
    for ca in sorted(ccaa_vistas):
        nombre_ca = ccaa_vistas[ca]
        out.append({
            "codigo": "CA" + ca, "codigo_ine": ca, "nombre": nombre_ca, "tipo": "comunidad",
            "nivel": 1, "padre_id": pais_codigo, "padre_descripcion": pais_nombre,
            "ruta": sep.join([pais_nombre, nombre_ca]),
        })

    # Provincias
    for cp in sorted(prov_de_ccaa):
        ca = prov_de_ccaa[cp]
        nombre_ca = ccaa_vistas.get(ca, ca)
        nombre_prov = PROV_NOMBRES.get(cp, cp)
        prov_vistas[cp] = nombre_prov
        out.append({
            "codigo": "PR" + cp, "codigo_ine": cp, "nombre": nombre_prov, "tipo": "provincia",
            "nivel": 2, "padre_id": "CA" + ca, "padre_descripcion": nombre_ca,
            "ruta": sep.join([pais_nombre, nombre_ca, nombre_prov]),
        })

    # Municipios
    for m in municipios:
        nombre_ca = ccaa_vistas.get(m["ca"], m["ca"])
        nombre_prov = prov_vistas.get(m["cp"], m["cp"])
        out.append({
            "codigo": "MU" + m["codigo"], "codigo_ine": m["codigo"], "nombre": m["nombre"],
            "tipo": "municipio", "nivel": 3, "padre_id": "PR" + m["cp"],
            "padre_descripcion": nombre_prov,
            "ruta": sep.join([pais_nombre, nombre_ca, nombre_prov, m["nombre"]]),
        })

    return out


# Import diferido para evitar ciclo con extraction (que registra esta función).
def _records(payload, content_field):
    from app.fetchers.extraction import _records as _r
    return _r(payload, content_field)
