"""Muestra gold (T09) y almacén/validador del gold (T10), con datos sintéticos y rutas temporales."""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from mtx import gold, muestreo
from mtx.app import componentes

PROTOCOLO = frozenset({"buenos", "días", "gracias", "saludos"})
CUERPO = " ".join(f"palabra{i} contenido{i}" for i in range(20))  # 40 palabras de contenido


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _universo(n_consultas=10, compartidos=0, textos_especiales=None):
    """Top-10 sintético; los primeros `compartidos` pasajes de Q1 aparecen también en Q2."""
    filas, pas = [], {}
    for q in range(1, n_consultas + 1):
        for r in range(1, 11):
            pid = f"{q}_{r}"
            if q == 2 and r <= compartidos:
                pid = f"1_{r}"
            filas.append({"query_id": f"Q{q}", "passage_id": pid, "doc_id": pid.split("_")[0],
                          "rango": r})
            pas.setdefault(pid, f"MARCA: {pid} {CUERPO}")
    for pid, t in (textos_especiales or {}).items():
        pas[pid] = t
    pasajes = pd.DataFrame({"passage_id": list(pas), "texto": list(pas.values()),
                            "inicio_cuerpo": [len("MARCA: ")] * len(pas),
                            "texto_sha256": [_sha(t) for t in pas.values()]})
    return pd.DataFrame(filas), pasajes


# --------------------------------------------------------------------------- T09


def test_misma_semilla_mismo_manifiesto_y_20_unicos():
    top, pas = _universo()
    a = muestreo.sortear_gold(top, pas, PROTOCOLO)
    b = muestreo.sortear_gold(top, pas, PROTOCOLO)
    pd.testing.assert_frame_equal(a.muestra, b.muestra)
    assert list(a.muestra.columns) == muestreo.COLUMNAS_MUESTRA
    assert a.muestra["passage_id"].nunique() == 20
    assert (a.muestra.groupby("query_id").size() == 2).all()
    assert set(a.muestra["semilla"]) == {42}


def test_una_plaza_alta_y_una_baja_por_consulta():
    top, pas = _universo()
    det = muestreo.sortear_gold(top, pas, PROTOCOLO).detalle
    for _, g in det.groupby("query_id"):
        rangos = dict(zip(g["plaza"], g["rango"], strict=True))
        assert 1 <= rangos["alto"] <= 5 and 6 <= rangos["bajo"] <= 10


def test_otra_semilla_cambia_el_sorteo():
    top, pas = _universo()
    a = muestreo.sortear_gold(top, pas, PROTOCOLO, semilla=42).muestra
    b = muestreo.sortear_gold(top, pas, PROTOCOLO, semilla=7).muestra
    assert list(a["passage_id"]) != list(b["passage_id"])


def test_colisiones_entre_consultas_sin_duplicar():
    # Q2 comparte con Q1 sus 8 primeros pasajes: el emparejamiento debe repartirlos.
    top, pas = _universo(compartidos=8)
    m = muestreo.sortear_gold(top, pas, PROTOCOLO).muestra
    assert m["passage_id"].nunique() == 20


def test_caso_imposible_reporta_consultas_en_conflicto():
    # Q1 y Q2 con exactamente los mismos tres pasajes, todos de rango alto: 4 plazas, 3 pasajes.
    filas = [{"query_id": q, "passage_id": f"x_{r}", "doc_id": "x", "rango": r}
             for q in ("Q1", "Q2") for r in (1, 2, 3)]
    pas = pd.DataFrame({"passage_id": [f"x_{r}" for r in (1, 2, 3)],
                        "texto": [f"M: {CUERPO}"] * 3, "inicio_cuerpo": [3] * 3,
                        "texto_sha256": ["h"] * 3})
    with pytest.raises(muestreo.MuestraInviable) as e:
        muestreo.sortear_gold(pd.DataFrame(filas), pas, PROTOCOLO)
    assert set(e.value.conflictos) <= {"Q1", "Q2"} and e.value.conflictos


