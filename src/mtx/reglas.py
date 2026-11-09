"""Reglas de extracción: FECHA, MONTO, cantidades auxiliares, gazetteers ORG/LOC y marca (PRD §6.7).

Trabaja siempre sobre el `texto` canónico del pasaje (mayúsculas y acentos intactos), nunca sobre
los tokens de IR. Los offsets son índices de carácter Python, `inicio` inclusivo y `fin`
exclusivo, y en todo resultado `texto[inicio:fin] == entidad.texto`.

Decisiones de este módulo (ver `docs/decisiones.md`):
- MONTO es dinero (D11); porcentajes y cantidades salen por `extraer_auxiliares`, nunca como `Entidad`.
- Ante solape entre fuentes gana el span más largo; en empate, `regex_fecha > regex_monto >
  gazetteer_loc > gazetteer_org > marca` (§6.7.8).
- Fechas con año de dos dígitos: 18 a 30 se expanden a 20yy; el resto queda ambiguo (`fecha_iso`
  vacía). `dd/mm/aa` se lee día primero, como se escribe en México.
"""
from __future__ import annotations

import calendar
import csv
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import config, preproceso

TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
JERARQUIA = {"regex_fecha": 0, "regex_monto": 1, "gazetteer_loc": 2, "gazetteer_org": 3, "marca": 4}
GAZETTEER_EXTENDIDO = config.DIR_CONFIG / "gazetteer_extendido.csv"
GAZETTEER_LOC = config.DIR_CONFIG / "gazetteer_loc.csv"


@dataclass
class Entidad:
    tipo: str          # PER | ORG | LOC | FECHA | MONTO
    texto: str
    inicio: int
    fin: int
    metodo: str = "regla"
    fuente: str = ""   # regex_fecha | regex_monto | gazetteer_org | gazetteer_loc | marca
    en_marca: bool = False


# --------------------------------------------------------------------------- FECHA

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
          "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
          "diciembre": 12}
_MES = "|".join(_MESES)
_DIA = r"(?:primero|\d{1,2})"
_ANIO = r"(?:19|20)\d{2}"
_MOD = r"(?:pr[óo]xim[oa]|pasad[oa]|est[ea])"
_NORMALIZA_MOD = {"próximo": "proximo", "proximo": "proximo", "próxima": "proximo",
                  "proxima": "proximo", "pasado": "pasado", "pasada": "pasado", "este": "este",
                  "esta": "este"}

_P_INTERVALO = (rf"(?P<d1>{_DIA})\s+al\s+(?P<d2>{_DIA})\s+de\s+(?P<mes>{_MES})"
                rf"(?:\s+(?:de|del)\s+(?P<anio>{_ANIO}))?")
_P_ABSOLUTA = (rf"(?:(?P<mod>{_MOD})\s+)?(?P<dia>{_DIA})\s+de\s+(?P<mes>{_MES})"
               rf"(?:\s+(?:de|del)\s+(?P<anio>{_ANIO}))?")
_P_MES_ANIO = rf"(?P<mes>{_MES})\s+(?:de|del)\s+(?P<anio>{_ANIO})"
_P_NUMERICA = r"(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4}|\d{2})"
_P_ANIO = rf"(?P<anio>{_ANIO})"

_F = re.IGNORECASE
RE_FECHA_BUSQUEDA = [
    ("intervalo", re.compile(rf"(?<![\w/])del\s+{_P_INTERVALO}(?!\w)", _F), "d1"),
    ("absoluta", re.compile(rf"(?<![\w/]){_P_ABSOLUTA}(?!\w)", _F), None),
    ("mes_anio", re.compile(rf"(?<![\w/]){_P_MES_ANIO}(?!\w)", _F), None),
    ("numerica", re.compile(rf"(?<![\w/.,]){_P_NUMERICA}(?![\w/])", _F), None),
    ("anio_contexto", re.compile(
        rf"(?<!\w)(?:en|desde|hasta|durante|el\s+año|del\s+año|para)\s+{_P_ANIO}(?!\w)"
        rf"(?!\s+(?:pesos|dólares|dolares|millones|mil(?!\w)|personas|habitantes|casos|kilómetros"
        rf"|metros|litros))", _F), "anio"),
]
_RE_ANALISIS = [
    ("intervalo", re.compile(_P_INTERVALO, _F)), ("absoluta", re.compile(_P_ABSOLUTA, _F)),
    ("mes_anio", re.compile(_P_MES_ANIO, _F)), ("numerica", re.compile(_P_NUMERICA, _F)),
    ("anio", re.compile(_P_ANIO, _F)),
]


