"""Normalización prudente de entidades (PRD §6.10). Nunca toca `inicio`, `fin` ni `texto`.

FECHA: ISO según precisión (día, mes, año, intervalo); relativas `próximo`/`pasado`/`este` y fechas
sin año se resuelven con la fecha del discurso como ancla solo si es válida. MONTO: `Decimal`,
valor en unidades, escala, moneda (MXN, USD o vacía: `$` solo no fija moneda), rangos y ambiguos
sin valor. ORG/LOC: `canonico` solo por equivalencia verificada del gazetteer. PER: alias por
sufijo dentro del mismo pasaje.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pandas as pd

from mtx import reglas

ANCLA_MIN, ANCLA_MAX = date(2018, 1, 1), date(2024, 12, 31)
LIMITE_PLAUSIBLE = Decimal(10) ** 14
"""Un monto de 100 billones o más (escala larga) supera varias veces el PIB de México: se marca
ambiguo porque probablemente es un billón de escala corta (10^9) mal leído."""

_RE_ABS = re.compile(reglas._P_ABSOLUTA, re.IGNORECASE)
_RE_INT = re.compile(reglas._P_INTERVALO, re.IGNORECASE)
_RE_DEC_COMA = re.compile(r"(\d),(\d{1,2})(?!\d)")
_RE_RANGO = re.compile(r"^(?:entre\s+)?(?P<a>.+?)\s+(?:y|a)\s+(?P<b>.+)$", re.IGNORECASE)
_RE_HAY_CIFRA = re.compile(rf"\d|\b(?:{reglas.PALABRA_NUM}|mil)\b", re.IGNORECASE)

CAMPOS_FECHA = ["fecha_iso", "fecha_inicio", "fecha_fin", "precision_fecha", "fecha_relativo",
                "fecha_ancla", "resuelta_desde_ancla", "estado_fecha"]
CAMPOS_MONTO = ["valor_num", "valor_min", "valor_max", "moneda", "escala", "estado_monto"]
CAMPOS_IDENTIDAD = ["canonico", "texto_normalizado", "estado_identidad"]


# --------------------------------------------------------------------------- texto


def texto_normalizado(texto: str) -> str:
    """Minúsculas, sin acentos (conserva la ñ) y espacios colapsados, para agrupar."""
    t = unicodedata.normalize("NFD", texto.lower().replace("ñ", "\x00"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").replace("\x00", "ñ")
    return " ".join(t.split())


# --------------------------------------------------------------------------- FECHA


def ancla_valida(fecha) -> date | None:
    """La fecha del discurso como `date` si es válida y está en el rango del corpus."""
    if fecha is None or pd.isna(fecha):  # None o NaT
        return None
    d = fecha.date() if hasattr(fecha, "date") else fecha
    if not isinstance(d, date):
        return None
    return d if ANCLA_MIN <= d <= ANCLA_MAX else None


def _siguiente(dia: int, mes: int, ancla: date, hacia: int) -> date | None:
    """Ocurrencia estricta siguiente (`hacia=1`) o anterior (`-1`) de día/mes respecto al ancla."""
    for anio in ((ancla.year, ancla.year + 1) if hacia > 0 else (ancla.year, ancla.year - 1)):
        try:
            d = date(anio, mes, dia)
        except ValueError:
            continue
        if (d > ancla) if hacia > 0 else (d < ancla):
            return d
    return None


def normalizar_fecha(texto: str, ancla=None) -> dict:
    """Campos de tiempo de `entidades_enriquecidas.csv` para una FECHA."""
    a = reglas.analizar_fecha(texto)
    anc = ancla_valida(ancla)
    out = {"fecha_iso": a["fecha_iso"], "fecha_inicio": a["fecha_inicio"],
           "fecha_fin": a["fecha_fin"], "precision_fecha": a["precision"],
           "fecha_relativo": a["modificador"], "fecha_ancla": anc.isoformat() if anc else "",
           "resuelta_desde_ancla": False, "estado_fecha": a["estado"]}
    if a["estado"] != "parcial":
        return out
    if anc is None:
        return out  # sin ancla válida queda parcial
    if a["precision"] == "intervalo":
        m = _RE_INT.fullmatch(texto)
        mes = reglas._MESES[m["mes"].lower()]
        d1, d2 = reglas._dia(m["d1"]), reglas._dia(m["d2"])
        try:
            ini, fin = date(anc.year, mes, d1), date(anc.year, mes, d2)
        except ValueError:
            return {**out, "estado_fecha": "invalida"}
        return {**out, "fecha_inicio": ini.isoformat(), "fecha_fin": fin.isoformat(),
                "resuelta_desde_ancla": True, "estado_fecha": "ok"}
    m = _RE_ABS.fullmatch(texto)
    dia, mes = reglas._dia(m["dia"]), reglas._MESES[m["mes"].lower()]
    mod = a["modificador"]
    if mod in ("proximo", "pasado"):
        d = _siguiente(dia, mes, anc, 1 if mod == "proximo" else -1)
    else:
        try:
            d = date(anc.year, mes, dia)
        except ValueError:
            d = None
    if d is None:
        return {**out, "estado_fecha": "invalida"}
    return {**out, "fecha_iso": d.isoformat(), "resuelta_desde_ancla": True, "estado_fecha": "ok"}


# --------------------------------------------------------------------------- MONTO


def decimal_estable(v: Decimal | None) -> str:
    """Representación decimal sin notación científica ni ceros sobrantes."""
    if v is None:
        return ""
    s = format(v, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _escala(t: str) -> str:
    if re.search(r"\bbill[oó]n(es)?\b", t):
        return "billones"
    if re.search(r"\bmil\s+mill[oó]n(es)?\b", t):
        return "mil_millones"
    if re.search(r"\bmill[oó]n(es)?\b", t):
        return "millones"
    if re.search(r"\bmil\b", t):
        return "mil"
    return "uno"


def _moneda(t: str) -> str:
    if re.search(r"\bd[oó]lares\b|\busd\b", t):
        return "USD"
    if re.search(r"\bpesos\b|\bmxn\b", t):
        return "MXN"
    return ""


def _valor(expr: str) -> Decimal:
    return reglas.valor_cifra(_RE_DEC_COMA.sub(r"\1.\2", expr))


def normalizar_monto(texto: str) -> dict:
    """Campos de dinero de `entidades_enriquecidas.csv` para un MONTO."""
    t = texto.lower()
    out = {"valor_num": "", "valor_min": "", "valor_max": "", "moneda": _moneda(t),
           "escala": _escala(t), "estado_monto": "ok"}
    if not _RE_HAY_CIFRA.search(t):
        return {**out, "estado_monto": "ambiguo"}  # «varios millones de pesos»
    rango = _RE_RANGO.match(t)
    if rango and _RE_HAY_CIFRA.search(rango["a"]) and _RE_HAY_CIFRA.search(rango["b"]):
        a, b = rango["a"], rango["b"]
        # La escala y la moneda escritas al final aplican a ambos extremos («entre 2 y 3 mil
        # millones»): se copian al extremo izquierdo si no las trae.
        cola = re.search(r"(mil\s+)?(mill[oó]n(es)?|bill[oó]n(es)?)", b)
        if cola and not re.search(r"mill|bill", a):
            a = f"{a} {cola.group()}"
        va, vb = _valor(a), _valor(b)
        if va > vb:
            return {**out, "estado_monto": "ambiguo"}
        return {**out, "valor_min": decimal_estable(va), "valor_max": decimal_estable(vb),
                "estado_monto": "rango"}
    v = _valor(t)
    if v <= 0:
        return {**out, "estado_monto": "ambiguo"}
    if out["escala"] == "billones" and v >= LIMITE_PLAUSIBLE:
        return {**out, "estado_monto": "ambiguo"}
    return {**out, "valor_num": decimal_estable(v)}


# --------------------------------------------------------------------------- ORG/LOC y PER


@lru_cache(maxsize=2)
def equivalencias(ruta: str = str(reglas.GAZETTEER_EXTENDIDO)) -> dict[str, str]:
    """`texto_normalizado` de nombre, variante o sigla → nombre canónico del gazetteer."""
    eq: dict[str, str] = {}
    with open(Path(ruta), encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            for n in [fila["nombre"], *reglas._partir(fila["variantes"]),
                      *reglas._partir(fila["siglas"])]:
                eq.setdefault(texto_normalizado(n), fila["nombre"])
    return eq


def normalizar_identidad(tipo: str, texto: str) -> dict:
    tn = texto_normalizado(texto)
    if tipo in ("ORG", "LOC"):
        canon = equivalencias().get(tn, "")
        return {"canonico": canon, "texto_normalizado": tn,
                "estado_identidad": "gazetteer" if canon else "sin_equivalencia"}
    if tipo == "PER":
        return {"canonico": "", "texto_normalizado": tn, "estado_identidad": ""}
    return {"canonico": "", "texto_normalizado": tn, "estado_identidad": ""}


def vincular_personas(personas: list[dict]) -> None:
    """En un mismo pasaje: si el nombre A es sufijo por palabras de B, A apunta a B (in situ).

    `personas` son dicts con `texto_normalizado`; se escriben `canonico` y `estado_identidad`.
    Compartir solo el apellido con dos nombres distintos no vincula (ambigüedad).
    """
    for p in personas:
        palabras = p["texto_normalizado"].split()
        largos = {q["texto_normalizado"] for q in personas
                  if len(q["texto_normalizado"].split()) > len(palabras)
                  and q["texto_normalizado"].split()[-len(palabras):] == palabras}
        if len(largos) == 1:
            p["canonico"] = largos.pop()
            p["estado_identidad"] = "vinculado_por_sufijo"
