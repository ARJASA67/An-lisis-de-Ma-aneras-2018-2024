"""T04 a T06 · TF-IDF, BM25 propio, filtro de fecha y top-k (PRD §6.4, U9, U10)."""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from rank_bm25 import BM25Okapi  # solo desarrollo: nunca se importa desde src/mtx

from mtx import preproceso
from mtx.indice import construir
from mtx.ranking import (
    BM25,
    Buscador,
    ajustar_tfidf,
    mascara_fecha,
    top_k,
    validar_ventana,
    variantes_oficiales,
)


def armar(docs):
    """docs: lista de (doc_id, posicion, fecha|None, tokens). Devuelve `(Buscador, indice)`."""
    ids = [f"{d}_{p}" for d, p, _, _ in docs]
    tokens = [t for *_, t in docs]
    ind = construir(ids, tokens)
    pasajes = pd.DataFrame({
        "passage_id": ids, "doc_id": [d for d, *_ in docs], "posicion": [p for _, p, *_ in docs],
        "fecha": pd.to_datetime([f for _, _, f, _ in docs]),
    })
    vec, X = ajustar_tfidf(tokens)
    from mtx.ranking import Tfidf
    return Buscador(ind, Tfidf(vec, X), pasajes), ind


# ------------------------------------------------------------------ T04: fórmulas a mano

CORPUS = [["a", "a", "b"], ["b", "c"], ["c", "c", "c", "d"]]  # N=3, avgdl=3


def test_bm25_a_mano():
    ind = construir(["0_0", "1_0", "2_0"], CORPUS)
    k1, b, N, avgdl = 1.5, 0.75, 3, 3.0
    idf_a = math.log(1 + (N - 1 + 0.5) / (1 + 0.5))   # df(a) = 1
    idf_b = math.log(1 + (N - 2 + 0.5) / (2 + 0.5))   # df(b) = 2

    def parte(tf, dl):
        return tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))

    esperado = np.array([
        idf_a * parte(2, 3) + idf_b * parte(1, 3),
        idf_b * parte(1, 2),
        0.0,
    ])
    np.testing.assert_allclose(BM25(ind).puntajes(["a", "b"]), esperado, atol=1e-12)


def test_bm25_repetidos_cuentan_una_vez_y_ausentes_cero():
    ind = construir(["0_0", "1_0", "2_0"], CORPUS)
    m = BM25(ind)
    np.testing.assert_array_equal(m.puntajes(["a", "a", "a"]), m.puntajes(["a"]))
    np.testing.assert_array_equal(m.puntajes(["a", "zzz"]), m.puntajes(["a"]))
    r = m.puntajes(["zzz"])
    assert not np.isnan(r).any() and (r == 0).all()


def test_tfidf_a_mano():
    vec, X = ajustar_tfidf(CORPUS)
    from mtx.ranking import Tfidf
    N, df = 3, {"a": 1, "b": 2, "c": 2, "d": 1}

    def w(t, tf):
        return (1 + math.log(tf)) * (math.log((1 + N) / (1 + df[t])) + 1)

    def vector(tf_por_termino):
        v = {t: w(t, tf) for t, tf in tf_por_termino.items()}
        n = math.sqrt(sum(x * x for x in v.values()))
        return {t: x / n for t, x in v.items()}

    docs = [vector({"a": 2, "b": 1}), vector({"b": 1, "c": 1}), vector({"c": 3, "d": 1})]
    q = vector({"a": 1, "c": 1})
    esperado = [sum(q.get(t, 0) * x for t, x in d.items()) for d in docs]
    np.testing.assert_allclose(Tfidf(vec, X).puntajes(["a", "c"]), esperado, atol=1e-12)


def test_tfidf_consulta_nula_da_ceros_sin_nan():
    vec, X = ajustar_tfidf(CORPUS)
    from mtx.ranking import Tfidf
    for q in (["zzz"], []):
        r = Tfidf(vec, X).puntajes(q)
        assert not np.isnan(r).any() and (r == 0).all()


def _corpus_aleatorio(n=200, seed=7):
    rng = random.Random(seed)
    vocab = [f"t{i}" for i in range(60)]
    pesos = [1 / (i + 1) for i in range(60)]  # los primeros términos tienen df > N/2
    return [rng.choices(vocab, weights=pesos, k=rng.randint(3, 40)) for _ in range(n)], vocab


class _Okapi(BM25Okapi):
    """`BM25Okapi` con el idf propio: `ln(1 + (N - df + 0.5) / (df + 0.5))`."""

    def _calc_idf(self, nd):
        for termino, df in nd.items():
            self.idf[termino] = math.log(1 + (self.corpus_size - df + 0.5) / (df + 0.5))