def _dia(valor: str) -> int:
    return 1 if valor.lower() == "primero" else int(valor)


def _anio_dos_digitos(a: str) -> int | None:
    """Regla de siglo documentada: 18 a 30 → 2018 a 2030; el resto es ambiguo (None)."""
    n = int(a)
    return 2000 + n if 18 <= n <= 30 else None


def _dia_valido(dia: int, mes: int, anio: int | None) -> bool:
    if not 1 <= mes <= 12 or dia < 1:
        return False
    tope = calendar.monthrange(anio, mes)[1] if anio else (29 if mes == 2 else
                                                         calendar.monthrange(2001, mes)[1])
    return dia <= tope


def analizar_fecha(texto: str) -> dict:
    """Valores normalizados de una FECHA ya detectada: `fecha_iso`, `precision`, `estado`, ...

    `estado` ∈ ok | invalida | parcial (sin año) | anio_ambiguo. Un `31 de febrero` se detecta por la
    regex pero aquí queda `invalida` con `fecha_iso` vacía. No resuelve fechas relativas.
    """
    vacio = {"fecha_iso": "", "precision": "", "estado": "no_reconocida", "modificador": "",
             "fecha_inicio": "", "fecha_fin": ""}
    for nombre, patron in _RE_ANALISIS:
        m = patron.fullmatch(texto)
        if not m:
            continue
        out = dict(vacio)
        g = m.groupdict()
        mod = _NORMALIZA_MOD.get((g.get("mod") or "").lower(), "")
        out["modificador"] = mod
        if nombre == "anio":
            return {**out, "fecha_iso": g["anio"], "precision": "anio", "estado": "ok"}
        if nombre == "mes_anio":
            return {**out, "fecha_iso": f"{g['anio']}-{_MESES[g['mes'].lower()]:02d}",
                    "precision": "mes", "estado": "ok"}
        if nombre == "numerica":
            d, mes = int(g["d"]), int(g["m"])
            anio = int(g["a"]) if len(g["a"]) == 4 else _anio_dos_digitos(g["a"])
            out["precision"] = "dia"
            if anio is None:
                return {**out, "estado": "anio_ambiguo"}
            if not _dia_valido(d, mes, anio):
                return {**out, "estado": "invalida"}
            return {**out, "fecha_iso": f"{anio}-{mes:02d}-{d:02d}", "estado": "ok"}
        mes = _MESES[g["mes"].lower()]
        anio = int(g["anio"]) if g.get("anio") else None
        if nombre == "intervalo":
            d1, d2 = _dia(g["d1"]), _dia(g["d2"])
            out["precision"] = "intervalo"
            if not (_dia_valido(d1, mes, anio) and _dia_valido(d2, mes, anio) and d1 <= d2):
                return {**out, "estado": "invalida"}
            if anio is None:
                return {**out, "estado": "parcial"}
            return {**out, "fecha_inicio": f"{anio}-{mes:02d}-{d1:02d}",
                    "fecha_fin": f"{anio}-{mes:02d}-{d2:02d}", "estado": "ok"}
        d = _dia(g["dia"])
        out["precision"] = "dia"
        if not _dia_valido(d, mes, anio):
            return {**out, "estado": "invalida"}
        if anio is None:
            return {**out, "estado": "parcial"}
        return {**out, "fecha_iso": f"{anio}-{mes:02d}-{d:02d}", "estado": "ok"}
    return vacio


def _fechas(texto: str) -> list[Entidad]:
    candidatas = []
    for _, patron, grupo in RE_FECHA_BUSQUEDA:
        for m in patron.finditer(texto):
            inicio = m.start(grupo) if grupo else m.start()
            candidatas.append((inicio, m.end()))
    candidatas.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
    elegidas: list[tuple[int, int]] = []
    for ini, fin in candidatas:
        if all(fin <= a or ini >= b for a, b in elegidas):
            elegidas.append((ini, fin))
    return [Entidad("FECHA", texto[a:b], a, b, fuente="regex_fecha") for a, b in sorted(elegidas)]


# --------------------------------------------------------------------------- MONTO y auxiliares

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
PALABRA_NUM = r"un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|cien"
CIFRA = (rf"(?:(?:{NUM}|{PALABRA_NUM})(?:\s+mil(?!\w)(?:\s+(?:{NUM}))?)?"
         rf"|mil(?!\w)(?:\s+(?:{NUM}))?)")
