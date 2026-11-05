"""T01 · Pruebas de contrato del kit del profesor (PRD §3, §13.1).

Verifican firmas, esquemas y comportamiento real de `kit/corpus.py`, `kit/consultas.csv`,
`kit/gazetteer_dependencias.csv` y `kit/evaluar.py` con fixtures sintéticos construidos aquí.
Nunca leen juicios ni gold reales. El kit se importa y se ejecuta solo vía `adaptadores_kit`.
"""
from __future__ import annotations

import inspect
import re
import subprocess
import sys

import pandas as pd
import pytest

from mtx import adaptadores_kit as ak

# --------------------------------------------------------------------------- utilidades


@pytest.fixture(scope="module")
def corpus():
    return ak.cargar_modulo_corpus()


def escribir_csv(ruta, filas, columnas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas, columns=columnas).to_csv(ruta, index=False)
    return ruta


COLS_JUICIOS = ["query_id", "doc_id", "passage_id", "relevante"]
COLS_RANKING = ["query_id", "modelo", "variante", "rango", "passage_id", "doc_id", "fecha",
                "posicion", "puntaje"]
COLS_GOLD = ["passage_id", "tipo", "texto", "inicio", "fin"]
COLS_ENTIDADES = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin", "metodo"]


def fila_ranking(q, rango, pid, modelo="bm25_con_filtro"):
    doc = int(pid.split("_")[0])
    return [q, modelo, modelo.split("_", 1)[1], rango, pid, doc, "2020-01-01", 0, 10.0 - rango]


def evaluar_ir(tmp_path, juicios, ranking, columnas_ranking=COLS_RANKING):
    j = escribir_csv(tmp_path / "j.csv", juicios, COLS_JUICIOS)
    r = escribir_csv(tmp_path / "r.csv", ranking, columnas_ranking)
    return pd.read_csv(ak.ejecutar_evaluador("ir", j, r, tmp_path / "out"))


def evaluar_ie(tmp_path, gold, entidades):
    g = escribir_csv(tmp_path / "g.csv", gold, COLS_GOLD)
    e = escribir_csv(tmp_path / "e.csv", entidades, COLS_ENTIDADES)
    return pd.read_csv(ak.ejecutar_evaluador("ie", g, e, tmp_path / "out"))


def celda(res, **filtro):
    sub = res
    for k, v in filtro.items():
        sub = sub[sub[k] == v]
    assert len(sub) == 1, f"se esperaba una fila para {filtro}, hay {len(sub)}"
    return sub.iloc[0]


# --------------------------------------------------------------------------- integridad del kit


def test_hashes_del_kit_coinciden_con_los_originales():
    assert ak.verificar_hashes() == []


def test_los_cuatro_archivos_del_kit_existen():
    for nombre in ak.ARCHIVOS_KIT:
        assert (ak.DIR_KIT / nombre).is_file(), nombre


# --------------------------------------------------------------------------- kit/corpus.py


def test_firmas_de_corpus(corpus):
    esperadas = {
        "cargar_corpus": ["forzar"],
        "limpiar_basico": ["texto"],
        "partir_por_interlocutor": ["texto"],
        "ventanas": ["tokens", "tam", "paso"],
        "segmentar_pasajes": ["df", "tam", "paso", "min_tokens"],
    }
    for nombre, params in esperadas.items():
        assert list(inspect.signature(getattr(corpus, nombre)).parameters) == params, nombre
    assert inspect.signature(corpus.cargar_corpus).parameters["forzar"].default is False
    pas = inspect.signature(corpus.segmentar_pasajes).parameters
    assert (pas["tam"].default, pas["paso"].default, pas["min_tokens"].default) == (200, 150, 40)


def test_expresion_de_interlocutor_del_prd(corpus):
    assert corpus.RE_INTERLOCUTOR.pattern == r"^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ ,.\-\(\)]{2,80}):\s*"
    assert corpus.RE_INTERLOCUTOR.flags & re.MULTILINE


def _dataset_falso(filas):
    class Falso:
        def to_pandas(self):
            return pd.DataFrame(filas)
    return Falso()


