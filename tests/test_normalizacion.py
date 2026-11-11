"""Normalización prudente (PRD §6.10): ≥15 montos, ≥10 fechas y no mezcla con los spans."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from mtx import normalizacion as nz

ANCLA = pd.Timestamp("2021-11-15")


@pytest.mark.parametrize("texto, valor, moneda, escala", [
    ("2 mil 500 millones de pesos", "2500000000", "MXN", "millones"),
    ("mil 200 millones de pesos", "1200000000", "MXN", "millones"),
    ("tres mil millones de dólares", "3000000000", "USD", "mil_millones"),
    ("20 mil millones de pesos", "20000000000", "MXN", "mil_millones"),
    ("$1,200 millones", "1200000000", "", "millones"),
    ("$500 pesos", "500", "MXN", "uno"),
    ("un millón de pesos", "1000000", "MXN", "millones"),
    ("1.5 billones de pesos", "1500000000000", "MXN", "billones"),
    ("2,5 millones de dólares", "2500000", "USD", "millones"),
    ("45 mil pesos", "45000", "MXN", "mil"),
    ("$3,500", "3500", "", "uno"),
    ("100 dolares", "100", "USD", "uno"),
    ("cien millones de pesos", "100000000", "MXN", "millones"),
])
def test_montos_con_valor(texto, valor, moneda, escala):
    r = nz.normalizar_monto(texto)
    assert (r["valor_num"], r["moneda"], r["escala"], r["estado_monto"]) == (
        valor, moneda, escala, "ok")


def test_monto_rango_comparte_escala():
    r = nz.normalizar_monto("entre 2 y 3 mil millones de pesos")
    assert (r["valor_min"], r["valor_max"], r["estado_monto"], r["valor_num"]) == (
        "2000000000", "3000000000", "rango", "")


def test_monto_ambiguo_sin_cifra():
    r = nz.normalizar_monto("varios millones de pesos")
    assert r["estado_monto"] == "ambiguo" and r["valor_num"] == ""


def test_billon_implausible_es_ambiguo():
    r = nz.normalizar_monto("500 billones de pesos")
    assert r["estado_monto"] == "ambiguo" and r["valor_num"] == ""


def test_decimal_estable_sin_notacion_cientifica():
    from decimal import Decimal
    assert nz.decimal_estable(Decimal("2.5E+9")) == "2500000000"
    assert nz.decimal_estable(Decimal("12.50")) == "12.5"


@pytest.mark.parametrize("texto, iso, precision, estado", [
    ("15 de enero de 2021", "2021-01-15", "dia", "ok"),
    ("diciembre de 2021", "2021-12", "mes", "ok"),
    ("2019", "2019", "anio", "ok"),
    ("29 de febrero de 2020", "2020-02-29", "dia", "ok"),
    ("29 de febrero de 2021", "", "dia", "invalida"),
    ("31 de abril de 2022", "", "dia", "invalida"),
    ("15/03/21", "2021-03-15", "dia", "ok"),
    ("15/03/99", "", "dia", "anio_ambiguo"),
])
def test_fechas_absolutas(texto, iso, precision, estado):
    r = nz.normalizar_fecha(texto, ANCLA)
    assert (r["fecha_iso"], r["precision_fecha"], r["estado_fecha"]) == (iso, precision, estado)
    assert r["resuelta_desde_ancla"] is False


def test_intervalo_y_intervalo_invertido():
    r = nz.normalizar_fecha("1 al 15 de marzo de 2020", ANCLA)
    assert (r["fecha_inicio"], r["fecha_fin"], r["precision_fecha"]) == (
        "2020-03-01", "2020-03-15", "intervalo")
    assert nz.normalizar_fecha("15 al 1 de marzo de 2020", ANCLA)["estado_fecha"] == "invalida"


def test_relativas_con_ancla():
    p = nz.normalizar_fecha("próximo 15 de enero", ANCLA)
    assert (p["fecha_iso"], p["fecha_relativo"], p["resuelta_desde_ancla"]) == (
        "2022-01-15", "proximo", True)
    q = nz.normalizar_fecha("pasado 20 de noviembre", ANCLA)
    assert q["fecha_iso"] == "2020-11-20"
    s = nz.normalizar_fecha("3 de diciembre", ANCLA)
    assert (s["fecha_iso"], s["fecha_ancla"]) == ("2021-12-03", "2021-11-15")


def test_relativa_sin_ancla_queda_parcial():
    for ancla in (None, pd.NaT, pd.Timestamp("1990-01-01")):
        r = nz.normalizar_fecha("próximo 15 de enero", ancla)
        assert (r["estado_fecha"], r["fecha_iso"], r["fecha_ancla"]) == ("parcial", "", "")


def test_identidad_org_por_gazetteer_y_sin_equivalencia():
    r = nz.normalizar_identidad("ORG", "Sedena")
    assert (r["canonico"], r["estado_identidad"]) == ("Secretaría de la Defensa Nacional",
                                                      "gazetteer")
    r = nz.normalizar_identidad("ORG", "Empresa Inventada")
    assert (r["canonico"], r["estado_identidad"]) == ("", "sin_equivalencia")
    assert nz.texto_normalizado("  Secretaría  de Energía ") == "secretaria de energia"
    assert nz.texto_normalizado("Peña") == "peña"


def test_personas_por_sufijo_y_apellido_ambiguo():
    ps = [{"texto_normalizado": t, "canonico": "", "estado_identidad": ""} for t in
          ("rocio nahle garcia", "nahle garcia", "garcia", "luisa maria alcalde")]
    nz.vincular_personas(ps)
    assert ps[1]["canonico"] == "rocio nahle garcia"
    assert ps[1]["estado_identidad"] == "vinculado_por_sufijo"
    # «garcia» es sufijo de dos nombres distintos: no se vincula.
    assert ps[2]["canonico"] == "" and ps[3]["canonico"] == ""


def test_no_mezcla_con_spans():
    fila = {"texto": "20 mil millones de pesos", "inicio": 10, "fin": 34}
    antes = dict(fila)
    nz.normalizar_monto(fila["texto"])
    nz.normalizar_fecha("15 de enero de 2021", date(2021, 1, 1))
    assert fila == antes
