"""T10 · Evaluación de IE: detalle contra el kit, complementaria de 20 IDs (P04) y errores.

Las entidades de estas pruebas son datos sintéticos de formato; no son anotaciones del gold.
"""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import evaluacion as ev

TEXTO_A = "PRESIDENTE JUAN PÉREZ: La Refinería Dos Bocas y el IMSS costaron 300 millones de pesos."
TEXTO_B = "Nada que anotar aquí."


def gold_df(filas):
    return pd.DataFrame(filas, columns=["passage_id", "tipo", "texto", "inicio", "fin"])


def pred_df(filas):
    cols = ["passage_id", "tipo", "texto", "inicio", "fin", "metodo", "fuentes"]
    return pd.DataFrame(filas, columns=cols)


def span(texto, sub, desde=0):
    i = texto.index(sub, desde)
    return i, i + len(sub)


def pasajes():
    return pd.DataFrame({"passage_id": ["1_0", "2_0"], "texto": [TEXTO_A, TEXTO_B],
                         "inicio_cuerpo": [TEXTO_A.index(":") + 2, 0]})


def g(tipo, sub, pid="1_0"):
    return (pid, tipo, sub, *span(TEXTO_A, sub))


def p(tipo, sub, metodo="modelo", fuentes="modelo", pid="1_0", texto=TEXTO_A):
    return (pid, tipo, sub, *span(texto, sub), metodo, fuentes)


# ------------------------------------------------------------------ métricas
def test_detalle_reproduce_al_kit(tmp_path):
    gold = gold_df([g("PER", "JUAN PÉREZ"), g("ORG", "IMSS"), g("LOC", "Refinería Dos Bocas")])
    pred = pred_df([p("PER", "JUAN PÉREZ", "ambos", "marca|modelo"),
                    p("ORG", "IMSS", "regla", "gazetteer_org"),
                    p("LOC", "Dos Bocas")])
    pred.insert(0, "query_id", "Q1")
    pred.insert(1, "doc_id", "1")
    gold.to_csv(tmp_path / "gold.csv", index=False)
    pred.drop(columns="fuentes").to_csv(tmp_path / "ent.csv", index=False)
    kit = ev.evaluar_ie_oficial(tmp_path / "gold.csv", tmp_path / "ent.csv", tmp_path / "out")
    det = ev.evaluar_ie(gold, pred).set_index(["metodo", "tipo"])
    for f in kit.itertuples(index=False):
        d = det.loc[(f.metodo, f.tipo)]
        assert (d["tp"], d["predichas"], d["soporte"]) == (f.tp, f.predichas, f.gold)
        if d["estado"] == "ok":
            assert d["f1"] == pytest.approx(f.f1)


def test_estados_no_aplicable_y_sin_cobertura():
    gold = gold_df([g("PER", "JUAN PÉREZ")])
    det = ev.evaluar_ie(gold, pred_df([])).set_index(["metodo", "tipo"])
    assert det.loc[("modelo", "MONTO"), "estado"] == "sin_cobertura"
    assert det.loc[("regla", "MONTO"), "estado"] == "no_aplicable"
    assert pd.isna(det.loc[("regla", "MONTO"), "f1"])
    assert det.loc[("regla", "PER"), "f1"] == 0.0


def test_complementaria_cuenta_fp_en_pasaje_vacio():
    gold = gold_df([g("PER", "JUAN PÉREZ")])
    pred = pred_df([p("PER", "JUAN PÉREZ"), p("LOC", "Nada", pid="2_0", texto=TEXTO_B)])
    kit = ev.evaluar_ie(gold, pred).set_index(["metodo", "tipo"])
    comp = ev.evaluar_ie(gold, pred, ["1_0", "2_0"]).set_index(["metodo", "tipo"])
    assert kit.loc[("combinado", "TODOS"), "fp"] == 0
    assert comp.loc[("combinado", "TODOS"), "fp"] == 1
    assert comp.attrs["pasajes_evaluados"] == 2


def test_duplicados_entre_consultas_cuentan_una_vez():
    gold = gold_df([g("ORG", "IMSS")])
    pred = pred_df([p("ORG", "IMSS"), p("ORG", "IMSS")])
    det = ev.evaluar_ie(gold, pred).set_index(["metodo", "tipo"])
    assert det.loc[("combinado", "TODOS"), "predichas"] == 1


