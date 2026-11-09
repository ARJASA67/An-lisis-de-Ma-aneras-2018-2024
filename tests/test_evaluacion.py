"""T08b · Evaluación de IR: vista con ventana, ganador (D08), etiquetas y reproducibilidad.

Los 0/1 de las pruebas sintéticas son datos de formato; no son juicios del proyecto.
"""
from __future__ import annotations

import filecmp

import pandas as pd
import pytest

from mtx import config
from mtx import evaluacion as ev

P = ev.PROMEDIO


def resultados(q1, q2, no_juzgados=0):
    """Resultados sintéticos con la forma del kit: 2 consultas × 4 variantes + 4 promedios.

    `q1` y `q2` son `(AP de TF-IDF, AP de BM25)` de cada consulta, iguales con y sin filtro.
    """
    filas = []
    for q, (t, b) in {"Q1": q1, "Q2": q2}.items():
        for m in ev.VARIANTES:
            ap = t if m.startswith("tfidf") else b
            filas.append({"query_id": q, "modelo": m, "P@5": 0.5, "P@10": 0.5, "AP": ap,
                          "relevantes_recuperados": 5.0, "relevantes_en_pool": 8.0,
                          "no_juzgados": no_juzgados})
    r = pd.DataFrame(filas)
    prom = r.groupby("modelo")[["P@5", "P@10", "AP"]].mean().round(4).reset_index()
    prom.insert(0, "query_id", P)
    return pd.concat([r, prom], ignore_index=True)


# ------------------------------------------------------------------ aceptación
def test_verificar_resultados_completos():
    assert ev.verificar_resultados(resultados((0.4, 0.6), (0.4, 0.6)), n_consultas=2) == []


def test_verificar_detecta_no_juzgados_y_filas_faltantes():
    malos = ev.verificar_resultados(resultados((0.4, 0.6), (0.4, 0.6), no_juzgados=2), 2)
    assert any("no juzgados" in p for p in malos)
    recortado = resultados((0.4, 0.6), (0.4, 0.6)).iloc[:-2]
    assert any("promedio" in p for p in ev.verificar_resultados(recortado, 2))


# ------------------------------------------------------------------ D08
def test_mejor_modelo_mayor_map_con_filtro():
    r = resultados((0.3, 0.5), (0.3, 0.5))  # MAP tfidf 0.3, bm25 0.5
    m = ev.elegir_mejor_modelo(r)
    assert m["modelo"] == "bm25_con_filtro" and m["alternativa"] == "tfidf_con_filtro"
    assert "diferencia_menor_0.01" not in m


def test_mejor_modelo_tfidf_si_gana():
    m = ev.elegir_mejor_modelo(resultados((0.7, 0.2), (0.7, 0.2)))
    assert m["modelo"] == "tfidf_con_filtro" and m["map"] == pytest.approx(0.7)


def test_empate_exacto_va_a_bm25():
    m = ev.elegir_mejor_modelo(resultados((0.4, 0.4), (0.4, 0.4)))
    assert m["modelo"] == "bm25_con_filtro" and m["empate_exacto"] is True
    assert m["diferencia_menor_0.01"] is True


def test_diferencia_menor_a_0_01_se_marca_sin_cambiar_la_regla():
    r = resultados((0.40, 0.405), (0.40, 0.405))  # MAP 0.40 vs 0.405
    m = ev.elegir_mejor_modelo(r)
    assert m["modelo"] == "bm25_con_filtro" and m["diferencia_menor_0.01"] is True


def test_el_modelo_sin_filtro_nunca_se_elige():
    r = resultados((0.1, 0.2), (0.1, 0.2))
    r.loc[(r["modelo"] == "bm25_sin_filtro") & (r["query_id"] == P), "AP"] = 0.99
    assert ev.elegir_mejor_modelo(r)["modelo"] in ev.MODELOS_CON_FILTRO


# ------------------------------------------------------------------ ventana
POOL = pd.DataFrame({"query_id": ["Q1"] * 4, "passage_id": ["a", "b", "c", "d"],
                     "en_ventana": ["True", "False", "True", "False"],
                     "fecha": ["2020-01-01", "2019-01-01", "2020-02-02", ""]})
