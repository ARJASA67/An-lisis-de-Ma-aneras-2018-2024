"""T07 y T08 · Pool de relevancia y validación de formato de juicios (PRD §6.5, D06).

Los archivos de juicios de estas pruebas son sintéticos, viven en `tmp_path` y solo verifican
formato y cobertura; nunca se escriben en `anotaciones/`.
"""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from mtx import pool

CONS = pd.DataFrame({
    "query_id": ["Q1", "Q2"], "desde": ["2020-01-01", "2019-01-01"],
    "hasta": ["2020-12-31", "2019-12-31"]})


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def pasajes():
    ids = [f"{d}_{p}" for d in (1, 2, 3) for p in (0, 1, 2)]
    textos = [f"texto {i}" for i in ids]
    fechas = ["2020-03-01"] * 3 + ["2019-05-01"] * 3 + [None] * 3
    return pd.DataFrame({
        "passage_id": ids, "doc_id": [int(i.split("_")[0]) for i in ids],
        "fecha": pd.to_datetime(fechas), "texto": textos, "texto_sha256": [sha(t) for t in textos]})


def fila(q, m, r, p):
    return {"query_id": q, "modelo": m, "rango": r, "passage_id": p}


def ranking_solapado():
    """Cuatro rankings parcialmente solapados para Q1; uno propio para Q2."""
    q1 = {
        "tfidf_con_filtro": ["1_0", "1_1", "1_2"],
        "bm25_con_filtro": ["1_1", "1_0", "2_0"],
        "tfidf_sin_filtro": ["1_0", "3_0", "1_1"],
        "bm25_sin_filtro": ["2_0", "1_1", "3_1"],
    }
    filas = [fila("Q1", m, i + 1, p) for m, ps in q1.items() for i, p in enumerate(ps)]
    filas += [fila("Q2", "tfidf_con_filtro", 1, "1_0"), fila("Q2", "bm25_con_filtro", 1, "2_0")]
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ T07: unión exacta
def test_union_exacta_sin_duplicados():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    q1 = p[p["query_id"] == "Q1"]
    assert set(q1["passage_id"]) == {"1_0", "1_1", "1_2", "2_0", "3_0", "3_1"}
    assert not q1["passage_id"].duplicated().any()
    assert list(p.columns) == pool.COLUMNAS_POOL


def test_procedencia_y_mejores_rangos():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    f = p[(p["query_id"] == "Q1") & (p["passage_id"] == "1_1")].iloc[0]
    assert f["variantes"] == "tfidf_con_filtro|bm25_con_filtro|tfidf_sin_filtro|bm25_sin_filtro"
    assert (f["mejor_rango_tfidf"], f["mejor_rango_bm25"]) == (2, 1)
    g = p[(p["query_id"] == "Q1") & (p["passage_id"] == "3_1")].iloc[0]
    assert g["variantes"] == "bm25_sin_filtro" and g["mejor_rango_tfidf"] == ""


def test_en_ventana_con_fecha_desconocida_falsa():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    q1 = p[p["query_id"] == "Q1"].set_index("passage_id")["en_ventana"]
    assert q1["1_0"] and not q1["2_0"] and not q1["3_0"]  # 2019 fuera, fecha desconocida fuera


def test_hash_coincide_con_texto():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    assert all(sha(t) == h for t, h in zip(p["texto"], p["texto_sha256"]))


def test_pasaje_ausente_o_modelo_desconocido_falla():
    r = ranking_solapado()
    with pytest.raises(ValueError, match="ausentes de pasajes"):
        pool.construir_pool(pd.concat([r, pd.DataFrame([fila("Q1", "tfidf_con_filtro", 9, "9_9")])]),
                            pasajes(), CONS)
    with pytest.raises(ValueError, match="desconocidas"):
        pool.construir_pool(pd.concat([r, pd.DataFrame([fila("Q1", "otro", 1, "1_0")])]),
                            pasajes(), CONS)


# ------------------------------------------------------------------ T08: juicio por consulta
def test_pasaje_compartido_entre_consultas_son_dos_filas():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    assert len(p[p["passage_id"] == "1_0"]) == 2
    assert set(p[p["passage_id"] == "1_0"]["query_id"]) == {"Q1", "Q2"}


# ------------------------------------------------------------------ orden y avisos
def test_orden_determinista_y_completo():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    a, b = pool.orden_presentacion(p), pool.orden_presentacion(p)
    assert a == b
    assert sorted(a["Q1"]) == sorted(p[p["query_id"] == "Q1"]["passage_id"])
    assert a["Q1"] != sorted(a["Q1"])  # barajado, no alfabético


def test_orden_no_depende_del_orden_de_filas():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    assert pool.orden_presentacion(p) == pool.orden_presentacion(p.sample(frac=1, random_state=1))