def test_alertas():
    res = pd.DataFrame([{"metodo": "combinado", "tipo": "TODOS", "f1": 0.2, "gold": 50},
                        {"metodo": "regla", "tipo": "LOC", "f1": 1.0, "gold": 6},
                        {"metodo": "regla", "tipo": "MONTO", "f1": 1.0, "gold": 5}])
    a = ev.alertas_ie(res)
    assert len(a) == 2 and "0.2000" in a[0] and "LOC" in a[1]


# ------------------------------------------------------------------ errores
def cats(err):
    return set(zip(err["texto_gold"].fillna(""), err["texto_pred"].fillna(""), err["categoria"]))


def test_categorias_de_error():
    gold = gold_df([g("PER", "JUAN PÉREZ"), g("LOC", "Refinería Dos Bocas"), g("ORG", "IMSS"),
                    g("MONTO", "300 millones de pesos")])
    pred = pred_df([p("PER", "JUAN"), p("LOC", "Refinería"), p("LOC", "Dos Bocas"),
                    p("MONTO", "300 millones", "regla", "regex_monto"),
                    p("LOC", "costaron", "regla", "gazetteer_loc")])
    err = ev.analizar_errores(gold, pred, pasajes())
    c = cats(err)
    assert ("JUAN PÉREZ", "JUAN (PER)", "frontera") in c
    assert ("JUAN PÉREZ", "JUAN (PER)", "en_marca") in c
    assert ("Refinería Dos Bocas", "Refinería (LOC) | Dos Bocas (LOC)",
            "frontera:entidad_partida") in c
    assert ("300 millones de pesos", "300 millones (MONTO)", "frontera:monto_sin_unidad") in c
    assert ("IMSS", "", "sigla_no_reconocida") in c and ("IMSS", "", "omision") in c
    esp = err[err["categoria"] == "espuria"]
    assert list(esp["texto_pred"]) == ["costaron"] and list(esp["fuente"]) == ["gazetteer"]
    assert list(err.columns) == ev.COLUMNAS_ERRORES


def test_anidadas_no_son_entidad_partida():
    gold = gold_df([g("LOC", "Refinería Dos Bocas")])
    pred = pred_df([p("LOC", "Dos Bocas"), p("LOC", "Bocas")])
    err = ev.analizar_errores(gold, pred, pasajes())
    assert "frontera:entidad_partida" not in set(err["categoria"])


def test_tipo_y_obra_en_ambos_lados():
    gold = gold_df([g("LOC", "Refinería Dos Bocas")])
    pred = pred_df([p("ORG", "Refinería Dos Bocas")])
    err = ev.analizar_errores(gold, pred, pasajes(), {"Refinería Dos Bocas"})
    assert {"tipo", "tipo:obra_LOC_vs_ORG"} <= set(err["categoria"])
    # Lado predicción: el gold ya se acertó y sobra una predicción del mismo span con otro tipo.
    pred2 = pred_df([p("LOC", "Refinería Dos Bocas", "regla", "gazetteer_loc"),
                     p("ORG", "Refinería Dos Bocas")])
    err2 = ev.analizar_errores(gold, pred2, pasajes(), {"Refinería Dos Bocas"})
    assert set(err2["categoria"]) == {"tipo", "tipo:obra_LOC_vs_ORG"}
    assert set(err2["inicio"]) == {span(TEXTO_A, "Refinería Dos Bocas")[0]}


def test_aciertos_no_generan_errores_y_resumen():
    gold = gold_df([g("ORG", "IMSS")])
    assert ev.analizar_errores(gold, pred_df([p("ORG", "IMSS")]), pasajes()).empty
    err = ev.analizar_errores(gold, pred_df([p("LOC", "costaron", "regla", "gazetteer_loc")]),
                              pasajes())
    res = ev.resumen_errores(err)
    assert set(res["categoria"]) == {"omision", "sigla_no_reconocida", "espuria"}
    assert res.loc[res["categoria"] == "omision", "metodo"].item() == "ninguno"
    assert res.loc[res["categoria"] == "espuria", "fuente"].item() == "gazetteer"