def test_consistencia_con_rank_bm25_con_idf_propio():
    corpus, vocab = _corpus_aleatorio()
    ind = construir([f"{i}_0" for i in range(len(corpus))], corpus)
    propio, ref = BM25(ind), _Okapi(corpus, k1=1.5, b=0.75)
    rng = random.Random(1)
    for _ in range(5):
        consulta = list(dict.fromkeys(rng.sample(vocab, 4) + ["inexistente"]))
        np.testing.assert_allclose(propio.puntajes(consulta), ref.get_scores(consulta), atol=1e-6)


def test_sin_la_subclase_rank_bm25_difiere():
    """Documenta por qué se necesita la subclase: el idf de `BM25Okapi` es otro. Con términos de
    df > N/2 además aplica un piso epsilon, que vuelve las diferencias más marcadas."""
    corpus, vocab = _corpus_aleatorio()
    ind = construir([f"{i}_0" for i in range(len(corpus))], corpus)
    frecuentes = [t for t in vocab if ind.df.get(t, 0) > ind.N / 2]
    assert frecuentes, "el fixture debe tener términos con df > N/2"
    consulta = frecuentes[:2]
    dif = np.abs(BM25(ind).puntajes(consulta) - BM25Okapi(corpus).get_scores(consulta)).max()
    assert dif > 1e-3


def test_ranking_py_no_importa_rank_bm25():
    import mtx.ranking as r
    assert "rank_bm25" not in Path(r.__file__).read_text(encoding="utf-8")


# ------------------------------------------------------------------ T05: filtro de fecha

FECHAS = np.array(["2020-01-01", "2020-06-15", "2020-06-16", "NaT", "2021-01-01"],
                  dtype="datetime64[ns]")


def test_ventana_inclusiva_en_los_limites_exactos():
    m = mascara_fecha(FECHAS, "2020-06-15", "2020-06-16")
    assert m.tolist() == [False, True, True, False, False]


def test_nat_fuera_con_filtro_y_dentro_sin_filtro():
    assert mascara_fecha(FECHAS, None, None).tolist() == [True] * 5
    assert mascara_fecha(FECHAS, "2000-01-01", "2030-01-01").tolist() == [True, True, True, False,
                                                                          True]


def test_ventana_abierta_por_un_lado():
    assert mascara_fecha(FECHAS, "2020-06-16", None).tolist() == [False, False, True, False, True]
    assert mascara_fecha(FECHAS, None, "2020-06-15").tolist() == [True, True, False, False, False]
    assert mascara_fecha(FECHAS, "", "2020-06-15").tolist() == [True, True, False, False, False]


def test_ventana_invertida_o_invalida_es_error_claro():
    with pytest.raises(ValueError, match="invertida"):
        mascara_fecha(FECHAS, "2021-01-01", "2020-01-01")
    with pytest.raises(ValueError, match="inválido"):
        validar_ventana("no-es-fecha", None)


def test_desde_igual_a_hasta_es_un_solo_dia():
    assert mascara_fecha(FECHAS, "2020-06-15", "2020-06-15").tolist() == [False, True, False,
                                                                           False, False]


# ------------------------------------------------------------------ T06: top-k y desempates


def _punt(n):
    return np.arange(n, dtype=float)[::-1].copy()


@pytest.mark.parametrize("n_elegibles", [0, 3, 10])
def test_top_k_con_cero_tres_y_diez_candidatos(n_elegibles):
    n = 25
    elegibles = np.zeros(n, dtype=bool)
    elegibles[:n_elegibles] = True
    doc, pos = np.arange(n), np.zeros(n, dtype=int)
    sel = top_k(np.ones(n), elegibles, doc, pos, 10)
    assert len(sel) == n_elegibles and elegibles[sel].all()  # nunca se cuelan excluidos


def test_top_k_recorta_a_diez_y_no_rellena_con_excluidos():
    n = 40
    elegibles = np.arange(n) < 15
    puntajes = np.where(elegibles, 0.0, 99.0)  # los excluidos tienen los mejores puntajes
    sel = top_k(puntajes, elegibles, np.arange(n), np.zeros(n, dtype=int))
    assert len(sel) == 10 and elegibles[sel].all()


def test_desempate_numerico_por_doc_id_y_posicion():
    """`10_2` quedaría antes que `9_1` si se ordenara como cadena (U9)."""
    doc = np.array([10, 9, 9, 10])
    pos = np.array([2, 1, 0, 0])
    sel = top_k(np.ones(4), np.ones(4, dtype=bool), doc, pos)
    assert [(doc[i], pos[i]) for i in sel] == [(9, 0), (9, 1), (10, 0), (10, 2)]


def test_el_puntaje_manda_sobre_el_desempate():
    doc, pos = np.array([1, 2, 3]), np.zeros(3, dtype=int)
    sel = top_k(np.array([0.5, 0.9, 0.5]), np.ones(3, dtype=bool), doc, pos)
    assert sel.tolist() == [1, 0, 2]