def test_sustitucion_objetiva_por_corto_y_por_protocolo():
    especiales = {f"{q}_{r}": "MARCA: muy corto" for q in range(1, 11) for r in (1, 2, 3)}
    especiales.update({f"{q}_{r}": "MARCA: " + " ".join(["buenos días gracias saludos"] * 8)
                       for q in range(1, 11) for r in (6, 7)})
    top, pas = _universo(textos_especiales=especiales)
    res = muestreo.sortear_gold(top, pas, PROTOCOLO)
    elegidos = set(res.muestra["passage_id"])
    assert not elegidos & set(especiales)
    if len(res.sustituciones):
        assert set(res.sustituciones["passage_retirado"]) <= set(especiales)


def test_motivo_sustitucion_cifras():
    assert "palabras de contenido" in muestreo.motivo_sustitucion("M: hola", 3, PROTOCOLO)
    texto = "M: " + " ".join(["gracias"] * 30)
    assert "protocolo" in muestreo.motivo_sustitucion(texto, 3, PROTOCOLO)
    texto = "M: " + " ".join(["buenos días saludos"] * 20 + [CUERPO])
    assert "protocolo" in muestreo.motivo_sustitucion(texto, 3, PROTOCOLO)
    assert muestreo.motivo_sustitucion(f"M: {CUERPO}", 3, PROTOCOLO) is None
    # La marca de interlocutor no cuenta como contenido.
    assert muestreo.motivo_sustitucion(f"{CUERPO}: hola", len(CUERPO) + 2, PROTOCOLO)


def test_protocolo_real_se_carga():
    p = muestreo.cargar_protocolo()
    assert {"gracias", "buenos", "saludos"} <= p and all(x == x.lower() for x in p)


# --------------------------------------------------------------------------- búsqueda y tokens


def test_buscar_ocurrencias_todas_con_contexto():
    texto = "Pemex dijo que Pemex y Pemex"
    occ = gold.buscar_ocurrencias(texto, "Pemex", contexto=5)
    assert [(o.inicio, o.fin) for o in occ] == [(0, 5), (15, 20), (23, 28)]
    assert occ[1].antes == " que " and occ[1].despues == " y Pe"
    assert gold.buscar_ocurrencias(texto, "") == []


def test_span_de_tokens_recorta_puntuacion_y_conserva_pesos():
    texto = "costó $1,200 millones. Y (Pemex), dijo"
    toks = gold.tokens(texto)
    i = next(k for k, t in enumerate(toks) if t[2] == "$1,200")
    ini, fin = gold.span_de_tokens(texto, toks, i, i + 1)
    assert texto[ini:fin] == "$1,200 millones"
    k = next(k for k, t in enumerate(toks) if t[2] == "(Pemex),")
    ini, fin = gold.span_de_tokens(texto, toks, k, k)
    assert texto[ini:fin] == "Pemex"
    ini, fin = gold.span_de_tokens(texto, toks, k, k, recortar=False)
    assert texto[ini:fin] == "(Pemex),"


# --------------------------------------------------------------------------- almacén y validador


@pytest.fixture
def entorno(tmp_path):
    top, pas = _universo()
    res = muestreo.sortear_gold(top, pas, PROTOCOLO)
    textos = dict(zip(pas["passage_id"], pas["texto"], strict=True))
    ruta_muestra = tmp_path / "muestra_gold.csv"
    res.muestra.to_csv(ruta_muestra, index=False)
    rutas = {"ruta_gold": tmp_path / "gold_entidades.csv",
             "ruta_estado": tmp_path / "estado_gold.csv"}
    alm = gold.AlmacenGold(res.muestra, textos, ruta_cierre=tmp_path / "cierre_gold.json",
                           **rutas)
    return alm, res.muestra, textos, rutas, tmp_path, ruta_muestra


def _span(texto, sub):
    i = texto.index(sub)
    return i, i + len(sub)


def test_agregar_valida_invariante_duplicado_y_anidamiento(entorno):
    alm, muestra, textos, *_ = entorno
    pid = muestra["passage_id"].iloc[0]
    t = textos[pid]
    i, f = _span(t, "palabra3 contenido3")
    alm.agregar(pid, "ORG", i, f)
    assert alm.entidades(pid)[0]["texto"] == "palabra3 contenido3"
    with pytest.raises(ValueError, match="Duplicado"):
        alm.agregar(pid, "ORG", i, f)
    with pytest.raises(ValueError, match="Anidada"):
        alm.agregar(pid, "PER", i, i + len("palabra3"))
    with pytest.raises(ValueError, match="Tipo inválido"):
        alm.agregar(pid, "MISC", *_span(t, "palabra5"))
    with pytest.raises(ValueError, match="fuera"):
        alm.agregar(pid, "LOC", len(t) - 1, len(t) + 3)