ESCALA = r"(?:\s+(?:millones|millón|billones|billón))?"
MONEDA = r"\s+(?:de\s+)?(?:pesos|dólares|dolares)"
LIMITE_IZQ = r"(?<![\w$.,])"
RE_MONTO = re.compile(
    rf"{LIMITE_IZQ}(?:\$\s?{CIFRA}{ESCALA}(?:{MONEDA})?|{CIFRA}{ESCALA}{MONEDA})(?!\w)", _F)
RE_PORCENTAJE = re.compile(rf"{LIMITE_IZQ}(?P<num>{NUM})\s*(?:por\s+ciento(?!\w)|%)", _F)
UNIDADES_CANTIDAD = ("dosis", "elementos", "litros", "sucursales", "hectáreas", "hectareas",
                     "beneficiarios", "sembradores", "kilómetros", "kilometros")
RE_CANTIDAD = re.compile(
    rf"{LIMITE_IZQ}(?P<cifra>{CIFRA}{ESCALA})\s+(?:de\s+)?(?P<unidad>{'|'.join(UNIDADES_CANTIDAD)})"
    rf"(?!\w)", _F)

_PALABRAS = {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
             "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "cien": 100}
_RE_ATOMO = re.compile(rf"{NUM}|[a-záéíóúñ]+", _F)


def valor_cifra(expresion: str) -> Decimal:
    """Valor numérico (en unidades) de `2 mil 500 millones`, `mil 200`, `un millón`, `1.5 billones`.

    Escala larga: un billón es 10^12. Ignora `de`, `pesos` y demás palabras.
    """
    total = Decimal(0)
    for atomo in _RE_ATOMO.findall(expresion.lower()):
        if atomo[0].isdigit():
            total += Decimal(atomo.replace(",", ""))
        elif atomo in _PALABRAS:
            total += _PALABRAS[atomo]
        elif atomo == "mil":
            total = (total or Decimal(1)) * 1000
        elif atomo in ("millón", "millones"):
            total = (total or Decimal(1)) * 10**6
        elif atomo in ("billón", "billones"):
            total = (total or Decimal(1)) * 10**12
    return total


def _montos(texto: str) -> list[Entidad]:
    return [Entidad("MONTO", m.group(), m.start(), m.end(), fuente="regex_monto")
            for m in RE_MONTO.finditer(texto)]


def extraer_auxiliares(texto: str) -> list[dict]:
    """Porcentajes y cantidades (D11). No son entidades del examen: nunca van a `entidades.csv`."""
    filas = []
    for m in RE_PORCENTAJE.finditer(texto):
        filas.append({"texto": m.group(), "inicio": m.start(), "fin": m.end(),
                      "tipo_aux": "PORCENTAJE", "valor_num": Decimal(m.group("num")),
                      "unidad": "porcentaje", "estado_normalizacion": "ok",
                      "regla_id": "re_porcentaje"})
    for m in RE_CANTIDAD.finditer(texto):
        filas.append({"texto": m.group(), "inicio": m.start(), "fin": m.end(),
                      "tipo_aux": "CANTIDAD", "valor_num": valor_cifra(m.group("cifra")),
                      "unidad": m.group("unidad").lower(), "estado_normalizacion": "ok",
                      "regla_id": "re_cantidad"})
    return sorted(filas, key=lambda f: f["inicio"])


# --------------------------------------------------------------------------- gazetteer

COMUNES_SENSIBLES = frozenset({"patria", "morena", "salud", "bienestar", "cultura", "economía"})
"""Nombres que también son palabras comunes: se buscan siempre sensibles a mayúsculas (§6.7.7)."""
_IZQ, _DER = r"(?<![\wáéíóúñü])", r"(?![\wáéíóúñü])"


def _sensible(termino: str) -> bool:
    return len(termino) <= 5 or termino.lower() in COMUNES_SENSIBLES


def _compilar(terminos: list[str], sensible: bool) -> re.Pattern | None:
    if not terminos:
        return None
    alternativas = {re.escape(t) for t in terminos}
    if sensible:  # exacto o todo en mayúsculas (marca de interlocutor, PRD §6.7.7)
        alternativas |= {re.escape(t.upper()) for t in terminos}
    ordenadas = sorted(alternativas, key=len, reverse=True)
    return re.compile(_IZQ + "(?:" + "|".join(ordenadas) + ")" + _DER, 0 if sensible else _F)


class Gazetteer:
    """Gazetteers ORG y LOC con motor de coincidencia más larga (PRD §6.7.7)."""

    def __init__(self, terminos_org: list[str], terminos_loc: list[str], estados: list[str]):
        self._terminos = {"ORG": sorted(set(terminos_org)), "LOC": sorted(set(terminos_loc))}
        self.estados = list(estados)
        self._regex = {}
        for tipo, lista in self._terminos.items():
            self._regex[tipo] = (
                _compilar([t for t in lista if _sensible(t)], True),
                _compilar([t for t in lista if not _sensible(t)], False))

    def terminos(self, tipo: str) -> set[str]:
        return set(self._terminos[tipo])

    def coincidencias(self, texto: str, tipo: str) -> list[tuple[int, int]]:
        """Spans sin solape, ganando la coincidencia más larga dentro de este gazetteer."""
        spans = [(m.start(), m.end()) for r in self._regex[tipo] if r for m in r.finditer(texto)]
        spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
        elegidos: list[tuple[int, int]] = []
        for ini, fin in spans:
            if all(fin <= a or ini >= b for a, b in elegidos):
                elegidos.append((ini, fin))
        return sorted(elegidos)


def _partir(celda: str) -> list[str]:
    return [p.strip() for p in (celda or "").split("|") if p.strip()]


@lru_cache(maxsize=4)
def _cargar(ruta_org: str, ruta_loc: str) -> Gazetteer:
    org, loc, estados = [], [], []
    with open(ruta_org, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            nombres = [fila["nombre"], *_partir(fila["variantes"]), *_partir(fila["siglas"])]
            (loc if fila["etiqueta"] == "LOC" else org).extend(n for n in nombres if n)
    with open(ruta_loc, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            loc.extend([fila["nombre"], *_partir(fila["variantes"])])
            if fila["categoria"] == "estado":
                estados.append(fila["nombre"])
    return Gazetteer(org, loc, estados)


def cargar_gazetteer(ruta_org: Path = GAZETTEER_EXTENDIDO, ruta_loc: Path = GAZETTEER_LOC) -> Gazetteer:
    """Lee `config/gazetteer_extendido.csv` (ORG y obras como LOC) y `config/gazetteer_loc.csv`."""
    return _cargar(str(ruta_org), str(ruta_loc))


_RE_DE = re.compile(r"\s+(?:de|del)\s+", _F)


def _gazetteers(texto: str, inicio_cuerpo: int, gaz: Gazetteer) -> list[Entidad]:
    org = gaz.coincidencias(texto, "ORG")
    loc = gaz.coincidencias(texto, "LOC")
    # Una ORG de nombre completo seguida de «de/del <LOC>» es una sola ORG (PRD §3.6):
    # `Secretaría de Salud de Tabasco`, sin LOC interno.
    ampliadas = []
    for ini, fin in org:
        if " " in texto[ini:fin]:
            puente = _RE_DE.match(texto, fin)
            if puente:
                siguiente = next(((a, b) for a, b in loc if a == puente.end()), None)
                if siguiente:
                    fin = siguiente[1]
        ampliadas.append((ini, fin))
    ents = [Entidad("ORG", texto[a:b], a, b, fuente="gazetteer_org", en_marca=a < inicio_cuerpo)
            for a, b in ampliadas]
    ents += [Entidad("LOC", texto[a:b], a, b, fuente="gazetteer_loc", en_marca=a < inicio_cuerpo)
             for a, b in loc]
    return ents


# --------------------------------------------------------------------------- marca de interlocutor

CARGOS = frozenset({
    "PRESIDENTE", "PRESIDENTA", "SECRETARIO", "SECRETARIA", "SUBSECRETARIO", "SUBSECRETARIA",
    "DIRECTOR", "DIRECTORA", "SUBDIRECTOR", "SUBDIRECTORA", "COORDINADOR", "COORDINADORA",
    "TITULAR", "PROCURADOR", "PROCURADORA", "SUBPROCURADOR", "SUBPROCURADORA", "FISCAL",
    "GOBERNADOR", "GOBERNADORA", "JEFE", "JEFA", "COMANDANTE", "GENERAL", "ALMIRANTE", "EMBAJADOR",
    "EMBAJADORA", "SENADOR", "SENADORA", "DIPUTADO", "DIPUTADA", "MINISTRO", "MINISTRA", "VOCERO",
    "VOCERA", "COMISIONADO", "COMISIONADA", "ALCALDE", "ALCALDESA", "REPRESENTANTE", "MUNICIPAL",
    "ENCARGADO", "ENCARGADA", "DELEGADO", "DELEGADA", "SECRETARIO(A)"})
"""Cargos conocidos que preceden a un nombre o forman el cargo de la marca (lista cerrada)."""
GENERICOS = frozenset({
    "PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA", "INTERLOCUTOR(A)", "INTERVENCIÓN", "VOZ", "VOCES",
    "MODERADOR", "MODERADORA", "REPORTERO", "REPORTERA", "PARTICIPANTE", "PERIODISTA", "ASISTENTE",
    "PÚBLICO", "PUBLICO"})
"""Marcas genéricas: sin entidad."""
_PARTICULAS = frozenset({"DE", "DEL", "LA", "LAS", "EL", "LOS", "Y", "EN", "PARA", "POR"})
_RE_PALABRA = re.compile(r"\S+")


def _persona_en_segmento(seg: str, solo_segmento: bool) -> tuple[int, int] | None:
    """Offsets (dentro de `seg`) de la persona, o None si el segmento es cargo, genérico u otra cosa.

    El cargo inicial solo se quita cuando la marca no tiene comas (`PRESIDENTE ANDRÉS MANUEL ...`).
    Con comas, un segmento que empieza con cargo es el cargo completo (`PROCURADOR FEDERAL DEL
    CONSUMIDOR`) y no se toma como persona.
    """
    palabras = list(_RE_PALABRA.finditer(seg))
    if not palabras or seg != seg.upper():
        return None
    if palabras[0].group() in GENERICOS:
        return None
    i = 0
    while i < len(palabras) and palabras[i].group() in CARGOS:
        i += 1
    if i and not solo_segmento:
        return None
    resto = palabras[i:]
    if not 2 <= len(resto) <= 5 or resto[0].group() in _PARTICULAS:
        return None
    if not all(re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ.'-]*", p.group()) for p in resto):
        return None
    return resto[0].start(), resto[-1].end()


def _marca(texto: str, inicio_cuerpo: int, org_gaz: list[tuple[int, int]]) -> list[Entidad]:
    """PER de la marca (cargo quitado por lista cerrada) y ORG si la marca entera es una ORG."""
    if inicio_cuerpo <= 0:
        return []
    fin_marca = len(texto[:inicio_cuerpo].rstrip(": \t\n"))
    marca = texto[:fin_marca]
    if not marca.strip():
        return []
    ents = []
    if "," not in marca and any(a <= 0 and b >= fin_marca for a, b in org_gaz):
        ents.append(Entidad("ORG", marca, 0, fin_marca, fuente="marca", en_marca=True))
        return ents
    cursor = 0
    segmentos = marca.split(",")
    for seg in segmentos:
        persona = _persona_en_segmento(seg.strip(), len(segmentos) == 1)
        if persona:
            inicio = cursor + (len(seg) - len(seg.lstrip())) + persona[0]
            fin = cursor + (len(seg) - len(seg.lstrip())) + persona[1]
            ents.append(Entidad("PER", texto[inicio:fin], inicio, fin, fuente="marca", en_marca=True))
        cursor += len(seg) + 1
    return ents


# --------------------------------------------------------------------------- colisiones y API


def resolver_colisiones(candidatas: list[Entidad]) -> tuple[list[Entidad], list[dict]]:
    """Gana el span más largo; en empate, la jerarquía de `JERARQUIA`. Devuelve ganadoras y solapes."""
    orden = sorted(candidatas, key=lambda e: (-(e.fin - e.inicio), JERARQUIA[e.fuente], e.inicio))
    ganadoras: list[Entidad] = []
    colisiones: list[dict] = []
    for e in orden:
        choque = next((g for g in ganadoras if e.inicio < g.fin and g.inicio < e.fin), None)
        if choque is None:
            ganadoras.append(e)
            continue
        mas_largo = (choque.fin - choque.inicio) != (e.fin - e.inicio)
        colisiones.append({
            "fuente_ganadora": choque.fuente, "fuente_suprimida": e.fuente,
            "tipo_ganadora": choque.tipo, "tipo_suprimida": e.tipo,
            "inicio_ganadora": choque.inicio, "fin_ganadora": choque.fin,
            "texto_ganador": choque.texto, "inicio_suprimida": e.inicio, "fin_suprimida": e.fin,
            "texto_suprimido": e.texto, "motivo": "span_mas_largo" if mas_largo else "jerarquia"})
    return sorted(ganadoras, key=lambda e: (e.inicio, e.fin)), colisiones


def extraer_reglas_con_colisiones(texto: str, inicio_cuerpo: int, gaz: Gazetteer | None = None,
                                  ) -> tuple[list[Entidad], list[dict]]:
    """Todas las fuentes de reglas, resueltas; devuelve también los solapes suprimidos."""
    gaz = gaz or cargar_gazetteer()
    gazet = _gazetteers(texto, inicio_cuerpo, gaz)
    org_spans = [(e.inicio, e.fin) for e in gazet if e.tipo == "ORG"]
    candidatas = _fechas(texto) + _montos(texto) + gazet + _marca(texto, inicio_cuerpo, org_spans)
    for e in candidatas:
        e.en_marca = e.inicio < inicio_cuerpo
    return resolver_colisiones(candidatas)


def extraer_reglas(texto: str, inicio_cuerpo: int, gaz: Gazetteer | None = None) -> list[Entidad]:
    """API de PRD §6.7.9: entidades por reglas con procedencia (`fuente`, `en_marca`)."""
    return extraer_reglas_con_colisiones(texto, inicio_cuerpo, gaz)[0]


# --------------------------------------------------------------------------- minado de siglas

_NOMBRE = r"(?:[A-ZÁÉÍÓÚÑ][\wáéíóúñü.-]*|de|del|la|las|los|y|e|para)"
RE_NOMBRE_SIGLA = re.compile(
    rf"((?:[A-ZÁÉÍÓÚÑ][\wáéíóúñü.-]*)(?:\s+{_NOMBRE}){{1,7}})\s+\(([A-ZÁÉÍÓÚÑ]{{2,8}})\)")
RE_ROMANO = re.compile(r"[IVXLCDM]+")
RE_TOKEN_MAYUS = re.compile(r"(?<![\wáéíóúñü])[A-ZÁÉÍÓÚÑ]{3,7}(?![\wáéíóúñü])")


def minar_siglas(pasajes: pd.DataFrame, gaz: Gazetteer | None = None, min_frecuencia: int = 5,
                 ) -> pd.DataFrame:
    """Candidatas a sigla para revisión del alumno: `sigla, nombre_propuesto, frecuencia, ejemplo`.

    Solo mira el cuerpo (desde `inicio_cuerpo`), nunca la marca. Excluye lo que ya está en el
    gazetteer y la stoplist. El asistente propone; aceptar o rechazar es decisión del alumno.
    """
    gaz = gaz or cargar_gazetteer()
    conocidas = {t.upper() for t in gaz.terminos("ORG") | gaz.terminos("LOC")}
    paradas = {p.upper() for p in preproceso.stoplist()}
    frecuencia: Counter[str] = Counter()
    nombres: dict[str, Counter[str]] = {}
    ejemplos: dict[str, str] = {}
    for texto, ic in zip(pasajes["texto"], pasajes["inicio_cuerpo"], strict=True):
        cuerpo = texto[int(ic):]
        vistas = set()
        for m in RE_TOKEN_MAYUS.finditer(cuerpo):
            vistas.add(m.group())
            ejemplos.setdefault(m.group(), cuerpo[max(0, m.start() - 40):m.end() + 40].replace("\n", " "))
        for m in RE_NOMBRE_SIGLA.finditer(cuerpo):
            nombre, sigla = m.group(1), m.group(2)
            if nombre[0] == sigla[0]:
                nombres.setdefault(sigla, Counter())[nombre] += 1
                vistas.add(sigla)
                ejemplos.setdefault(sigla, cuerpo[max(0, m.start() - 40):m.end() + 40].replace("\n", " "))
        frecuencia.update(vistas)
    filas = []
    for sigla, n in frecuencia.items():
        if sigla in conocidas or sigla in paradas or n < min_frecuencia or RE_ROMANO.fullmatch(sigla):
            continue  # los números romanos (III, XIX, XXI) no son siglas
        propuesto = nombres[sigla].most_common(1)[0][0] if sigla in nombres else ""
        filas.append({"sigla": sigla, "nombre_propuesto": propuesto, "frecuencia": n,
                      "ejemplo": ejemplos[sigla]})
    df = pd.DataFrame(filas, columns=["sigla", "nombre_propuesto", "frecuencia", "ejemplo"])
    return df.sort_values(["frecuencia", "sigla"], ascending=[False, True]).reset_index(drop=True)