DOCS = [
    (1, 0, "2020-01-10", ["tren", "maya", "tren"]),
    (1, 1, "2020-01-10", ["refineria", "dos", "boca"]),
    (2, 0, "2021-05-01", ["tren", "maya"]),
    (9, 1, None, ["tren", "vacuna"]),
    (10, 0, "2022-02-02", ["vacuna", "huachicol"]),
    (10, 1, "2022-02-02", ["otro", "tema"]),
]


@pytest.mark.parametrize("modelo", ["bm25", "tfidf"])
def test_buscar_respeta_ventana_y_no_rellena(modelo):
    b, _ = armar(DOCS)
    res, est = b.buscar("tren", "2020-01-01", "2020-12-31", modelo)
    assert set(res["passage_id"]) <= {"1_0", "1_1"}
    assert len(res) == 2 and est["elegibles"] == 2
    assert est["excluidos_por_filtro"] == 4 and est["excluidos_fecha_desconocida"] == 1
    assert any("no se rellena" in a for a in est["avisos"])


def test_buscar_sin_filtro_incluye_fecha_desconocida():
    b, _ = armar(DOCS)
    res, est = b.buscar("vacuna", modelo="bm25")
    assert "9_1" in set(res["passage_id"])
    assert est["excluidos_por_filtro"] == 0 and len(res) == 6


def test_termino_desconocido_marca_sin_senal_lexica():
    b, _ = armar(DOCS)
    res, est = b.buscar("zzzz", modelo="bm25")
    assert (res["puntaje"] == 0).all() and (res["sin_senal_lexica"] == 1).all()
    assert any("sin señal" in a for a in est["avisos"])


def test_consulta_vacia_devuelve_aviso_y_ninguna_fila():
    b, _ = armar(DOCS)
    res, est = b.buscar("el de la", modelo="bm25")
    assert len(res) == 0 and est["tokens"] == [] and est["avisos"]


def test_ventana_invertida_en_buscar_lanza_error():
    b, _ = armar(DOCS)
    with pytest.raises(ValueError):
        b.buscar("tren", "2022-01-01", "2020-01-01")


def test_modelo_desconocido():
    b, _ = armar(DOCS)
    with pytest.raises(ValueError):
        b.buscar("tren", modelo="lsa")


def test_desempate_en_buscar_ordena_por_doc_id_numerico():
    docs = [(10, 0, "2020-01-01", ["tren"]), (9, 1, "2020-01-01", ["tren"]),
            (2, 3, "2020-01-01", ["tren"])]
    b, _ = armar(docs)
    res, _ = b.buscar("tren", modelo="bm25")
    assert res["passage_id"].tolist() == ["2_3", "9_1", "10_0"]


def test_cambiar_solo_la_marca_no_altera_puntajes_ni_orden():
    cuerpos = ["el tren maya llega a la peninsula", "la vacuna contra covid llega",
               "tren de carga y tren de pasajeros"]

    def construir_con(marcas):
        docs = []
        for i, (m, c) in enumerate(zip(marcas, cuerpos)):
            toks = preproceso.tokenizar_pasaje(m + c, len(m))
            docs.append((i, 0, "2020-01-01", toks))
        return armar(docs)[0]

    a = construir_con(["PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: "] * 3)
    b = construir_con(["REPORTERA ZORRILLA: ", "PRESIDENTE: ", "INTERLOCUTOR: "])
    for modelo in ("bm25", "tfidf"):
        ra, _ = a.buscar("tren maya", modelo=modelo)
        rb, _ = b.buscar("tren maya", modelo=modelo)
        pd.testing.assert_frame_equal(ra, rb)


def test_cuatro_variantes_por_consulta_y_columnas():
    b, _ = armar(DOCS)
    consultas = pd.DataFrame({"query_id": ["Q1"], "consulta": ["tren maya"],
                              "desde": ["2020-01-01"], "hasta": ["2020-12-31"]})
    r = variantes_oficiales(b, consultas)
    assert list(r.columns) == ["query_id", "modelo", "variante", "rango", "passage_id", "doc_id",
                               "fecha", "posicion", "puntaje", "sin_senal_lexica"]
    assert set(r["modelo"]) == {"tfidf_con_filtro", "bm25_con_filtro", "tfidf_sin_filtro",
                                "bm25_sin_filtro"}
    assert set(r[r["variante"] == "con_filtro"]["passage_id"]) <= {"1_0", "1_1"}
    assert not r.duplicated(["query_id", "modelo", "rango"]).any()
    assert not r.duplicated(["query_id", "modelo", "passage_id"]).any()


def test_buscador_exige_el_mismo_orden_que_el_indice():
    ind = construir(["0_0", "1_0"], [["a"], ["b"]])
    pas = pd.DataFrame({"passage_id": ["1_0", "0_0"], "doc_id": [1, 0], "posicion": [0, 0],
                        "fecha": pd.to_datetime(["2020-01-01", "2020-01-01"])})
    vec, X = ajustar_tfidf([["a"], ["b"]])
    from mtx.ranking import Tfidf
    with pytest.raises(ValueError):
        Buscador(ind, Tfidf(vec, X), pas)