def test_guardado_atomico_con_revision_y_conflicto(entorno):
    alm, muestra, textos, rutas, *_ = entorno
    pid = muestra["passage_id"].iloc[0]
    alm.agregar(pid, "LOC", *_span(textos[pid], "palabra1"))
    otra = gold.AlmacenGold(muestra, textos, ruta_cierre=alm.ruta_cierre, **rutas)
    otra.agregar(pid, "LOC", *_span(textos[pid], "palabra2"))
    with pytest.raises(componentes.ConflictoRevision):
        alm.agregar(pid, "LOC", *_span(textos[pid], "palabra4"))
    alm.cargar()
    assert len(alm.entidades(pid)) == 2
    assert pd.read_csv(rutas["ruta_estado"], dtype=str).set_index("passage_id").at[
        pid, "n_entidades"] == "2"


def test_borrar_y_reabrir(entorno):
    alm, muestra, textos, *_ = entorno
    pid = muestra["passage_id"].iloc[0]
    i, f = _span(textos[pid], "palabra1")
    alm.agregar(pid, "LOC", i, f)
    alm.cerrar_pasaje(pid)
    assert alm.estado(pid) == "cerrado"
    alm.borrar(pid, "LOC", i, f)
    assert alm.entidades(pid) == [] and alm.estado(pid) == "en_progreso"


def test_t10_cierre_valido_con_pasaje_vacio_y_bloqueo_posterior(entorno):
    alm, muestra, textos, rutas, _tmp, ruta_muestra = entorno
    ids = list(muestra["passage_id"])
    for pid in ids[1:]:
        alm.agregar(pid, "PER", *_span(textos[pid], "palabra0"))
    for pid in ids:
        alm.cerrar_pasaje(pid)  # ids[0] se cierra con cero entidades
    errores, avisos = gold.validar_gold(muestra, textos, comprobar_git=False, **rutas)
    assert errores == [] and any("cero entidades" in a for a in avisos)
    cierre = gold.cerrar_gold(muestra, textos, ruta_cierre=alm.ruta_cierre,
                              ruta_muestra=ruta_muestra, comprobar_git=False, **rutas)
    assert json.loads(alm.ruta_cierre.read_text(encoding="utf-8"))["sha256_gold"] == cierre[
        "sha256_gold"]
    with pytest.raises(PermissionError):
        alm.agregar(ids[0], "ORG", *_span(textos[ids[0]], "palabra9"))


def test_validar_detecta_pendientes_offsets_y_hash(entorno):
    alm, muestra, textos, rutas, *_ = entorno
    pid = muestra["passage_id"].iloc[0]
    alm.agregar(pid, "PER", *_span(textos[pid], "palabra0"))
    errores, _ = gold.validar_gold(muestra, textos, comprobar_git=False, **rutas)
    assert any("sin cerrar" in e for e in errores)
    df = pd.read_csv(rutas["ruta_gold"], dtype={"passage_id": str})
    df.loc[0, "inicio"] = int(df.loc[0, "inicio"]) + 1
    df.to_csv(rutas["ruta_gold"], index=False)
    textos_mod = {**textos, muestra["passage_id"].iloc[1]: "cambiado"}
    errores, _ = gold.validar_gold(muestra, textos_mod, comprobar_git=False, **rutas)
    assert any("offsets rotos" in e for e in errores)
    assert any("hash" in e for e in errores)


def test_no_cierra_si_hay_errores(entorno):
    alm, muestra, textos, rutas, _tmp, ruta_muestra = entorno
    with pytest.raises(ValueError, match="No se puede cerrar"):
        gold.cerrar_gold(muestra, textos, ruta_cierre=alm.ruta_cierre, ruta_muestra=ruta_muestra,
                         comprobar_git=False, **rutas)
    assert not alm.ruta_cierre.exists()
