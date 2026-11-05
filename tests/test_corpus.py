"""T02 · Limpieza, canonización de marcas y segmentación (PRD §6.1). Sin red, texto sintético."""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import config, corpus


@pytest.fixture(scope="module")
def cfg():
    return config.cargar_yaml("limpieza.yaml")


@pytest.fixture(scope="module")
def rx(cfg):
    return corpus._compilar(cfg)


def limpio(texto, rx):
    return corpus.limpiar_texto(texto, rx)[0]


# --------------------------------------------------------------------------- marcas


def test_marca_tilde_se_canoniza_a_una_linea_por_intervencion(rx):
    t = "~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR Buenos días. ~~~PREGUNTA Gracias, presidente."
    assert limpio(t, rx) == ("\nPRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: Buenos días."
                             "\nPREGUNTA: Gracias, presidente.")


def test_etiqueta_pegada_al_texto_y_interlocutor_vs_interlocutora(rx):
    t = "~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADORIgualmente. ~~~INTERLOCUTOR Sí. ~~~INTERLOCUTORA No."
    assert partir_etiquetas(limpio(t, rx)) == [
        "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", "INTERLOCUTOR", "INTERLOCUTORA"]


def partir_etiquetas(canonico):
    return [q for q, _ in corpus.partir_canonico(canonico)]


def test_marca_en_linea_con_cargo(rx):
    t = ("~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR Adelante. SECRETARIO, JORGE ALCOCER VARELA, "
         "SECRETARIO DE SALUD: Con su permiso.")
    pares = corpus.partir_canonico(limpio(t, rx))
    assert pares[-1] == ("SECRETARIO, JORGE ALCOCER VARELA, SECRETARIO DE SALUD", "Con su permiso.")
    assert pares[0][1] == "Adelante."


def test_etiqueta_en_linea_larga_que_el_kit_no_reconoce(rx):
    quien = ("JESÚS RAMÍREZ CUEVAS, COORDINADOR GENERAL DE COMUNICACIÓN SOCIAL Y VOCERO "
             "DE PRESIDENCIA")
    assert len(quien) > 81  # el kit solo admite etiquetas de hasta 81 caracteres
    pares = corpus.partir_canonico(limpio(f"Hola. {quien}: Es del Inegi.", rx))
    assert pares == [("", "Hola."), (quien, "Es del Inegi.")]


def test_corte_de_oracion_previa_en_mayusculas(rx):
    t = "~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR A ver, el IMSS. ZOÉ ROBLEDO ABURTO: Perdón."
    pares = corpus.partir_canonico(limpio(t, rx))
    assert pares[0][1] == "A ver, el IMSS."
    assert pares[1] == ("ZOÉ ROBLEDO ABURTO", "Perdón.")


def test_abreviatura_titulo_no_corta_la_etiqueta(rx):
    pares = corpus.partir_canonico(limpio("Sigue. DR. LUIS PÉREZ GÓMEZ: Buenos días.", rx))
    assert pares[-1][0] == "DR. LUIS PÉREZ GÓMEZ"


def test_una_palabra_en_mayusculas_no_es_marca_salvo_lista(rx):
    assert partir_etiquetas(limpio("Ojo. NOTA: esto sigue igual.", rx)) == [""]
    assert partir_etiquetas(limpio("Dice. INTERVENCIÓN: Sí.", rx)) == ["", "INTERVENCIÓN"]


def test_etiqueta_con_parentesis_desbalanceados_se_rechaza(rx):
    assert partir_etiquetas(limpio("Canta. EN TU DÍA ENTREGA TOTAL) (LOS ALBATROS INTERPRETAN: x", rx)) == [""]


def test_no_quedan_tildes_ni_espacios_duros(rx):
    t = limpio("~~~PREGUNTA Hola  mundo ~~~INTERLOCUTORA Sí", rx)
    assert "~" not in t and " " not in t and "  " not in t


# --------------------------------------------------------------------------- limpieza


