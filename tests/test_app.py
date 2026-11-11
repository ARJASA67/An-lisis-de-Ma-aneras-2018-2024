"""T15 · Persistencia atómica, dos pestañas, reanudación, resaltado y modo ciego de la app.

Los juicios de estas pruebas son valores de formato en `tmp_path`; nada se escribe en
`anotaciones/` y el asistente no juzga nada.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from mtx import pool
from mtx.app import componentes as c

PL = pd.DataFrame({
    "query_id": ["Q1", "Q1", "Q1", "Q2"], "passage_id": ["1_0", "1_1", "2_0", "1_0"],
    "doc_id": [1, 1, 2, 1], "fecha": ["2020-01-01"] * 4, "texto": ["t"] * 4,
    "texto_sha256": ["h"] * 4})


@pytest.fixture
def criterios(tmp_path):
    ruta = tmp_path / "criterios.md"
    ruta.write_text("Relevancia temática.", encoding="utf-8")
    return ruta


def almacen(tmp_path, criterios):
    return c.AlmacenJuicios(PL, ruta=tmp_path / "juicios.csv", ruta_criterios=criterios,
                            hash_pool="abc")


# ------------------------------------------------------------------ gate de criterios
def test_sin_criterios_no_se_registra(tmp_path):
    a = c.AlmacenJuicios(PL, ruta=tmp_path / "j.csv", ruta_criterios=tmp_path / "no.md")
    with pytest.raises(PermissionError):
        a.registrar("Q1", "1_0", "1")
    assert not (tmp_path / "j.csv").exists()


def test_criterios_vacios_no_cuentan(tmp_path):
    (tmp_path / "c.md").write_text("  \n", encoding="utf-8")
    assert not c.criterios_listos(tmp_path / "c.md")


# ------------------------------------------------------------------ persistencia
def test_registrar_escribe_formato_exacto_sin_bom(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    crudo = (tmp_path / "juicios.csv").read_bytes()
    assert not crudo.startswith(b"\xef\xbb\xbf")
    assert crudo.decode().splitlines() == ["query_id,doc_id,passage_id,relevante", "Q1,1,1_0,1"]
    assert a.revision == 1


def test_omitido_se_guarda_vacio_y_no_es_cero(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "")
    assert a.estado("Q1", "1_0") == ""
    assert a.progreso("Q1") == (0, 3)
    assert (tmp_path / "juicios.csv").read_text().splitlines()[1] == "Q1,1,1_0,"


def test_cambiar_un_juicio_actualiza_la_fila_y_respalda(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    a.registrar("Q1", "1_0", "0")
    assert len(a.df) == 1 and a.estado("Q1", "1_0") == "0"
    resp = tmp_path / "respaldo" / "juicios.r00001.csv"
    assert resp.exists() and "Q1,1,1_0,1" in resp.read_text()


def test_mismo_pasaje_en_dos_consultas_es_independiente(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    assert a.estado("Q2", "1_0") is None


def test_par_fuera_del_pool_o_valor_invalido(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    with pytest.raises(ValueError, match="pool"):
        a.registrar("Q1", "9_9", "1")
    with pytest.raises(ValueError, match="inválido"):
        a.registrar("Q1", "1_0", "2")


def test_reanudacion_conserva_conteo_y_primer_pendiente(tmp_path, criterios):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    a.registrar("Q1", "1_1", "")
    b = almacen(tmp_path, criterios)  # sesión nueva
    assert b.progreso("Q1") == (1, 3) and b.revision == 2
    orden = ["1_0", "1_1", "2_0"]
    assert c.primer_pendiente(orden, lambda p: b.estado("Q1", p)) == 1  # el omitido sigue pendiente


# ------------------------------------------------------------------ dos pestañas
def test_segunda_sesion_desfasada_se_rechaza(tmp_path, criterios):
    a, b = almacen(tmp_path, criterios), almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    antes = (tmp_path / "juicios.csv").read_bytes()
    with pytest.raises(c.ConflictoRevision, match="otra pestaña"):
        b.registrar("Q1", "1_1", "0")
    assert (tmp_path / "juicios.csv").read_bytes() == antes
    b.cargar()
    b.registrar("Q1", "1_1", "0")
    assert b.progreso("Q1") == (2, 3)


# ------------------------------------------------------------------ interrupción
def test_interrupcion_antes_del_replace_deja_el_original_intacto(tmp_path, criterios, monkeypatch):
    a = almacen(tmp_path, criterios)
    a.registrar("Q1", "1_0", "1")
    original = (tmp_path / "juicios.csv").read_bytes()

    def falla(*args, **kw):
        raise OSError("corte simulado")

    monkeypatch.setattr(os, "replace", falla)
    with pytest.raises(OSError):
        a.registrar("Q1", "1_1", "0")
    monkeypatch.undo()
    assert (tmp_path / "juicios.csv").read_bytes() == original
    assert list(tmp_path.glob(".*.tmp")) == []  # el temporal se limpia
    assert (tmp_path / "respaldo" / "juicios.r00001.csv").read_bytes() == original
    assert a.revision == 1 or c.leer_meta(tmp_path / "juicios.csv")["revision"] == 1


def test_pool_hash_queda_en_la_meta(tmp_path, criterios):
    almacen(tmp_path, criterios).registrar("Q1", "1_0", "1")
    assert c.leer_meta(tmp_path / "juicios.csv")["pool_sha256"] == "abc"


# ------------------------------------------------------------------ siguiente pendiente
def test_siguiente_pendiente_circular_y_unico():
    estados = {"a": "1", "b": None, "c": "0", "d": ""}
    est = estados.get
    orden = ["a", "b", "c", "d"]
    assert c.siguiente_pendiente(orden, est, 1) == 3  # salta el actual y el 0
    assert c.siguiente_pendiente(orden, est, 3) == 1  # circular
    estados["d"] = "1"
    assert c.siguiente_pendiente(orden, est, 1) == 1  # único pendiente: él mismo
    assert c.siguiente_pendiente(orden, est, 1, saltar_actual=False) == 1
    estados["b"] = "0"
    assert c.siguiente_pendiente(orden, est, 1) is None


# ------------------------------------------------------------------ resaltado
def test_resaltado_escapa_html_y_conserva_offsets():
    texto = "𝐀 <b>& cosa</b> huachicol fin"
    ini = texto.index("huachicol")
    out = c.resaltar_html(texto, [(ini, ini + 9, "termino")])
    assert "&lt;b&gt;&amp; cosa&lt;/b&gt;" in out and "<b>" not in out
    assert '<mark class="termino">huachicol</mark>' in out
    assert texto[ini:ini + 9] == "huachicol"  # índices de carácter, no UTF-16


def test_resaltado_rechaza_solape_y_fuera_de_rango():
    with pytest.raises(ValueError, match="solapados"):
        c.resaltar_html("abcdef", [(0, 3, "x"), (2, 4, "y")])
    with pytest.raises(ValueError, match="fuera"):
        c.resaltar_html("abc", [(0, 9, "x")])


def test_resaltado_sin_replace_no_duplica_apariciones():
    texto = "gas y más gas"
    out = c.resaltar_html(texto, [(0, 3, "termino")])
    assert out.count("<mark") == 1


def test_spans_terminos_por_raiz_sobre_texto_completo():
    texto = "MARCA tren: El tren maya avanza; trenes nuevos <x>"
    ini = len("MARCA tren: ")
    spans = c.spans_terminos(texto, "construcción del Tren Maya", ini)
    palabras = [texto[a:b] for a, b, _ in spans]
    assert {"tren", "trenes", "maya"} <= set(palabras)
    assert all(a >= ini for a, _, _ in spans)  # la marca no se busca
    assert all(texto[a:b] != "MARCA" for a, b, _ in spans)


def test_html_pasaje_marca_en_gris_la_marca():
    out = c.html_pasaje("PRESIDENTE: el tren avanza", "tren", 12)
    assert '<mark class="marca">PRESIDENTE: </mark>' in out
    assert '<mark class="termino">tren</mark>' in out


# ------------------------------------------------------------------ modo ciego
def test_pool_ciego_no_expone_procedencia(tmp_path):
    pl = pd.DataFrame({**{k: PL[k] for k in PL.columns}, "en_ventana": True,
                       "variantes": "bm25_con_filtro", "mejor_rango_tfidf": 1,
                       "mejor_rango_bm25": 2})
    pl.to_csv(tmp_path / "p.csv", index=False)
    visto = c.cargar_pool_ciego(tmp_path / "p.csv")
    assert list(visto.columns) == c.COLUMNAS_PUBLICAS_POOL
    assert not {"variantes", "mejor_rango_tfidf", "mejor_rango_bm25", "en_ventana"} & set(visto)


def test_gold_cerrado_depende_solo_del_cierre(tmp_path):
    assert not c.gold_cerrado(tmp_path / "cierre_gold.json")
    (tmp_path / "cierre_gold.json").write_text("{}")
    assert c.gold_cerrado(tmp_path / "cierre_gold.json")


# ------------------------------------------------------------------ estado
def test_estado_nunca_completado_por_existir(tmp_path, monkeypatch):
    """Con pool real y sin juicios: criterios y juicios pendientes humanos, pool válido."""
    if not pool.POOL_CSV.exists():
        pytest.skip("falta salida/04_pool.csv")
    monkeypatch.setattr(c, "CRITERIOS_RELEVANCIA", tmp_path / "no.md")
    monkeypatch.setattr(pool, "JUICIOS_CSV", tmp_path / "no_juicios.csv")
    est = {f.nombre: f for f in c.estado_artefactos()}
    assert est["Criterios de relevancia"].estado == "pendiente humano"
    assert est["Juicios de relevancia"].estado == "pendiente humano"
    assert est["Pool de relevancia"].estado in {"válido", "obsoleto"}
    assert all(f.estado in c.ESTADOS for f in est.values())
    assert est["Cierre del gold"].estado != "válido"


# ------------------------------------------------------------------ app de punta a punta (AppTest)
def _app(tmp_path, monkeypatch, con_criterios=True):
    from streamlit.testing.v1 import AppTest
    if con_criterios:
        (tmp_path / "c.md").write_text("Relevancia temática.", encoding="utf-8")
    monkeypatch.setattr(c, "CRITERIOS_RELEVANCIA", tmp_path / "c.md")
    monkeypatch.setattr(pool, "JUICIOS_CSV", tmp_path / "anot" / "juicios.csv")
    ruta = pool.POOL_CSV.parents[1] / "src" / "mtx" / "app" / "app.py"
    return AppTest.from_file(str(ruta), default_timeout=120)


@pytest.mark.skipif(not pool.POOL_CSV.exists(), reason="falta salida/04_pool.csv")
def test_app_sin_criterios_no_ofrece_botones_de_juicio(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch, con_criterios=False).run()
    assert not at.exception
    etiquetas = {b.label for b in at.button}
    assert "Actualizar" in etiquetas
    assert not etiquetas & {"Relevante (1)", "No relevante (0)", "Omitir por ahora", "Anterior"}


@pytest.mark.skipif(not pool.POOL_CSV.exists(), reason="falta salida/04_pool.csv")
def test_app_flujo_1_0_omitir_anterior_y_ciego(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    assert not at.exception
    texto_pagina = " ".join(m.value for m in at.markdown)
    for prohibido in ("tfidf", "bm25", "mejor_rango", "variante"):
        assert prohibido not in texto_pagina.lower()

    def boton(etiqueta):
        return next(b for b in at.button if b.label == etiqueta)

    destino = tmp_path / "anot" / "juicios.csv"
    boton("Relevante (1)").click().run()
    boton("Omitir por ahora").click().run()
    boton("No relevante (0)").click().run()
    boton("Anterior").click().run()
    assert not at.exception
    filas = destino.read_text(encoding="utf-8").splitlines()
    assert filas[0] == "query_id,doc_id,passage_id,relevante"
    valores = [f.rsplit(",", 1)[1] for f in filas[1:]]
    assert valores == ["1", "", "0"]  # omitido queda vacío, nunca 0
    assert c.leer_meta(destino)["revision"] == 3
