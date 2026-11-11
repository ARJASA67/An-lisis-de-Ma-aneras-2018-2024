"""Fusión reglas + modelo (PRD §6.9, D12, D16, T08, T13). Fixtures sintéticos."""
from __future__ import annotations

import pandas as pd

from mtx import fusion

TEXTO = "PRESIDENTE: Fonatur y Pemex en Dos Bocas, Tabasco, con Rocío Nahle."
IC = len("PRESIDENTE: ")


def _e(tipo, sub, fuente=None, conf=None, desde=0):
    i = TEXTO.index(sub, desde)
    d = {"tipo": tipo, "texto": sub, "inicio": i, "fin": i + len(sub)}
    if fuente is not None:
        d.update(fuente=fuente, en_marca=i < IC)
    if conf is not None:
        d["confianza"] = conf
    return d


def test_t13_exacta_parcial_y_tipo_distinto():
    reglas = [_e("ORG", "Fonatur", "gazetteer_org"), _e("LOC", "Dos Bocas", "gazetteer_loc"),
              _e("ORG", "Pemex", "gazetteer_org")]
    modelo = [_e("ORG", "Fonatur", conf=0.9), _e("LOC", "Dos Bocas, Tabasco", conf=0.8),
              _e("LOC", "Pemex", conf=0.7), _e("PER", "Rocío Nahle", conf=0.99)]
    filas, solapes = fusion.fusionar_pasaje("1_1", reglas, modelo, IC)
    por = {(f.tipo, f.texto): f for f in filas}
    assert por[("ORG", "Fonatur")].metodo == "ambos"
    assert por[("ORG", "Fonatur")].fuentes == "gazetteer_org|modelo"
    assert por[("ORG", "Fonatur")].puntaje_modelo == 0.9
    assert por[("LOC", "Dos Bocas")].metodo == "regla"
    assert por[("LOC", "Dos Bocas, Tabasco")].metodo == "modelo"
    assert por[("ORG", "Pemex")].metodo == "regla" and por[("LOC", "Pemex")].metodo == "modelo"
    assert por[("PER", "Rocío Nahle")].metodo == "modelo"
    assert len(filas) == 6
    clases = sorted(s["clase"] for s in solapes)
    assert clases == ["solape_parcial", "tipo_distinto"]
    parcial = next(s for s in solapes if s["clase"] == "solape_parcial")
    assert parcial["longitud_solape"] == len("Dos Bocas")


def test_en_marca_para_entidades_del_modelo():
    filas, _ = fusion.fusionar_pasaje("1_1", [], [_e("PER", "PRESIDENTE", conf=0.5)], IC)
    assert filas[0].en_marca


def test_t08_pasaje_compartido_y_orden_determinista():
    filas, _ = fusion.fusionar_pasaje("5_2", [_e("ORG", "Pemex", "gazetteer_org")],
                                      [_e("LOC", "Tabasco", conf=0.9)], IC)
    uni = pd.DataFrame([{"passage_id": "5_2", **vars(f)} for f in filas])
    ambito = pd.DataFrame({"query_id": ["Q3", "Q1", "Q10"], "passage_id": ["5_2", "5_2", "7_1"],
                           "doc_id": ["5", "5", "7"]})
    df = fusion.a_consultas(uni, ambito)[fusion.COLUMNAS_ENTIDADES]
    assert list(df["query_id"]) == ["Q1", "Q1", "Q3", "Q3"]
    assert (df[df["query_id"] == "Q1"].drop(columns="query_id").reset_index(drop=True)
            .equals(df[df["query_id"] == "Q3"].drop(columns="query_id").reset_index(drop=True)))
    otra = fusion.a_consultas(uni, ambito)[fusion.COLUMNAS_ENTIDADES]
    assert df.to_csv(index=False) == otra.to_csv(index=False)


def test_contrato_entidades():
    filas, _ = fusion.fusionar_pasaje("1_1", [_e("ORG", "Pemex", "gazetteer_org")], [], IC)
    uni = pd.DataFrame([{"passage_id": "1_1", **vars(f)} for f in filas])
    ambito = pd.DataFrame({"query_id": ["Q1"], "passage_id": ["1_1"], "doc_id": ["1"]})
    df = fusion.a_consultas(uni, ambito)[fusion.COLUMNAS_ENTIDADES]
    assert fusion.validar_entidades(df, {"1_1": TEXTO}) == []
    malo = df.assign(metodo="combinado")
    assert any("Métodos" in e for e in fusion.validar_entidades(malo, {"1_1": TEXTO}))
    dup = pd.concat([df, df])
    assert any("duplicada" in e for e in fusion.validar_entidades(dup, {"1_1": TEXTO}))
    roto = df.assign(inicio=df["inicio"] + 1)
    assert any("Offsets" in e for e in fusion.validar_entidades(roto, {"1_1": TEXTO}))
    extra = df.assign(fuentes="x")
    assert fusion.validar_entidades(extra, {"1_1": TEXTO})[0].startswith("Columnas")
