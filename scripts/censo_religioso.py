"""Censo de entidades religiosas — pipeline de CURACIÓN offline.

Coherente con la arquitectura ODM (decisión 2026-06-06): los joins NO viven en
la plataforma. ODM publica las piezas (RER, BDNS, Fundaciones, Contrataciones,
inmatriculaciones como dato de referencia) y este script las ENSAMBLA fuera del
runtime, produciendo el censo y marcando lo ambiguo para revisión.

Algoritmo establecido (dos anclas + léxico, sin IA en la vía determinista):

  1. ANCLA NIF (determinista, señal fuerte):
       - letra R  → entidad religiosa inscrita (RER): naturaleza CONFIRMADA.
       - letra G  → asociación/fundación; religiosa solo si lo respalda léxico,
                    confesión RER o pertenencia a federación.
     El RER público NO publica NIF; el NIF se ANCLA cruzando la denominación
     normalizada del RER con BDNS/Fundaciones (que sí traen NIF+denominación).

  2. PERTENENCIA AL RER (determinista, definitiva): estar en el RER es, por
     definición, ser entidad religiosa. El scoring sirve sobre todo para
     beneficiarios que aparecen en BDNS/contratos y NO están en el RER.

  3. SCORING LÉXICO (determinista, transparente y auditable): puntúa la
     denominación con un léxico ponderado (confesional multirreligioso) +
     señales de confesión/sección/federación del RER.

  4. CRUCES de salida: los NIF resueltos se cruzan con inmatriculaciones
     (propiedades) y contratos para enriquecer cada ficha del censo.

Vía ASISTIDA (--asistido): los casos AMBIGUOS (misma denominación → varios NIF,
o naturaleza dudosa por debajo de umbral) se elevan a la API de Claude, que
adjudica con salida JSON estricta. Nunca decide sola sobre lo que el
determinista ya resolvió: solo desempata lo que el determinista marca a revisar.

Uso:
  python scripts/censo_religioso.py \
      --rer rer.jsonl --bdns bdns.jsonl [--fundaciones fund.jsonl] \
      [--inmatriculaciones inmo.jsonl] [--contratos contratos.jsonl] \
      [--asistido] [--modelo claude-opus-4-8] --out censo_out/

Entradas JSONL (un objeto por línea). Campos esperados (tolerante a ausencias):
  RER:           nombre, confesion, seccion, tipo_entidad, federaciones,
                 comunidad_autonoma, numero_inscripcion
  BDNS:          beneficiario|denominacion|razon_social, nif|cif|id_beneficiario
  Fundaciones:   nombre|denominacion, nif|cif
  inmatricul.:   titular|denominacion|nombre, (opc. nif), municipio, tipo_bien
  contratos:     adjudicatario|denominacion, nif|cif, objeto, importe

Salidas en --out:
  censo.jsonl       — entidades con nif, naturaleza, score, evidencia, cruces.
  ambiguos.jsonl    — a revisar (denominación con varios NIF, o score en franja).
  sin_ancla.jsonl   — RER sin NIF localizable (quedan en censo como CONFIRMADA
                       por pertenencia, pero sin NIF para cruzar propiedades).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Reutiliza el normalizador del motor de cruce genérico.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from cruce_curacion import _norm_key as _norm  # type: ignore
except Exception:  # pragma: no cover - fallback autocontenido
    def _norm(v: Any) -> Any:
        if not isinstance(v, str):
            return v
        s = unicodedata.normalize("NFKD", v)
        s = "".join(c for c in s if not unicodedata.combining(c))
        return " ".join(s.upper().split())


# --------------------------------------------------------------------------- #
# Léxico de naturaleza religiosa (confesional multirreligioso). Ponderado.
# Términos "fuertes" identifican por sí solos; "modificadores" suman con apoyo.
# --------------------------------------------------------------------------- #
LEXICO_FUERTE = {
    # ALCANCE: SOLO CONFESIÓN CATÓLICA.
    # — Organismos católicos (corpus RER + webs diocesanas + CEE) —
    "parroquia": 5, "diocesis": 5, "archidiocesis": 5, "arquidiocesis": 5,
    "obispado": 5, "arzobispado": 5, "cabildo catedral": 5,
    "curia diocesana": 5, "vicaria": 4, "arciprestazgo": 5, "arcipreste": 4,
    "delegacion diocesana": 5, "secretariado diocesano": 5, "seminario": 4,
    "cofradia": 4, "hermandad": 4, "archicofradia": 5, "sacramental": 3,
    "congregacion": 4, "orden religiosa": 5, "monasterio": 5, "convento": 5,
    "abadia": 5,
    "caritas": 5, "manos unidas": 5, "fundacion diocesana": 5,
    "instituto secular": 4, "instituto de vida consagrada": 5, "entidad canonica": 5,
    "pia union": 4, "casa colegio": 4, "casa sacerdotal": 5,
    "pontificia": 4, "pontificio": 4, "apostolado": 4, "obra pia": 4,
    "capellania": 4, "priorato": 4, "abadesa": 4, "noviciado": 4, "santutegia": 4,
    "cartuja": 5, "san juan de dios": 5, "hospitalarias": 4, "martir": 3,
    # — Órdenes / congregaciones (m. y f.) —
    "carmelitas": 4, "franciscanos": 4, "franciscanas": 4, "dominicos": 4,
    "dominicas": 4, "jesuitas": 4, "salesianos": 4, "salesianas": 4,
    "capuchinos": 4, "claretianos": 4, "escolapios": 4, "redentoristas": 4,
    "agustinos": 4, "agustinas": 4, "mercedarias": 4, "adoratrices": 4,
    "clarisas": 4, "concepcionistas": 4, "benedictinas": 4, "benedictinos": 4,
    "trinitarias": 4, "oblatas": 4, "hijas de la caridad": 5, "siervas de": 4,
    "hermanitas de": 4, "esclavas de": 4, "religiosas de": 4, "religiosos de": 4,
    "misioneros": 4, "misioneras": 4, "hermanas de la caridad": 5,
    "sacerdotal": 4, "sacerdotes": 3, "beato": 3, "beata": 3,
}
# Adjetivos confesionales: SÍ son señal por sí solos (cuentan siempre).
# catolica/diocesana/parroquial a 3 → alcanzan "probable" sin otra señal.
LEXICO_MODIF_ALWAYS = {
    "catolica": 3, "catolico": 3, "diocesano": 3, "diocesana": 3, "parroquial": 3,
    "eclesial": 2, "eclesiastica": 2, "canonica": 2, "apostolica": 2,
    "religiosa": 2, "religioso": 2,
    "evangelizacion": 2, "catequesis": 2, "pastoral": 1,
}
# Hagiónimos y genéricos: en España casi todo callejero/patrón lleva un santo.
# Solo cuentan si hay un término ESTRUCTURAL (FUERTE) o confesional presente.
LEXICO_MODIF_GATED = {
    "sagrada familia": 2, "del santisimo": 2, "nuestra senora": 2, "capilla": 2,
    "sagrada": 1, "sagrado": 1, "virgen": 1, "santisima": 1, "santisimo": 1,
    "san ": 1, "santa ": 1, "santo ": 1, "del carmen": 1, "del rosario": 1,
    "liturgia": 1, "oracion": 1, "colegio": 1, "casa": 1, "fundacion": 1,
    "mision": 1, "iglesia": 1, "fraternidad": 1,
    # advocaciones (= nombre de patrón) y edificios de culto: solo con estructural
    "sagrado corazon": 2, "corazon de jesus": 2, "inmaculada": 2, "purisima": 2,
    "cristo rey": 2, "divina pastora": 2, "verbo divino": 2, "espiritu santo": 2,
    "jesus maria": 2, "jesus y maria": 2, "jesus-maria": 2, "santisimo sacramento": 2,
    "santisima trinidad": 2, "amor de dios": 2, "casa de dios": 2,
    "ermita": 2, "santuario": 2, "basilica": 2, "oratorio": 2, "catedral": 2, "colegiata": 2,
}
# Entidades SECULARES que toman prestadas palabras de sonido religioso (NO católicas).
LEXICO_NEGATIVO = {
    "cofradia de pescadores": 8, "cofradia de mareantes": 8, "posito de pescadores": 8,
    "posito": 5, "cofradia gastronomica": 8, "cofradia enologica": 8,
    "cofradia del vino": 8, "cofradia vinica": 8, "cofradia del cava": 8,
    "hermandad de labradores": 8, "hermandad de donantes": 8,
    "hermandad de jubilados": 8, "hermandad de pensionistas": 8,
    "hermandad de excombatientes": 8, "hermandad sindical": 8,
    "hermandad de veteranos": 8, "hermandad de empleados": 8,
    # Cofradías de pescadores (gremio pesquero) — también sin "de" y con patrón mariano
    "cofradia pescadores": 8, "cofradias pescadores": 8, "cofradia de pescadores": 8,
    "cofradias de pescadores": 8, "moros y cristianos": 8, "hermandad gallega": 8, "gastronom": 8, "cofradias pescadore": 8,
    "federacion de cofradias": 8, "posito": 5,
    # Comisiones/sociedades de fiestas y festejos de pueblo (patrón ≠ entidad católica)
    "comision de fiestas": 8, "comision de festas": 8, "comision de festexos": 8,
    "comision de festejos": 8, "comissio de festes": 8, "sociedad de fiestas": 8,
    "asociacion de fiestas": 8, "asociacion de festas": 8, "asoc de festas": 8,
    "junta de fiestas": 8, "pena": 4,
    # Asociaciones de vecinos / tercera edad
    "asociacion de vecinos": 8, "asociacion de veciños": 8, "asoc de vecinos": 8,
    "asoc de veciños": 8, "asociacion de veciñas": 8, "tercera edad": 8,
}

UMBRAL_CONFIRMA = 5    # score determinista → naturaleza "religiosa" confirmada
UMBRAL_PROBABLE = 3    # entre probable y confirma: "probable"
# por debajo de PROBABLE y sin ancla R / RER → "descartada" (salvo asistido)


def _texto(reg: Dict, *claves: str) -> str:
    for k in claves:
        v = reg.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _nif(reg: Dict) -> str:
    raw = _texto(reg, "nif", "cif", "id_beneficiario", "nif_beneficiario", "documento")
    return re.sub(r"[^0-9A-Za-z]", "", raw).upper()


def letra_nif(nif: str) -> str:
    return nif[0] if nif and nif[0].isalpha() else ""


def puntua_lexico(nombre: str) -> Tuple[int, List[str]]:
    """Score determinista de la denominación. Devuelve (score, evidencia).

    Gating: los hagiónimos (san/santa/virgen…) y genéricos (colegio/casa/
    fundación) solo puntúan si hay un término ESTRUCTURAL fuerte o un adjetivo
    confesional presente. Un santo suelto no es señal religiosa (medio callejero
    español es hagiotopónimo).
    """
    n = " " + _norm(nombre).lower() + " "
    score, evid = 0, []
    fuerte = False
    for term, w in LEXICO_FUERTE.items():
        if term in n:
            score += w
            evid.append(f"+{w} «{term}»")
            fuerte = True
    confesional = False
    for term, w in LEXICO_MODIF_ALWAYS.items():
        if term in n:
            score += w
            evid.append(f"+{w} conf «{term.strip()}»")
            confesional = True
    if fuerte or confesional:
        for term, w in LEXICO_MODIF_GATED.items():
            if term in n:
                score += w
                evid.append(f"+{w} mod «{term.strip()}»")
    for term, w in LEXICO_NEGATIVO.items():
        if term in n:
            score -= w
            evid.append(f"-{w} secular «{term}»")
    return score, evid


# Marcadores de confesiones NO católicas. El censo es católico-only, y la letra R
# del NIF marca "entidad religiosa" de CUALQUIER confesión: hay que excluir el resto
# incluso cuando vienen con NIF-R o inscritas en el RER. Stems elegidos sin colisión
# con términos católicos (p.ej. "evangelic" no casa con "evangelizacion"/"evangelista",
# y NO se incluye "bautista" por San Juan Bautista).
LEXICO_NO_CATOLICO = (
    "evangelic", "evangelista de", "protestant", "pentecostal", "adventist",
    "asamblea de dios", "asambleas de dios", "filadelfia", "iglesia de filadelfia",
    "islamic", "musulman", "mezquita", "morabito", "comunidad islam",
    "budist", "hindu", "krishna", "soka gakkai",
    "judia", "judio", "israelita", "hebrea", "sinagoga", "sefardi", "comunidad judia",
    "ortodox", "testigos de jehova", "testigos cristianos de jehova",
    "mormon", "santos de los ultimos dias", "jesucristo de los santos",
    "cienciolog", "bahai", "fe bahai", "sij", "gurdwara", "iglesia de la unificacion",
)


def naturaleza(*, nombre: str, nif: str, en_rer: bool,
               confesion: str = "", federaciones: Any = None) -> Dict[str, Any]:
    """Clasificación determinista de la naturaleza religiosa de una entidad."""
    letra = letra_nif(nif)
    lex, evid = puntua_lexico(nombre)
    score = lex
    # Exclusión de confesiones no católicas (prevalece sobre RER y NIF-R).
    _n = " " + _norm(nombre).lower() + " "
    for marca in LEXICO_NO_CATOLICO:
        if marca in _n:
            return {"naturaleza": "descartada", "via": "no_catolica",
                    "score": score, "evidencia": [f"no católica «{marca.strip()}»"] + evid}
    # NIF-P = corporación local (ayuntamientos, parroquias rurales/concejos civiles
    # de Asturias-Galicia, juntas vecinales). Nunca es entidad eclesial católica.
    if letra == "P":
        return {"naturaleza": "descartada", "via": "ente_local",
                "score": score, "evidencia": ["NIF-P: corporación local civil"] + evid}
    # Solo R/G/V/Q son formas jurídicas posibles de entidad eclesial católica.
    # A/B/C/D/E/F/H/J = sociedades/comunidades mercantiles o de propietarios;
    # I/N = extranjeras (fuera de censo español); DNI personal = persona física.
    if letra and letra not in ("R", "G", "V", "Q"):
        return {"naturaleza": "descartada", "via": "forma_no_eclesial",
                "score": score, "evidencia": [f"NIF-{letra}: forma jurídica no eclesial"] + evid}
    if confesion and str(confesion).strip():
        score += 3; evid.append("+3 confesión RER")
    fed = federaciones if isinstance(federaciones, list) else (
        [federaciones] if (federaciones and str(federaciones).strip()) else [])
    if fed:
        score += 2; evid.append("+2 pertenece a federación")

    if en_rer:
        return {"naturaleza": "confirmada", "via": "pertenencia_rer",
                "score": score, "evidencia": ["RER: inscrita"] + evid}
    if letra == "R":
        return {"naturaleza": "confirmada", "via": "nif_r",
                "score": max(score, UMBRAL_CONFIRMA),
                "evidencia": ["NIF-R: entidad religiosa inscrita"] + evid}
    if score >= UMBRAL_CONFIRMA:
        return {"naturaleza": "confirmada", "via": "lexico", "score": score, "evidencia": evid}
    if score >= UMBRAL_PROBABLE:
        return {"naturaleza": "probable", "via": "lexico", "score": score, "evidencia": evid}
    # NIF-G NO es señal por sí sola (cubre todas las asociaciones/fundaciones).
    # Una G con algo de señal léxica pero por debajo de umbral va a REVISAR
    # (humano o vía asistida); sin ninguna señal, se descarta.
    if letra == "G" and score > 0:
        return {"naturaleza": "revisar", "via": "g_senal_debil",
                "score": score, "evidencia": ["NIF-G"] + evid}
    return {"naturaleza": "descartada", "via": "bajo_umbral", "score": score, "evidencia": evid}


# --------------------------------------------------------------------------- #
# Índice NIF por denominación (desde BDNS + Fundaciones). Marca ambigüedades.
# --------------------------------------------------------------------------- #
def construir_indice_nif(*fuentes: Tuple[List[Dict], Tuple[str, ...]]
                         ) -> Tuple[Dict[str, Dict], set]:
    """fuentes: lista de (registros, claves_de_denominacion). Devuelve
    (indice denom_norm → {nif, nombre, fuente}, conjunto de denoms ambiguas)."""
    indice: Dict[str, Dict] = {}
    nifs_por_denom: Dict[str, set] = {}
    for registros, claves in fuentes:
        for r in registros:
            nombre = _texto(r, *claves)
            nif = _nif(r)
            if not nombre or not nif:
                continue
            k = _norm(nombre)
            nifs_por_denom.setdefault(k, set()).add(nif)
            indice[k] = {"nif": nif, "nombre": nombre, "fuente": r.get("_fuente", "")}
    ambiguas = {k for k, s in nifs_por_denom.items() if len(s) > 1}
    return indice, ambiguas


def cargar(path: Optional[str]) -> List[Dict]:
    if not path:
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def indexar_por_nif(registros: List[Dict]) -> Dict[str, List[Dict]]:
    idx: Dict[str, List[Dict]] = {}
    for r in registros:
        nif = _nif(r)
        if nif:
            idx.setdefault(nif, []).append(r)
    return idx


# --------------------------------------------------------------------------- #
# Vía asistida por la API de Claude (solo para ambiguos).
# --------------------------------------------------------------------------- #
def adjudicar_con_claude(ambiguos: List[Dict], modelo: str) -> List[Dict]:
    """Eleva los ambiguos a la API de Claude para adjudicar naturaleza/identidad.
    Salida JSON estricta. Requiere ANTHROPIC_API_KEY en el entorno."""
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("[asistido] falta ANTHROPIC_API_KEY; se omite la adjudicación", file=sys.stderr)
        return ambiguos
    resueltos: List[Dict] = []
    LOTE = 25
    for i in range(0, len(ambiguos), LOTE):
        lote = ambiguos[i:i + LOTE]
        items = [{"id": j, "denominacion": a.get("nombre", ""),
                  "nif_letra": letra_nif(a.get("nif", "")),
                  "confesion": a.get("confesion", ""),
                  "motivo_ambiguo": a.get("_motivo", "")}
                 for j, a in enumerate(lote)]
        prompt = (
            "Eres un curador de datos del registro público español. Para cada "
            "entidad decide si es una ENTIDAD RELIGIOSA (iglesia, parroquia, "
            "diócesis, cofradía, comunidad islámica/judía/evangélica, fundación "
            "confesional, etc.). Responde SOLO con un array JSON, sin texto ni "
            "markdown, un objeto por entrada con: id (int), naturaleza "
            "('confirmada'|'probable'|'descartada'), confianza (0-1), motivo "
            "(breve). Datos:\n" + json.dumps(items, ensure_ascii=False))
        body = json.dumps({"model": modelo, "max_tokens": 2000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body, method="POST",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=120))
            txt = "".join(b.get("text", "") for b in data.get("content", [])
                          if b.get("type") == "text").strip()
            txt = re.sub(r"^```(?:json)?|```$", "", txt).strip()
            veredictos = {v["id"]: v for v in json.loads(txt)}
        except Exception as e:  # pragma: no cover - red/parse
            print(f"[asistido] lote {i//LOTE} falló: {e}", file=sys.stderr)
            veredictos = {}
        for j, a in enumerate(lote):
            v = veredictos.get(j)
            out = dict(a)
            if v:
                out["naturaleza"] = v.get("naturaleza", a.get("naturaleza"))
                out["via"] = "asistida_claude"
                out["confianza_ia"] = v.get("confianza")
                out["motivo_ia"] = v.get("motivo")
            resueltos.append(out)
    return resueltos


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Construye el censo de entidades religiosas")
    ap.add_argument("--rer", help="JSONL del RER (entidades inscritas)")
    ap.add_argument("--bdns", help="JSONL de BDNS concesiones (beneficiario+NIF)")
    ap.add_argument("--fundaciones", help="JSONL del registro de fundaciones")
    ap.add_argument("--inmatriculaciones", help="JSONL de inmatriculaciones (propiedades)")
    ap.add_argument("--contratos", help="JSONL de contratos públicos")
    ap.add_argument("--asistido", action="store_true",
                    help="adjudica los ambiguos con la API de Claude")
    ap.add_argument("--modelo", default="claude-opus-4-8")
    ap.add_argument("--out", default="censo_out")
    a = ap.parse_args()

    rer = cargar(a.rer)
    bdns = cargar(a.bdns)
    fundaciones = cargar(a.fundaciones)
    inmo = cargar(a.inmatriculaciones)
    contratos = cargar(a.contratos)

    # 1) Índice NIF por denominación (BDNS + Fundaciones) con ambigüedades.
    indice_nif, denoms_ambiguas = construir_indice_nif(
        (bdns, ("beneficiario", "denominacion", "razon_social")),
        (fundaciones, ("nombre", "denominacion")),
    )

    # 2) Censo base: RER (anclando NIF) + beneficiarios BDNS/Fundaciones no-RER.
    censo: List[Dict] = []
    ambiguos: List[Dict] = []
    sin_ancla: List[Dict] = []
    vistos_nif: set = set()
    denoms_rer: set = set()

    for r in rer:
        nombre = _texto(r, "nombre", "denominacion")
        k = _norm(nombre)
        denoms_rer.add(k)
        ancla = indice_nif.get(k)
        nif = ancla["nif"] if ancla else ""
        nat = naturaleza(nombre=nombre, nif=nif, en_rer=True,
                         confesion=r.get("confesion", ""),
                         federaciones=r.get("federaciones"))
        ficha = {
            "nombre": nombre, "nif": nif,
            "confesion": r.get("confesion", ""), "seccion": r.get("seccion", ""),
            "tipo_entidad": r.get("tipo_entidad", ""),
            "comunidad_autonoma": r.get("comunidad_autonoma", ""),
            "numero_inscripcion": r.get("numero_inscripcion", ""),
            "federaciones": r.get("federaciones", []),
            "fuente_censo": "RER", **nat,
        }
        if nif and k in denoms_ambiguas:
            ficha["_motivo"] = "denominación con varios NIF en BDNS/Fundaciones"
            ambiguos.append(ficha)
        elif not nif:
            sin_ancla.append(ficha)        # religiosa confirmada pero sin NIF
            censo.append(ficha)
        else:
            vistos_nif.add(nif)
            censo.append(ficha)

    # Beneficiarios de BDNS/Fundaciones NO presentes en el RER: ¿religiosos?
    for registros, claves, fuente in (
            (bdns, ("beneficiario", "denominacion", "razon_social"), "BDNS"),
            (fundaciones, ("nombre", "denominacion"), "Fundaciones")):
        for reg in registros:
            nombre = _texto(reg, *claves)
            nif = _nif(reg)
            k = _norm(nombre)
            if not nombre or k in denoms_rer or nif in vistos_nif:
                continue
            nat = naturaleza(nombre=nombre, nif=nif, en_rer=False)
            if nat["naturaleza"] == "descartada":
                continue
            vistos_nif.add(nif)
            ficha = {"nombre": nombre, "nif": nif, "confesion": "",
                     "fuente_censo": fuente, **nat}
            if nat["naturaleza"] == "revisar":
                ficha["_motivo"] = "NIF-G con señal léxica débil"
                ambiguos.append(ficha)
            else:
                censo.append(ficha)

    # 3) Cruces de salida: propiedades (inmatriculaciones) y contratos por NIF.
    inmo_por_nif = indexar_por_nif(inmo)
    contr_por_nif = indexar_por_nif(contratos)
    # inmatriculaciones a menudo sin NIF → cruce por denominación como respaldo
    inmo_por_denom: Dict[str, List[Dict]] = {}
    for x in inmo:
        kk = _norm(_texto(x, "titular", "denominacion", "nombre"))
        if kk:
            inmo_por_denom.setdefault(kk, []).append(x)
    for ficha in censo:
        nif, k = ficha.get("nif", ""), _norm(ficha["nombre"])
        props = (inmo_por_nif.get(nif, []) if nif else []) or inmo_por_denom.get(k, [])
        contrs = contr_por_nif.get(nif, []) if nif else []
        ficha["n_propiedades"] = len(props)
        ficha["n_contratos"] = len(contrs)
        ficha["importe_contratos"] = round(sum(
            float(str(c.get("importe", 0)).replace(",", ".") or 0)
            for c in contrs if str(c.get("importe", "")).replace(",", ".")
            .replace(".", "").isdigit()), 2)

    # 4) Vía asistida sobre los ambiguos.
    if a.asistido and ambiguos:
        ambiguos = adjudicar_con_claude(ambiguos, a.modelo)
        for f in ambiguos:
            if f.get("naturaleza") in ("confirmada", "probable"):
                censo.append(f)

    # 5) Volcado.
    os.makedirs(a.out, exist_ok=True)
    def volcar(nombre, filas):
        with open(os.path.join(a.out, nombre), "w", encoding="utf-8") as fh:
            for f in filas:
                fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    volcar("censo.jsonl", censo)
    volcar("ambiguos.jsonl", ambiguos)
    volcar("sin_ancla.jsonl", sin_ancla)

    conf = sum(1 for f in censo if f["naturaleza"] == "confirmada")
    prob = sum(1 for f in censo if f["naturaleza"] == "probable")
    print(f"[censo_religioso] {len(censo)} entidades "
          f"({conf} confirmadas, {prob} probables), "
          f"{len(ambiguos)} ambiguas{' (adjudicadas por IA)' if a.asistido else ' (a revisar)'}, "
          f"{len(sin_ancla)} sin NIF → {a.out}/")


if __name__ == "__main__":
    main()