def test_acotaciones_se_borran_pero_las_siglas_en_parentesis_se_conservan(rx):
    t = "~~~PREGUNTA El IMSS (IMSS) aquí (inaudible) y (FINALIZA VIDEO) también (Inaudible) fin"
    out, info = corpus.limpiar_texto(t, rx)
    assert "(IMSS)" in out
    assert "inaudible" not in out.lower() and "VIDEO" not in out
    assert info["conteos"]["acotaciones"] == 3
    assert info["tipos_acotacion"]["inaudible"] == 2


def test_lema_anual_se_elimina(rx):
    t = ("~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR2022: Año de Ricardo Flores Magón, precursor "
         "de la Revolución Mexicana Buenos días.")
    out, info = corpus.limpiar_texto(t, rx)
    assert out == "\nPRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: Buenos días."
    assert info["conteos"]["lemas"] == 1


def test_saltos_crlf_y_lf_originales_son_espacios(rx):
    assert limpio("~~~PREGUNTA uno\r\ndos\ntres", rx) == "\nPREGUNTA: uno dos tres"


def test_acentos_y_nfc(rx):
    descompuesto = "~~~PREGUNTA cámara"  # "á" descompuesta
    assert limpio(descompuesto, rx) == "\nPREGUNTA: cámara"


def test_conteo_de_caracteres_descartados(rx):
    _, info = corpus.limpiar_texto("~~~PREGUNTA a (inaudible) b", rx)
    assert info["conteos"]["caracteres_descartados"] == len("(inaudible)")


# --------------------------------------------------------------------------- partir_canonico


def test_partir_canonico_sin_marcas_y_con_prefacio():
    assert corpus.partir_canonico("solo texto") == [("", "solo texto")]
    assert corpus.partir_canonico("pre\nA B: uno\nC D: dos") == [
        ("", "pre"), ("A B", "uno"), ("C D", "dos")]
    assert corpus.partir_canonico("\nA B:") == [("A B", "")]
    assert corpus.partir_canonico("") == []


# --------------------------------------------------------------------------- fechas

RANGO = (pd.Timestamp("2018-12-01"), pd.Timestamp("2024-09-30"))


def test_candidata_titulo_ignora_anos_absurdos():
    assert corpus.candidata_titulo("03.03.30 Versión estenográfica", RANGO) is None
    assert corpus.candidata_titulo("28.96.24 Versión", RANGO) is None  # mes inválido
    assert corpus.candidata_titulo("20.01.2024 Versión", RANGO) == pd.Timestamp("2024-01-20")
    assert corpus.candidata_titulo("Discurso del presidente", RANGO) is None


def test_candidata_url():
    assert corpus.candidata_url("https://x/30-09-24-version/", RANGO) == pd.Timestamp("2024-09-30")
    assert corpus.candidata_url("https://x/2021/05/06/algo", RANGO) == pd.Timestamp("2021-05-06")
    assert corpus.candidata_url("https://x/sin-fecha", RANGO) is None


def reparar(fecha, titulo, url=""):
    return corpus.reparar_fecha(fecha, titulo, url, RANGO, 3)


def test_error_tipografico_en_titulo_no_sustituye_fecha_correcta():
    r = reparar(pd.Timestamp("2020-03-03"), "03.03.30 Versión", "https://x/03-03-20-v/")
    assert r["fecha"] == pd.Timestamp("2020-03-03") and r["fecha_fuente"] == "original"


def test_fecha_con_ano_equivocado_se_corrige_con_el_titulo():
    r = reparar(pd.Timestamp("2020-01-20"), "20.01.2024 Versión")
    assert r["fecha"] == pd.Timestamp("2024-01-20")
    assert (r["fecha_fuente"], r["motivo"]) == ("titulo", "fecha_difiere_de_la_candidata")


def test_diferencia_dentro_de_tolerancia_conserva_la_original():
    r = reparar(pd.Timestamp("2019-06-11"), "11.06.19 Versión", "https://x/10-06-19-v/")
    assert r["fecha"] == pd.Timestamp("2019-06-11") and r["fecha_fuente"] == "original"


