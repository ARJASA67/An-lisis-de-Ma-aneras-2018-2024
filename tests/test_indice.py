"""T03 · Índice invertido a mano contra `CountVectorizer` (PRD §6.3)."""
from __future__ import annotations

import pickle
import random
import subprocess
import sys

import numpy as np
import pytest

from mtx import indice, preproceso
from mtx.indice import construir, identidad, matriz_conteos

# Fixture sintético con conteos conocidos. Las marcas de interlocutor van fuera de los cuerpos:
# "lópez" y "obrador" solo aparecen en la marca, así que deben tener df = 0 en ambos lados.
MARCAS = ["PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: ", "REPORTERO ZORRILLO XIMÉNEZ: "]
CUERPOS = [
    "el tren maya avanza y el tren llega",
    "la vacuna llega a la refineria",
    "tren vacuna vacuna vacuna",
    "huachicol en la refineria de dos bocas",
    "",
    "el el el el",
]


@pytest.fixture(scope="module")
def sintetico():
    ids = [f"{i}_0" for i in range(len(CUERPOS))]
    # Se tokeniza solo el cuerpo (D03): `tokenizar_pasaje` descarta la marca.
    tokens = [preproceso.tokenizar_pasaje(MARCAS[i % 2] + c, len(MARCAS[i % 2]))
              for i, c in enumerate(CUERPOS)]
    return ids, tokens, construir(ids, tokens)


def test_conteos_conocidos(sintetico):
    _, tokens, ind = sintetico
    t = preproceso.tokenizar
    assert ind.N == len(CUERPOS)
    tren, vacuna = t("tren")[0], t("vacuna")[0]
    assert ind.postings[tren] == {0: 2, 2: 1}
    assert ind.df[tren] == 2
    assert ind.postings[vacuna] == {1: 1, 2: 3}
    assert ind.df[vacuna] == 2
    assert ind.longitud[4] == 0  # cuerpo vacío: longitud cero, sin romper
    assert ind.avgdl == pytest.approx(sum(len(x) for x in tokens) / len(tokens))


def test_nombres_solo_en_marcas_tienen_df_cero(sintetico):
    _, tokens, ind = sintetico
    vec, _ = matriz_conteos(tokens)
    for nombre in ("zorrillo", "ximénez", "reportero"):
        raiz = preproceso.tokenizar(nombre)
        assert raiz, f"{nombre} debe sobrevivir al preproceso para que la prueba no sea vacía"
        for r in raiz:
            assert ind.df.get(r, 0) == 0
            assert r not in vec.vocabulary_


def _comparar(ind, tokens, terminos):
    vec, X = matriz_conteos(tokens)
    X = X.tocsc()
    for t in terminos:
        col = vec.vocabulary_.get(t)
        if col is None:
            assert ind.df.get(t, 0) == 0
            continue
        fila = X[:, col]
        assert ind.df[t] == fila.nnz, t
        assert sum(ind.postings[t].values()) == int(fila.sum()), t
        for idx, tf in ind.postings[t].items():
            assert tf == fila[idx, 0], (t, idx)


def test_fixture_coincide_con_countvectorizer(sintetico):
    _, tokens, ind = sintetico
    _comparar(ind, tokens, list(ind.postings))


def test_50_terminos_aleatorios_coinciden_con_countvectorizer():
    """Vocabulario sintético con distribución sesgada, semilla fija."""
    rng = random.Random(42)
    vocab = [f"t{i}" for i in range(300)]
    pesos = [1 / (i + 1) for i in range(300)]
    tokens = [rng.choices(vocab, weights=pesos, k=rng.randint(0, 60)) for _ in range(400)]
    ids = [f"{i}_0" for i in range(len(tokens))]
    ind = construir(ids, tokens)
    muestra = rng.sample(vocab, 50)
    _comparar(ind, tokens, muestra)
    # Todo el vocabulario coincide en tamaño y en suma total de conteos.
    vec, X = matriz_conteos(tokens)
    assert len(vec.vocabulary_) == len(ind.postings)
    assert int(X.sum()) == int(ind.longitud.sum())


def test_idf_bm25_es_positivo_y_cero_si_no_existe(sintetico):
    _, _, ind = sintetico
    assert ind.idf_bm25("inexistente") == 0.0
    assert all(ind.idf_bm25(t) > 0 for t in ind.postings)  # variante con idf positivo, incluso df > N/2


def test_cantidad_de_listas_distinta_de_ids_falla():
    with pytest.raises(ValueError):
        construir(["a", "b"], [["x"]])


def test_idx_de_es_estable(sintetico):
    ids, _, ind = sintetico
    assert [ind.idx_de[p] for p in ids] == list(range(len(ids)))


def test_identidad_es_de_modulo_y_el_indice_se_carga_en_otro_proceso(sintetico, tmp_path):
    assert identidad.__module__ == "mtx.indice" and identidad.__name__ == "identidad"
    _, tokens, ind = sintetico
    pkl, meta = tmp_path / "i.pkl", tmp_path / "m.json"
    indice.guardar(ind, pkl, meta, hash_tokens="h1", hash_config="c1")
    vec, _ = matriz_conteos(tokens)
    vpkl = tmp_path / "v.pkl"
    vpkl.write_bytes(pickle.dumps(vec, protocol=5))
    codigo = (
        "import pickle,sys; from mtx import indice;"
        f"i=indice.cargar(r'{pkl}'); v=pickle.load(open(r'{vpkl}','rb'));"
        "print(i.N, len(v.vocabulary_))"
    )
    out = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=True)
    assert out.stdout.split() == [str(ind.N), str(len(vec.vocabulary_))]


def test_cargar_rechaza_indice_con_hash_distinto(sintetico, tmp_path):
    _, _, ind = sintetico
    pkl, meta = tmp_path / "i.pkl", tmp_path / "m.json"
    indice.guardar(ind, pkl, meta, hash_tokens="h1", hash_config="c1")
    assert indice.cargar(pkl, meta, hash_tokens="h1").N == ind.N
    with pytest.raises(ValueError):
        indice.cargar(pkl, meta, hash_tokens="otro")


def test_marca_fuera_de_los_tokens_del_indice():
    """Cambiar solo la marca no altera tokens ni conteos (D03)."""
    cuerpo = "el tren maya avanza"
    a = preproceso.tokenizar_pasaje("PRESIDENTE: " + cuerpo, len("PRESIDENTE: "))
    b = preproceso.tokenizar_pasaje("REPORTERO ZETA: " + cuerpo, len("REPORTERO ZETA: "))
    assert a == b
    ia, ib = construir(["0_0"], [a]), construir(["0_0"], [b])
    assert ia.postings == ib.postings and np.array_equal(ia.longitud, ib.longitud)
