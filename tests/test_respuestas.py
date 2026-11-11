"""T14 · Tablas de respuesta: exclusiones U14, contexto, reporteros, grupos de evento y contrato.

Pasajes y entidades sintéticos de formato; no son datos del corpus.
"""
from __future__ import annotations

import pandas as pd

from mtx import respuestas as r

T1 = ("PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: La pensión será de dos mil 550 pesos bimestrales. "
      "Eso ya lo saben todos ustedes desde hace tiempo. "
      "Pemex invirtió 300 millones de pesos en otra cosa. Nada más.")
T2 = "REPORTERO: ¿Es cierto que serán dos mil 550 pesos bimestrales? Gracias."


def pasaje(texto, doc="1", reportero=False, interv="1-1", t0=0, t1=50):
    return r.Pasaje(texto, doc, "2020-01-01", texto.split(":")[0], reportero, interv, t0, t1)


def cand(pid, texto, sub, tipo="MONTO", valor=None):
    i = texto.index(sub)
    return {"query_id": "Q7", "passage_id": pid, "tipo": tipo, "texto": sub, "inicio": i,
            "fin": i + len(sub), "valor": valor or sub, "clave": r.plano(valor or sub)}


CAMPO = {"campo": "montos_bimestrales", "tipo": "MONTO", "relacion": "monto bimestral",
         "patrones_contexto": ["bimestr"], "unidad_respuesta": "bimestral"}


def test_exclusiones_marca_y_lista_solo_per():
    ents = pd.DataFrame([
        {"query_id": "Q1", "tipo": "PER", "texto_normalizado": "andres manuel lopez obrador",
         "en_marca": True},
        {"query_id": "Q1", "tipo": "PER", "texto_normalizado": "andres manuel lopez obrador",
         "en_marca": False},
        {"query_id": "Q1", "tipo": "ORG", "texto_normalizado": "andres manuel lopez obrador",
         "en_marca": False},
        {"query_id": "Q1", "tipo": "PER", "texto_normalizado": "rocio nahle", "en_marca": False}])
    f, c = r.excluir(ents, ["Andrés Manuel López Obrador"])
    assert list(f["tipo"]) == ["ORG", "PER"]
    assert c.set_index("motivo")["n"].to_dict() == {"en_marca": 1, "lista_excluir": 1}


def test_patron_de_contexto_decide_el_estado():
    p = {"a": pasaje(T1)}
    c = pd.DataFrame([cand("a", T1, "dos mil 550 pesos"), cand("a", T1, "300 millones de pesos")])
    filas, _ = r.responder_campo("Q7", CAMPO, c, p, ventana=20)
    est = {f["valor"]: f["estado"] for f in filas}
    assert est == {"dos mil 550 pesos": "respaldado_en_texto", "300 millones de pesos": "ambiguo"}
    for f in filas:
        assert T1[f["evidencia_inicio"]:f["evidencia_fin"]] == f["cita"]


def test_reportero_no_se_atribuye_ni_se_respalda():
    p = {"b": pasaje(T2, reportero=True)}
    filas, _ = r.responder_campo("Q7", CAMPO, pd.DataFrame([cand("b", T2, "dos mil 550 pesos")]),
                                 p, 60)
    assert filas[0]["estado"] == "ambiguo"
    assert filas[0]["relacion"].startswith("pregunta de reportero")
    assert filas[0]["interlocutor"] == "REPORTERO"


def test_ventanas_solapadas_de_una_intervencion_son_un_evento():
    p = {"a": pasaje(T1, t0=0, t1=40), "a2": pasaje(T1, t0=30, t1=70),
         "c": pasaje(T1, doc="2", interv="2-1")}
    c = pd.DataFrame([cand(pid, T1, "dos mil 550 pesos") for pid in ("a", "a2", "c")])
    filas, frec = r.responder_campo("Q7", CAMPO, c, p, 60)
    assert len(filas) == 2  # a y a2 se deduplican
    assert len({f["grupo_evento"] for f in filas}) == 2
    assert frec.iloc[0]["n_discursos"] == 2 and frec.iloc[0]["n_menciones"] == 3


def test_unico_marca_contradictorio_sin_eliminar():
    t = "Recibirán cinco mil pesos al mes. Mejor dicho, seis mil pesos al mes por sembrador."
    campo = {**CAMPO, "unico": True, "patrones_contexto": ["al mes"]}
    c = pd.DataFrame([cand("a", t, "cinco mil pesos"), cand("a", t, "seis mil pesos")])
    filas, _ = r.responder_campo("Q5", campo, c, {"a": pasaje(t)}, 60)
    assert [f["estado"] for f in filas] == ["contradictorio", "contradictorio"]
    assert len({f["grupo_evento"] for f in filas}) == 1


def test_no_encontrado_y_contrato():
    filas, _ = r.responder_campo("Q7", CAMPO, pd.DataFrame(), {}, 60)
    df = pd.DataFrame(filas, columns=r.COLUMNAS)
    assert df["estado"].tolist() == ["no_encontrado"]
    assert r.validar_respuestas(df, {}) == []
    malo = df.assign(estado="inventado")
    assert r.validar_respuestas(malo, {})


def test_valoraciones_faltantes_o_desactualizadas():
    hashes = {"Q1": "abc", "Q2": "def"}
    val = {"Q1": {"texto": "Escrito por el alumno.", "tabla_sha256": "abc"},
           "Q2": {"texto": "Escrito por el alumno.", "tabla_sha256": "viejo"}}
    assert r.validar_valoraciones(val, hashes) == ["Q2: la valoración no corresponde a la tabla vigente"]
    assert len(r.validar_valoraciones({}, hashes)) == 2
    assert "[VALIDAR]" in r.bloque_valoracion(None, "abc")
    assert "invalidada" in r.bloque_valoracion(val["Q2"], "def")
