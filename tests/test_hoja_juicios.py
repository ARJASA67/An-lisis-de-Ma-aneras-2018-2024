"""Hoja de cálculo para juicios colaborativos: ciega, sin precarga, y lectura validada.

Los valores 1/0 de estas pruebas son de formato, en `tmp_path`; nada se escribe en `anotaciones/`.
"""
from __future__ import annotations

import pandas as pd
import pytest
from openpyxl import load_workbook

from mtx import hoja_juicios as h
from mtx import pool
from mtx.app import componentes as c

PL = pd.DataFrame({
    "query_id": ["Q1", "Q1", "Q2", "Q2", "Q2"], "passage_id": ["1_0", "2_0", "1_0", "3_0", "3_1"],
    "doc_id": [1, 2, 1, 3, 3], "fecha": ["2020-01-01", "", "2019-05-01", "2019-06-01", "2019-07-01"],
    "texto": ["=SUMA(1) hola", "texto <b>2", "dos", "tres", "cuatro"],
    "texto_sha256": ["h"] * 5,
    "en_ventana": [True] * 5, "variantes": ["bm25_con_filtro"] * 5,
    "mejor_rango_tfidf": [1] * 5, "mejor_rango_bm25": [2] * 5})
CONS = pd.DataFrame({"query_id": ["Q1", "Q2"], "consulta": ["uno", "dos"],
                     "pregunta_extraccion": ["¿qué?", "¿cómo?"]})
META = pd.DataFrame({"passage_id": ["1_0", "2_0", "3_0", "3_1"], "titulo": ["T"] * 4,
                     "interlocutor": ["I"] * 4}).set_index("passage_id")
CRITERIOS = "# Criterios de relevancia\n\nTrata del tema.\n"


def libro(tmp_path, consultas=("Q1", "Q2")):
    return h.generar(tmp_path / "h.xlsx", PL, CONS, META, CRITERIOS, list(consultas))


def test_pendientes_solo_cuenta_0_y_1():
    j = pd.DataFrame({"query_id": ["Q1", "Q1", "Q2"], "passage_id": ["1_0", "2_0", "1_0"],
                      "relevante": ["1", "0", ""]})
    assert h.consultas_pendientes(PL, j) == ["Q2"]
    assert h.consultas_pendientes(PL, j.iloc[0:0]) == ["Q1", "Q2"]


def test_hoja_es_ciega_y_sin_precarga(tmp_path):
    wb = load_workbook(libro(tmp_path))
    assert wb.sheetnames == ["Q1", "Q2"]
    ws = wb["Q2"]
    encabezado = [ws.cell(row=h.FILA_ENCABEZADO, column=i).value for i in range(1, 9)]
    assert encabezado == h.ENCABEZADOS
    todo = " ".join(str(v) for fila in ws.iter_rows(values_only=True) for v in fila if v is not None)
    for prohibido in ("tfidf", "bm25", "variantes", "mejor_rango", "en_ventana"):
        assert prohibido not in todo.lower()
    assert all(ws.cell(row=r, column=h.COL_RELEVANTE).value is None
               for r in range(h.FILA_ENCABEZADO + 1, ws.max_row + 1))
    assert ws.data_validations.dataValidation[0].formula1 == '"1,0"'


def test_texto_con_igual_o_html_se_conserva_literal(tmp_path):
    ws = load_workbook(libro(tmp_path))["Q1"]
    textos = {ws.cell(row=r, column=2).value: ws.cell(row=r, column=7).value
              for r in range(h.FILA_ENCABEZADO + 1, ws.max_row + 1)}
    assert textos["1_0"] == "=SUMA(1) hola" and textos["2_0"] == "texto <b>2"
    assert ws.cell(row=h.FILA_ENCABEZADO + 1, column=7).data_type == "s"


def test_orden_de_la_hoja_es_el_de_la_app(tmp_path):
    ws = load_workbook(libro(tmp_path))["Q2"]
    ids = [ws.cell(row=r, column=2).value for r in range(h.FILA_ENCABEZADO + 1, ws.max_row + 1)]
    assert ids == pool.orden_presentacion(PL)["Q2"]


def llenar(ruta, q, valores, nombre="Ana"):
    wb = load_workbook(ruta)
    ws = wb[q]
    ws.cell(row=h.FILA_ANOTADOR, column=2, value=nombre)
    for i, v in enumerate(valores):
        ws.cell(row=h.FILA_ENCABEZADO + 1 + i, column=h.COL_RELEVANTE, value=v)
    wb.save(ruta)


def test_leer_normaliza_y_conserva_vacios(tmp_path):
    ruta = libro(tmp_path)
    llenar(ruta, "Q2", [1, 0.0, None])
    hoja, anot = h.leer(ruta)
    q2 = hoja[hoja["query_id"] == "Q2"]["relevante"].tolist()
    assert q2 == ["1", "0", ""] and anot["Q2"] == "Ana" and anot["Q1"] == ""
    assert h.revisar(hoja[hoja["query_id"] == "Q2"], {"Q2": "Ana"}, PL) == []


def test_revisar_detecta_valores_invalidos_y_falta_de_nombre(tmp_path):
    ruta = libro(tmp_path, ["Q2"])
    llenar(ruta, "Q2", ["si", 2, 1], nombre="")
    hoja, anot = h.leer(ruta)
    errores = h.revisar(hoja, anot, PL)
    assert any("nombre del anotador" in e for e in errores)
    assert sum("Valor inválido" in e for e in errores) == 2


def test_revisar_par_fuera_del_pool_y_doc_id(tmp_path):
    hoja = pd.DataFrame({"query_id": ["Q2", "Q2"], "passage_id": ["9_9", "3_0"],
                         "doc_id": ["9", "7"], "relevante": ["1", "0"]})
    errores = h.revisar(hoja, {"Q2": "Ana"}, PL)
    assert any("fuera del pool" in e for e in errores) and any("doc_id incoherente" in e for e in errores)


def test_encabezados_alterados_se_rechazan(tmp_path):
    ruta = libro(tmp_path)
    wb = load_workbook(ruta)
    wb["Q1"].cell(row=h.FILA_ENCABEZADO, column=2, value="otra")
    wb.save(ruta)
    with pytest.raises(ValueError, match="encabezados"):
        h.leer(ruta)


def test_importar_con_almacen_guarda_anotador_y_no_pisa(tmp_path):
    crit = tmp_path / "c.md"
    crit.write_text("ok", encoding="utf-8")
    alm = c.AlmacenJuicios(PL, ruta=tmp_path / "j.csv", ruta_criterios=crit, hash_pool="x")
    alm.registrar("Q2", "1_0", "0", anotador="Ana")
    alm.registrar("Q2", "3_0", "1", anotador="Luis")
    meta = c.leer_meta(tmp_path / "j.csv")
    assert meta["anotadores"] == {"Q2": "Luis"} and meta["pool_sha256"] == "x"
    assert alm.estado("Q2", "1_0") == "0"


def test_doc_id_flotante_de_sheets_se_normaliza(tmp_path):
    ruta = libro(tmp_path, ["Q2"])
    wb = load_workbook(ruta)
    ws = wb["Q2"]
    for r in range(h.FILA_ENCABEZADO + 1, ws.max_row + 1):
        ws.cell(row=r, column=3, value=float(ws.cell(row=r, column=3).value))
    wb.save(ruta)
    hoja, _ = h.leer(ruta)
    assert set(hoja["doc_id"]) <= {"1", "3"}
    assert h.revisar(hoja, {"Q2": "Ana"}, PL) == []