def test_fecha_ausente_usa_la_candidata_y_sin_candidata_no_inventa():
    assert reparar(pd.NaT, "05.05.21 Versión")["fecha"] == pd.Timestamp("2021-05-05")
    r = reparar(pd.NaT, "Discurso sin fecha")
    assert pd.isna(r["fecha"]) and r["fecha_fuente"] == "ninguna"


def test_titulo_y_url_contradictorios_se_senalan_sin_corregir():
    r = reparar(pd.Timestamp("2021-01-01"), "05.05.21 Versión", "https://x/20-08-21-v/")
    assert r["fecha"] == pd.Timestamp("2021-01-01")
    assert r["motivo"] == "titulo_y_url_se_contradicen"


# --------------------------------------------------------------------------- duplicados


def tabla_dup(textos, fechas):
    return pd.DataFrame({
        "doc_id": range(len(textos)), "fecha": pd.to_datetime(fechas),
        "titulo": ["t"] * len(textos), "texto_norm": [corpus.normalizar_para_hash(t) for t in textos]})


def test_duplicado_exacto_conserva_el_menor_doc_id(cfg):
    base = "uno dos tres cuatro cinco seis siete ocho"
    d = corpus.detectar_duplicados(tabla_dup([base, "otra cosa distinta " * 3, base.upper()],
                                             ["2020-01-01"] * 3), cfg)
    assert d[["doc_id_excluido", "doc_id_conservado", "tipo"]].values.tolist() == [[2, 0, "exacto"]]


def test_casi_duplicado_solo_con_la_misma_fecha(cfg):
    a = " ".join(f"p{i}" for i in range(200))
    b = a + " extra final"
    mismo = corpus.detectar_duplicados(tabla_dup([a, b], ["2020-01-01"] * 2), cfg)
    otro = corpus.detectar_duplicados(tabla_dup([a, b], ["2020-01-01", "2020-01-02"]), cfg)
    assert mismo["tipo"].tolist() == ["casi_duplicado"] and mismo["similitud"].iloc[0] >= 0.9
    assert otro.empty


def test_reversion_manual_evita_la_exclusion(cfg):
    cfg2 = {**cfg, "duplicados": {**cfg["duplicados"], "reversiones": [1]}}
    d = corpus.detectar_duplicados(tabla_dup(["igual texto aqui"] * 2, ["2020-01-01"] * 2), cfg2)
    assert d.empty


# --------------------------------------------------------------------------- segmentación


def discurso(doc_id, canonico, excluido=False, fecha="2020-01-01"):
    return {"doc_id": doc_id, "fecha": pd.Timestamp(fecha), "fecha_original": pd.Timestamp(fecha),
            "fecha_fuente": "original", "titulo": f"T{doc_id}", "url": f"u{doc_id}",
            "texto_canonico": canonico, "excluido": excluido}


def palabras(prefijo, n):
    return " ".join(f"{prefijo}{i}" for i in range(n))


def segmentar_demo(filas, **kw):
    return corpus.segmentar_con_descartes(pd.DataFrame(filas), **kw)


def test_invariantes_de_marca_reinyectada():
    c = f"\nPRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: {palabras('a', 60)}\nPREGUNTA: {palabras('b', 50)}"
    p, _ = segmentar_demo([discurso(7, c)])
    assert p["passage_id"].tolist() == ["7_0", "7_1"]
    for r in p.itertuples():
        assert r.texto[:r.inicio_cuerpo] == f"{r.interlocutor}: "
        assert r.marca_reinyectada and r.n_palabras == len(r.texto.split())
    assert p["es_reportero"].tolist() == [False, True]


def test_texto_sin_marcas_no_reinyecta():
    p, _ = segmentar_demo([discurso(1, palabras("w", 80))])
    assert p["inicio_cuerpo"].tolist() == [0] and p["interlocutor"].tolist() == [""]
    assert not p["marca_reinyectada"].iloc[0] and p["texto"].iloc[0] == palabras("w", 80)