@pytest.fixture
def corpus_aislado(tmp_path, monkeypatch):
    """Módulo del kit con la caché apuntando a un directorio temporal y `load_dataset` falso."""
    modulo = ak.cargar_modulo_corpus()
    monkeypatch.setattr(modulo, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(modulo, "CACHE", tmp_path / "data" / "discursos.parquet")
    llamadas = []
    filas = [
        {"url": "u0", "título": "T0", "fecha": "2020-01-02", "texto": "uno"},
        {"url": "u1", "título": "T1", "fecha": "no es fecha", "texto": None},
        {"url": "u2", "título": "T2", "fecha": "2021-05-06", "texto": "tres"},
        {"url": "u3", "título": "T3", "fecha": None, "texto": "cuatro"},
    ]

    def load_dataset(nombre, split):
        llamadas.append((nombre, split))
        return _dataset_falso(filas)

    import datasets
    monkeypatch.setattr(datasets, "load_dataset", load_dataset)
    return modulo, llamadas


def test_cargar_corpus_esquema_y_doc_id(corpus_aislado):
    modulo, llamadas = corpus_aislado
    df = modulo.cargar_corpus()
    assert llamadas == [("carevies/discursos_AMLO", "train")]
    assert list(df.columns) == ["doc_id", "url", "titulo", "fecha", "texto"]
    # La fila con texto nulo se elimina antes de asignar doc_id: consecutivo 0..N-1.
    assert df["doc_id"].tolist() == [0, 1, 2]
    assert df["url"].tolist() == ["u0", "u2", "u3"]
    assert df["fecha"].dtype.kind == "M"
    assert df["fecha"].isna().tolist() == [False, False, True]


def test_cargar_corpus_usa_cache_y_forzar(corpus_aislado):
    modulo, llamadas = corpus_aislado
    modulo.cargar_corpus()
    assert modulo.CACHE.exists()
    modulo.cargar_corpus()
    assert len(llamadas) == 1
    modulo.cargar_corpus(forzar=True)
    assert len(llamadas) == 2


def test_limpiar_basico_conserva_saltos_para_interlocutores(corpus):
    sucio = "PREGUNTA:   hola\r\n\r\n\r\nPRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR:  que   tal  "
    limpio = corpus.limpiar_basico(sucio)
    assert limpio == "PREGUNTA: hola\n\nPRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: que tal"
    marcas = [m.group(1) for m in corpus.RE_INTERLOCUTOR.finditer(limpio)]
    assert marcas == ["PREGUNTA", "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR"]


def test_limpiar_basico_casos_limite(corpus):
    assert corpus.limpiar_basico("a\n\n\n\n\nb") == "a\n\nb"
    assert corpus.limpiar_basico("a\nb") == "a\nb"  # un salto simple se conserva
    assert corpus.limpiar_basico("\t a \t") == "a"
    # Una línea que solo contiene un espacio no se cuenta como salto doble.
    assert corpus.limpiar_basico("a\n \nb") == "a\n \nb"


def test_partir_por_interlocutor(corpus):
    assert corpus.partir_por_interlocutor("sin marcas aquí") == [("", "sin marcas aquí")]
    assert corpus.partir_por_interlocutor("prefacio\nPREGUNTA: hola\nPRESIDENTE: adiós") == [
        ("", "prefacio"), ("PREGUNTA", "hola"), ("PRESIDENTE", "adiós")]
    assert corpus.partir_por_interlocutor("") == [("", "")]
    # Marca sin texto: se descarta.
    assert corpus.partir_por_interlocutor("PREGUNTA:\nPRESIDENTE: hola") == [("PRESIDENTE", "hola")]


@pytest.mark.parametrize("n, tamanos", [
    (0, [0]), (1, [1]), (200, [200]), (201, [200, 51]), (250, [200, 100]),
    (350, [200, 200]), (351, [200, 200, 51]),
])
def test_ventanas_tamano_y_traslape(corpus, n, tamanos):
    tokens = [f"t{i}" for i in range(n)]
    ventanas = corpus.ventanas(tokens, 200, 150)
    assert [len(v.split()) for v in ventanas] == tamanos


def test_ventanas_traslape_de_50_tokens(corpus):
    tokens = [f"t{i}" for i in range(350)]
    v0, v1 = (v.split() for v in corpus.ventanas(tokens, 200, 150))
    assert v0[150:] == v1[:50]


def test_menos_tokens_que_la_ventana_da_una_sola(corpus):
    assert corpus.ventanas(["a", "b", "c"], 200, 150) == ["a b c"]


def test_segmentar_pasajes_esquema_y_descartes(corpus):
    df = pd.DataFrame({
        "doc_id": [0, 1], "url": ["u", "v"], "titulo": ["T0", "T1"],
        "fecha": pd.to_datetime(["2020-01-01", None]),
        "texto": ["PREGUNTA: " + " ".join(["a"] * 50) + "\nPRESIDENTE: " + " ".join(["b"] * 30),
                  " ".join(["x"] * 300)],
    })
    p = corpus.segmentar_pasajes(df)
    assert list(p.columns) == ["passage_id", "doc_id", "fecha", "titulo", "posicion",
                               "interlocutor", "texto"]
    # La intervención de 30 palabras queda bajo min_tokens=40 y se descarta.
    assert p["passage_id"].tolist() == ["0_0", "1_0", "1_1"]
    assert p["posicion"].tolist() == [0, 0, 1]
    assert p["interlocutor"].tolist() == ["PREGUNTA", "", ""]
    assert p["fecha"].isna().tolist() == [False, True, True]
    # El texto del pasaje NO lleva la marca de interlocutor (el PRD §6.1 la reinyecta).
    assert not p["texto"].iloc[0].startswith("PREGUNTA")


# --------------------------------------------------------------------------- kit/consultas.csv

CONSULTAS_PRD = [
    ("Q1", "avances en la construcción del Tren Maya", "2020-01-01", "2023-12-31",
     "Qué dependencias y empresas participan, en qué estados y con qué montos"),
    ("Q2", "llegada y aplicación de vacunas contra el COVID-19", "2020-12-01", "2021-12-31",
     "Qué farmacéuticas, qué funcionarios y qué fechas y cantidades de dosis"),
    ("Q3", "refinería de Dos Bocas en Tabasco", "2019-01-01", "2022-12-31",
     "Qué organizaciones, qué personas responsables y qué montos de inversión"),
    ("Q4", "aeropuerto Felipe Ángeles en Santa Lucía", "2019-01-01", "2022-06-30",
     "Qué dependencia construye, qué lugares se mencionan y qué costos"),
    ("Q5", "programa Sembrando Vida y apoyo a campesinos", "2019-01-01", "2024-12-31",
     "Qué secretaría lo opera, en qué estados y con qué monto por beneficiario"),
    ("Q6", "combate al huachicol y robo de combustible", "2018-12-01", "2019-06-30",
     "Qué lugares, qué organizaciones y qué cifras de pérdidas o litros"),
    ("Q7", "pensión universal para adultos mayores", "2018-12-01", "2024-12-31",
     "Qué montos bimestrales, qué institución paga y qué fechas de aumento"),
    ("Q8", "aumento al salario mínimo y acuerdo con empresarios", "2018-12-01", "2024-01-31",
     "Qué organizaciones empresariales, qué porcentajes y qué montos diarios"),
]


def test_consultas_del_kit_coinciden_literalmente_con_el_prd():
    df = pd.read_csv(ak.DIR_KIT / "consultas.csv", dtype=str, keep_default_na=False)
    assert list(df.columns) == ["query_id", "consulta", "desde", "hasta", "pregunta_extraccion"]
    assert [tuple(f) for f in df.itertuples(index=False)] == CONSULTAS_PRD


# --------------------------------------------------------------------------- gazetteer


def test_gazetteer_del_kit():
    df = pd.read_csv(ak.DIR_KIT / "gazetteer_dependencias.csv", dtype=str, keep_default_na=False)
    assert list(df.columns) == ["nombre", "siglas", "tipo"]
    assert len(df) == 76
    assert set(df["tipo"]) == {
        "dependencia", "organismo", "organismo autónomo", "empresa",
        "empresa productiva del Estado", "obra", "organización empresarial", "partido",
        "organismo internacional", "poder judicial"}
    assert (df["tipo"] == "obra").sum() == 4


# --------------------------------------------------------------------------- evaluar.py · IR


def test_ir_solo_lee_cuatro_columnas_del_ranking(tmp_path):
    juicios = [["Q1", 1, "1_0", 1], ["Q1", 2, "2_0", 0]]
    nueve = [fila_ranking("Q1", 1, "1_0"), fila_ranking("Q1", 2, "2_0")]
    res9 = evaluar_ir(tmp_path / "a", juicios, nueve)
    cuatro = [[q, m, r, p] for q, m, _v, r, p, *_ in nueve]
    res4 = evaluar_ir(tmp_path / "b", juicios, cuatro, ["query_id", "modelo", "rango", "passage_id"])
    pd.testing.assert_frame_equal(res9, res4)


def test_ir_columnas_de_salida_y_fila_de_promedio(tmp_path):
    res = evaluar_ir(tmp_path, [["Q1", 1, "1_0", 1]], [fila_ranking("Q1", 1, "1_0")])
    assert list(res.columns) == ["query_id", "modelo", "P@5", "P@10", "AP",
                                 "relevantes_recuperados", "relevantes_en_pool", "no_juzgados"]
    prom = celda(res, query_id="PROMEDIO (MAP = AP)")
    assert prom["modelo"] == "bm25_con_filtro"
    assert prom["AP"] == 1.0
    assert prom[["relevantes_recuperados", "relevantes_en_pool", "no_juzgados"]].isna().all()


def test_ir_ap_divide_entre_relevantes_del_pool(tmp_path):
    # 4 relevantes en el pool; la lista recupera 2 (rangos 1 y 3) y un pasaje no juzgado.
    juicios = [["Q1", i, f"{i}_0", 1] for i in (1, 2, 3, 4)] + [["Q1", 5, "5_0", 0]]
    ranking = [fila_ranking("Q1", 1, "1_0"), fila_ranking("Q1", 2, "9_0"),
               fila_ranking("Q1", 3, "3_0")]
    res = evaluar_ir(tmp_path, juicios, ranking)
    q1 = celda(res, query_id="Q1")
    assert q1["AP"] == pytest.approx((1 / 1 + 2 / 3) / 4, abs=1e-4)  # no entre los 2 recuperados
    assert q1["relevantes_recuperados"] == 2
    assert q1["relevantes_en_pool"] == 4
    assert q1["no_juzgados"] == 1  # pasaje no juzgado cuenta como no relevante


def test_ir_lista_con_menos_de_k_no_falla_ni_rellena(tmp_path):
    juicios = [["Q1", 1, "1_0", 1], ["Q1", 3, "3_0", 1]]
    ranking = [fila_ranking("Q1", 1, "1_0"), fila_ranking("Q1", 2, "2_0"),
               fila_ranking("Q1", 3, "3_0")]
    q1 = celda(evaluar_ir(tmp_path, juicios, ranking), query_id="Q1")
    assert q1["P@5"] == pytest.approx(2 / 5)
    assert q1["P@10"] == pytest.approx(2 / 10)


def test_ir_consulta_sin_relevantes_da_ap_cero_y_entra_al_promedio(tmp_path):
    juicios = [["Q1", 1, "1_0", 1], ["Q2", 6, "6_0", 0]]
    ranking = [fila_ranking("Q1", 1, "1_0"), fila_ranking("Q2", 1, "6_0")]
    res = evaluar_ir(tmp_path, juicios, ranking)
    assert celda(res, query_id="Q2")["AP"] == 0.0
    assert celda(res, query_id="PROMEDIO (MAP = AP)")["AP"] == pytest.approx(0.5)


def test_ir_consulta_sin_juicios_se_evalua_en_silencio_con_ceros(tmp_path):
    # Caracterización: el kit no avisa. La validación del proyecto debe exigir cobertura.
    res = evaluar_ir(tmp_path, [["Q1", 1, "1_0", 1]],
                     [fila_ranking("Q1", 1, "1_0"), fila_ranking("Q9", 1, "7_0")])
    q9 = celda(res, query_id="Q9")
    assert (q9["AP"], q9["relevantes_en_pool"], q9["no_juzgados"]) == (0.0, 0, 1)


def test_ir_juicios_duplicados_inflan_el_denominador(tmp_path):
    # Caracterización: el denominador cuenta filas, no pasajes distintos.
    juicios = [["Q1", 1, "1_0", 1], ["Q1", 1, "1_0", 1]]
    q1 = celda(evaluar_ir(tmp_path, juicios, [fila_ranking("Q1", 1, "1_0")]), query_id="Q1")
    assert q1["relevantes_en_pool"] == 2
    assert q1["AP"] == pytest.approx(0.5)


def test_ir_una_corrida_produce_un_promedio_por_modelo(tmp_path):
    juicios = [["Q1", 1, "1_0", 1], ["Q1", 2, "2_0", 1]]
    ranking = [fila_ranking("Q1", 1, "1_0", "bm25_con_filtro"),
               fila_ranking("Q1", 1, "2_0", "tfidf_con_filtro")]
    res = evaluar_ir(tmp_path, juicios, ranking)
    prom = res[res["query_id"] == "PROMEDIO (MAP = AP)"]
    assert set(prom["modelo"]) == {"bm25_con_filtro", "tfidf_con_filtro"}


def test_ir_ranking_vacio_revienta(tmp_path):
    j = escribir_csv(tmp_path / "j.csv", [["Q1", 1, "1_0", 1]], COLS_JUICIOS)
    r = escribir_csv(tmp_path / "r.csv", [], ["query_id", "modelo", "rango", "passage_id"])
    with pytest.raises(RuntimeError, match="KeyError"):
        ak.ejecutar_evaluador("ir", j, r, tmp_path / "out")


def test_el_evaluador_escribe_en_el_directorio_actual(tmp_path):
    j = escribir_csv(tmp_path / "j.csv", [["Q1", 1, "1_0", 1]], COLS_JUICIOS)
    r = escribir_csv(tmp_path / "r.csv", [fila_ranking("Q1", 1, "1_0")], COLS_RANKING)
    destino = tmp_path / "cwd"
    destino.mkdir()
    subprocess.run([sys.executable, str(ak.DIR_KIT / "evaluar.py"), "ir", str(j), str(r)],
                   cwd=destino, check=True, capture_output=True)
    assert (destino / "resultados_ir.csv").is_file()


def test_evaluar_sin_argumentos_sale_con_error(tmp_path):
    p = subprocess.run([sys.executable, str(ak.DIR_KIT / "evaluar.py")], check=False, cwd=tmp_path,
                       capture_output=True, text=True)
    assert p.returncode == 1


def test_modo_desconocido_en_el_adaptador(tmp_path):
    with pytest.raises(ValueError):
        ak.ejecutar_evaluador("xx", tmp_path / "a", tmp_path / "b", tmp_path)


# --------------------------------------------------------------------------- evaluar.py · IE


def ent(q, pid, tipo, texto, ini, fin, metodo):
    return [q, int(pid.split("_")[0]), pid, tipo, texto, ini, fin, metodo]


def test_ie_columnas_de_salida_y_orden_de_metodos(tmp_path):
    res = evaluar_ie(tmp_path, [["1_0", "ORG", "Fonatur", 88, 95]],
                     [ent("Q1", "1_0", "ORG", "Fonatur", 88, 95, "ambos")])
    assert list(res.columns) == ["metodo", "tipo", "precision", "recall", "f1", "tp",
                                 "predichas", "gold"]
    assert list(dict.fromkeys(res["metodo"])) == ["regla", "modelo", "combinado"]
    assert celda(res, metodo="combinado", tipo="TODOS")["f1"] == 1.0


def test_ie_entidad_desplazada_un_caracter_es_error(tmp_path):
    res = evaluar_ie(tmp_path, [["1_0", "ORG", "Fonatur", 88, 95]],
                     [ent("Q1", "1_0", "ORG", "Fonatur", 89, 96, "ambos")])
    fila = celda(res, metodo="combinado", tipo="TODOS")
    assert (fila["tp"], fila["predichas"], fila["gold"]) == (0, 1, 1)


def test_ie_el_texto_no_interviene_en_la_coincidencia(tmp_path):
    res = evaluar_ie(tmp_path, [["1_0", "ORG", "Fonatur", 88, 95]],
                     [ent("Q1", "1_0", "ORG", "OTRO TEXTO", 88, 95, "regla")])
    assert celda(res, metodo="regla", tipo="TODOS")["tp"] == 1


def test_ie_metodos_regla_modelo_ambos(tmp_path):
    gold = [["1_0", "ORG", "A", 0, 1], ["1_0", "LOC", "B", 5, 6], ["1_0", "PER", "C", 9, 10]]
    pred = [ent("Q1", "1_0", "ORG", "A", 0, 1, "regla"),
            ent("Q1", "1_0", "LOC", "B", 5, 6, "modelo"),
            ent("Q1", "1_0", "PER", "C", 9, 10, "ambos")]
    res = evaluar_ie(tmp_path, gold, pred)
    assert celda(res, metodo="regla", tipo="TODOS")["tp"] == 2     # regla + ambos
    assert celda(res, metodo="modelo", tipo="TODOS")["tp"] == 2    # modelo + ambos
    assert celda(res, metodo="combinado", tipo="TODOS")["tp"] == 3


def test_ie_metodo_desconocido_no_revienta_y_solo_cuenta_en_combinado(tmp_path):
    # Diferencia con el PRD: no se descarta en todos los métodos.
    gold = [["1_0", "ORG", "A", 0, 1]]
    pred = [ent("Q1", "1_0", "ORG", "A", 0, 1, "otro"), ent("Q1", "1_0", "ORG", "B", 5, 6, "otro")]
    res = evaluar_ie(tmp_path, gold, pred)
    assert celda(res, metodo="regla", tipo="TODOS")["predichas"] == 0
    assert celda(res, metodo="modelo", tipo="TODOS")["predichas"] == 0
    assert celda(res, metodo="combinado", tipo="TODOS")["predichas"] == 2


def test_ie_deduplica_la_misma_entidad_entre_consultas(tmp_path):
    gold = [["1_0", "ORG", "Fonatur", 88, 95]]
    pred = [ent("Q1", "1_0", "ORG", "Fonatur", 88, 95, "ambos"),
            ent("Q3", "1_0", "ORG", "Fonatur", 88, 95, "ambos")]
    fila = celda(evaluar_ie(tmp_path, gold, pred), metodo="combinado", tipo="TODOS")
    assert (fila["tp"], fila["predichas"]) == (1, 1)


def test_ie_pasaje_fuera_del_gold_se_ignora_y_gold_sin_entidades_no_penaliza(tmp_path):
    # `3_0` es un pasaje gold sin entidades: no tiene filas en el gold, luego se ignora
    # y sus falsos positivos no cuentan (P04).
    gold = [["1_0", "ORG", "A", 0, 1]]
    pred = [ent("Q1", "1_0", "ORG", "A", 0, 1, "regla"),
            ent("Q1", "3_0", "ORG", "SEP", 0, 3, "regla")]
    fila = celda(evaluar_ie(tmp_path, gold, pred), metodo="regla", tipo="TODOS")
    assert (fila["tp"], fila["predichas"], fila["gold"]) == (1, 1, 1)


def test_ie_tipo_fuera_del_catalogo_tiene_fila_propia_y_cuenta_en_todos(tmp_path):
    gold = [["1_0", "ORG", "A", 0, 1]]
    pred = [ent("Q1", "1_0", "ORG", "A", 0, 1, "regla"), ent("Q1", "1_0", "XYZ", "z", 4, 5, "regla")]
    res = evaluar_ie(tmp_path, gold, pred)
    xyz = celda(res, metodo="regla", tipo="XYZ")
    assert (xyz["predichas"], xyz["gold"]) == (1, 0)
    assert celda(res, metodo="regla", tipo="TODOS")["predichas"] == 2


def test_ie_archivos_vacios_no_revientan(tmp_path):
    g_vacio = tmp_path / "gv.csv"
    e_vacio = tmp_path / "ev.csv"
    escribir_csv(g_vacio, [], COLS_GOLD)
    escribir_csv(e_vacio, [], COLS_ENTIDADES)
    g = escribir_csv(tmp_path / "g.csv", [["1_0", "ORG", "A", 0, 1]], COLS_GOLD)
    e = escribir_csv(tmp_path / "e.csv", [ent("Q1", "1_0", "ORG", "A", 0, 1, "regla")],
                     COLS_ENTIDADES)
    # Gold vacío o ambos vacíos: solo filas TODOS con ceros.
    for gold, pred in ((g_vacio, e), (g_vacio, e_vacio)):
        res = pd.read_csv(ak.ejecutar_evaluador("ie", gold, pred, tmp_path / "o1"))
        assert set(res["tipo"]) == {"TODOS"} and (res["f1"] == 0).all()
    # Predicciones vacías: una fila por tipo del gold, con ceros.
    res = pd.read_csv(ak.ejecutar_evaluador("ie", g, e_vacio, tmp_path / "o2"))
    assert celda(res, metodo="combinado", tipo="ORG")["gold"] == 1
    assert (res["f1"] == 0).all()