JUI = pd.DataFrame({"query_id": ["Q1"] * 4, "doc_id": [1, 2, 3, 4],
                    "passage_id": ["a", "b", "c", "d"], "relevante": [1, 1, 0, 1]})


def test_relevante_ventana_exige_ventana_y_fecha_conocida():
    j = ev.juicios_con_ventana(JUI, POOL)
    assert j["relevante_ventana"].tolist() == [1, 0, 0, 0]  # b fuera; c no relevante; d sin fecha


def test_conteo_por_ventana_separa_fuera_y_desconocida():
    c = ev.relevantes_por_ventana(ev.juicios_con_ventana(JUI, POOL)).iloc[0]
    assert (c["relevantes_tematicos"], c["dentro_de_ventana"], c["fuera_de_ventana"],
            c["fecha_desconocida"]) == (3, 1, 1, 1)


def test_ventana_rechaza_juicios_fuera_del_pool():
    extra = pd.concat([JUI, pd.DataFrame({"query_id": ["Q1"], "doc_id": [9], "passage_id": ["z"],
                                          "relevante": [1]})])
    with pytest.raises(ValueError, match="fuera del pool"):
        ev.juicios_con_ventana(extra, POOL)


# ------------------------------------------------------------------ tablas y etiquetas
def test_ganador_con_empate_y_diferencia():
    r = resultados((0.5, 0.3), (0.4, 0.4))  # Q1 gana TF-IDF; Q2 empata
    etiq = pd.DataFrame({"query_id": ["Q1", "Q2"], "longitud": ["corta", "larga"]})
    g = ev.ganador_por_consulta(r, etiq).set_index("query_id")
    assert g.loc["Q1", "ganador"] == "tfidf_con_filtro"
    assert g.loc["Q1", "diferencia_bm25_menos_tfidf"] == pytest.approx(-0.2)
    assert g.loc["Q2", "ganador"] == "empate" and g.loc["Q2", "longitud"] == "larga"


def test_tabla_ancha_una_fila_por_consulta():
    a = ev.tabla_ancha(resultados((0.3, 0.5), (0.5, 0.5)))
    assert list(a["query_id"]) == ["Q1", "Q2"]
    assert "AP__bm25_con_filtro" in a.columns and "no_juzgados__tfidf_sin_filtro" in a.columns


def test_sigla_y_nombre_propio():
    f = ev.tiene_sigla_o_nombre_propio
    assert f("llegada de vacunas contra el COVID-19") and f("avances del Tren Maya")
    assert f("operación del Banco del Bienestar")
    assert not f("combate al huachicol y robo de combustible")
    assert not f("pensión universal para adultos mayores")


def test_etiquetas_longitud_df_y_sinonimos():
    cons = pd.DataFrame({"query_id": ["Q1", "Q2", "Q3"],
                         "consulta": ["huachicol", "refinería de Dos Bocas en Tabasco",
                                      "programa social amplio para adultos mayores hoy"]})
    df = {"huachicol": 5, "refin": 2000, "dos": 3000, "boc": 10, "tabasc": 20}
    e = ev.etiquetas_consultas(cons, df, 100_000, ev.cargar_sinonimos()).set_index("query_id")
    assert e.loc["Q2", "terminos_df_alto"] == 2  # refin y dos superan el 1 %
    assert "huachicol" in e.loc["Q1", "sinonimos_conocidos"]
    assert "refineria_dos_bocas" in e.loc["Q2", "sinonimos_conocidos"]
    assert "adultos_mayores" in e.loc["Q3", "sinonimos_conocidos"]
    assert e.loc["Q1", "longitud"] == "corta" and e.loc["Q3", "longitud"] == "larga"


# ------------------------------------------------------------------ reproducibilidad (lenta)
@pytest.mark.lento
@pytest.mark.skipif(not (config.RAIZ / "resultados_ir.csv").exists(),
                    reason="falta resultados_ir.csv (make evaluar-ir)")
def test_resultados_oficiales_se_regeneran_con_el_kit(tmp_path):
    res = ev.evaluar_oficial(config.RAIZ / "juicios_relevancia.csv", config.RAIZ / "ranking.csv",
                             tmp_path)
    assert filecmp.cmp(tmp_path / "resultados_ir.csv", config.RAIZ / "resultados_ir.csv",
                       shallow=False)
    assert ev.verificar_resultados(res) == []