def test_posicion_solo_avanza_con_pasajes_conservados():
    c = f"\nA B: {palabras('x', 60)}\nC D: corto\nE F: {palabras('y', 60)}"
    p, d = segmentar_demo([discurso(3, c)])
    assert p["passage_id"].tolist() == ["3_0", "3_1"]
    assert d["interlocutor"].tolist() == ["C D"] and d["n_palabras"].tolist() == [1]


def test_ventanas_largas_traslapan_y_cubren_todo_el_texto():
    n = 430
    toks = [f"t{i}" for i in range(n)]
    p, d = segmentar_demo([discurso(2, f"\nA B: {' '.join(toks)}")])
    assert d.empty
    cuerpos = [r.texto[r.inicio_cuerpo:].split() for r in p.itertuples()]
    assert [r.token_inicio for r in p.itertuples()] == [0, 150, 300]
    cubierto = set()
    for r, c in zip(p.itertuples(), cuerpos, strict=True):
        assert c == toks[r.token_inicio:r.token_fin]
        cubierto.update(range(r.token_inicio, r.token_fin))
    assert cubierto == set(range(n))  # sin pérdida de contenido (T02)
    assert len(set(p["intervencion_id"])) == 1


def test_discursos_excluidos_no_generan_pasajes():
    p, _ = segmentar_demo([discurso(0, f"\nA B: {palabras('a', 60)}", excluido=True),
                           discurso(1, f"\nA B: {palabras('b', 60)}")])
    assert set(p["doc_id"]) == {1}


def test_es_reportero_conjunto_cerrado(cfg):
    assert all(corpus.es_reportero(x, cfg) for x in ("PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA",
                                                     "PREGUNTA 2"))
    assert not corpus.es_reportero("INTERVENCIÓN", cfg)
    assert not corpus.es_reportero("PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", cfg)


def test_ids_reconstruyen_doc_y_posicion():
    c = "".join(f"\nQ {i}: {palabras('w', 60)}" for i in range(5))
    p, _ = segmentar_demo([discurso(12, c)])
    for r in p.itertuples():
        assert r.passage_id == f"{r.doc_id}_{r.posicion}"
    assert p["posicion"].tolist() == list(range(5))


def test_determinismo_y_hash_independiente_del_orden():
    c = "".join(f"\nQ {i}: {palabras('w', 70)}" for i in range(4))
    filas = [discurso(1, c), discurso(2, c)]
    p1, _ = segmentar_demo(filas)
    p2, _ = segmentar_demo(list(reversed(filas)))
    assert corpus.hash_pasajes(p1) == corpus.hash_pasajes(p2)
    assert corpus.hash_pasajes(p1) != corpus.hash_pasajes(p1.iloc[:-1])


def test_columnas_exactas_y_orden():
    p, _ = segmentar_demo([discurso(0, f"\nA B: {palabras('a', 60)}")])
    assert list(p.columns) == corpus.COLUMNAS_PASAJES


def test_pipeline_completo_sobre_un_discurso_sintetico(cfg):
    texto = ("~~~PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR " + palabras("a", 50) +
             " (inaudible) " + "~~~PREGUNTA " + palabras("b", 45) + " JESÚS RAMÍREZ CUEVAS: " +
             palabras("c", 45))
    df = pd.DataFrame({"doc_id": [0], "url": ["https://x/01-02-21-v/"],
                       "titulo": ["01.02.21 Versión"], "fecha": pd.to_datetime(["2021-02-01"]),
                       "texto": [texto]})
    lim, inf = corpus.limpiar_ruido(df, cfg)
    assert inf["resumen"]["acotaciones_eliminadas"] == 1
    p = corpus.segmentar(lim)
    assert p["interlocutor"].tolist() == [
        "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR", "PREGUNTA", "JESÚS RAMÍREZ CUEVAS"]
    assert not p["texto"].str.contains("inaudible").any()