def test_avisos_de_tamano():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    avisos = pool.avisos_tamano(p, CONS)
    assert any("Q1" in a and "6 pasajes" in a for a in avisos)


def test_diferencias_detecta_cambios():
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    assert pool.diferencias_pool(p, p.copy()) == []
    menos = p[~((p["query_id"] == "Q1") & (p["passage_id"] == "3_1"))]
    assert any("3_1" in d for d in pool.diferencias_pool(menos, p))
    cambiado = p.copy()
    cambiado.loc[0, "texto_sha256"] = "x"
    assert any("texto cambiado" in d for d in pool.diferencias_pool(cambiado, p))


def test_roundtrip_csv_conserva_pool(tmp_path):
    p = pool.construir_pool(ranking_solapado(), pasajes(), CONS)
    pool.escribir_pool(p, tmp_path / "pool.csv")
    assert pool.diferencias_pool(p, pool.leer_pool(tmp_path / "pool.csv")) == []


# ------------------------------------------------------------------ validar_juicios (formato)
@pytest.fixture
def pl():
    return pool.construir_pool(ranking_solapado(), pasajes(), CONS)


def escribir(tmp_path, pl, relevante=None, quitar=0, extra=None, bom=False):
    """Archivo sintético solo de formato: alterna 0/1 por posición."""
    j = pl[["query_id", "doc_id", "passage_id"]].copy()
    j["relevante"] = [str(i % 2) if relevante is None else relevante for i in range(len(j))]
    if quitar:
        j = j.iloc[:-quitar]
    if extra is not None:
        j = pd.concat([j, pd.DataFrame([extra])])
    ruta = tmp_path / "juicios.csv"
    j.to_csv(ruta, index=False, encoding="utf-8-sig" if bom else "utf-8", lineterminator="\n")
    return ruta


def test_juicios_completos_pasan(tmp_path, pl):
    errores, avisos = pool.validar_juicios(escribir(tmp_path, pl), pl, pasajes())
    assert errores == [] and avisos == []


def test_cobertura_incompleta_es_error(tmp_path, pl):
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, quitar=2), pl, pasajes())
    assert any("Cobertura incompleta" in e for e in errores)


def test_pendiente_vacio_no_es_cero(tmp_path, pl):
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, relevante=""), pl, pasajes())
    assert any("Cobertura incompleta" in e for e in errores)


def test_valor_fuera_de_0_1(tmp_path, pl):
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, relevante="2"), pl, pasajes())
    assert any("inválido" in e for e in errores)


def test_par_fuera_del_pool_y_doc_id_incoherente(tmp_path, pl):
    extra = {"query_id": "Q2", "doc_id": 3, "passage_id": "3_2", "relevante": "0"}
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, extra=extra), pl, pasajes())
    assert any("fuera del pool" in e for e in errores)
    ruta = escribir(tmp_path, pl)
    j = pd.read_csv(ruta, dtype=str)
    j.loc[0, "doc_id"] = "99"
    j.to_csv(ruta, index=False, lineterminator="\n")
    errores, _ = pool.validar_juicios(ruta, pl, pasajes())
    assert any("doc_id incoherente" in e for e in errores)


def test_juicio_repetido(tmp_path, pl):
    extra = {"query_id": "Q1", "doc_id": 1, "passage_id": "1_0", "relevante": "1"}
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, extra=extra), pl, pasajes())
    assert any("repetido" in e for e in errores)


def test_bom_y_columnas(tmp_path, pl):
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl, bom=True), pl, pasajes())
    assert any("BOM" in e for e in errores)
    ruta = tmp_path / "mal.csv"
    ruta.write_text("query_id,passage_id,relevante\nQ1,1_0,1\n", encoding="utf-8")
    errores, _ = pool.validar_juicios(ruta, pl, pasajes())
    assert any("Columnas" in e for e in errores)


def test_corpus_cambiado_detectado_por_hash(tmp_path, pl):
    p = pasajes()
    p.loc[p["passage_id"] == "1_0", "texto_sha256"] = "otro"
    errores, _ = pool.validar_juicios(escribir(tmp_path, pl), pl, p)
    assert any("texto_sha256" in e for e in errores)


def test_consulta_sin_relevantes_avisa_sin_error(tmp_path, pl):
    errores, avisos = pool.validar_juicios(escribir(tmp_path, pl, relevante="0"), pl, pasajes())
    assert errores == []
    assert any("AP indefinido para Q1" in a for a in avisos)


def test_archivo_inexistente(tmp_path, pl):
    errores, _ = pool.validar_juicios(tmp_path / "no.csv", pl, pasajes())
    assert errores and "No existe" in errores[0]
