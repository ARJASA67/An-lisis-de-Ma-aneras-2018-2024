"""T11 · Reglas de extracción: FECHA, MONTO, auxiliares, gazetteers, marca y colisiones.

Los ejemplos son sintéticos (PRD §6.7.10) y no son anotaciones del corpus. Un caso que falla se
conserva con `xfail(strict=True)` y razón; no se borra del parametrize.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from mtx import config, reglas
from mtx.reglas import Entidad


def textos(tipo, texto, inicio_cuerpo=0, gaz=None):
    return [e.texto for e in reglas.extraer_reglas(texto, inicio_cuerpo, gaz) if e.tipo == tipo]


# ------------------------------------------------------------------ FECHA (PRD §6.7.1)
FECHA_POS = [
    ("el 15 de diciembre de 2023 fue", "15 de diciembre de 2023"),
    ("el primero de enero de 2020 salió", "primero de enero de 2020"),
    ("el 1 de septiembre del 2021 hubo", "1 de septiembre del 2021"),
    ("desde enero de 2021 hasta hoy", "enero de 2021"),
    ("fue en diciembre del 2019 cuando", "diciembre del 2019"),
    ("el 15/12/2023 se firmó", "15/12/2023"),
    ("el 1/1/19 llegó", "1/1/19"),
    ("el próximo 15 de enero iremos", "próximo 15 de enero"),
    ("el pasado 20 de noviembre fue", "pasado 20 de noviembre"),
    ("este 1 de julio habrá", "este 1 de julio"),
    ("en diciembre de 2021 empezó", "diciembre de 2021"),
    ("pasó en 2019 y luego", "2019"),
    ("ocurrió el año 2019 con", "2019"),
    ("trabajamos desde 2019 en", "2019"),
    ("del 1 al 15 de enero de 2021 se hará", "1 al 15 de enero de 2021"),
]
FECHA_NEG = ["15 personas llegaron", "página 15 del libro", "duró 2 horas", "15 de los 32 estados",
             "15 de cada 100 casos", "el folio 2019 se emitió", "costó en 2000 pesos"]


@pytest.mark.parametrize("texto,esperado", FECHA_POS)
def test_fecha_positivos_con_span_exacto(texto, esperado):
    assert textos("FECHA", texto) == [esperado]


@pytest.mark.parametrize("texto", FECHA_NEG)
def test_fecha_negativos(texto):
    assert textos("FECHA", texto) == []


def test_fecha_enumeracion_son_entidades_separadas():
    assert textos("FECHA", "el 3 de mayo de 2020 y el 5 de junio de 2021") == [
        "3 de mayo de 2020", "5 de junio de 2021"]


@pytest.mark.parametrize("texto,iso,precision,estado", [
    ("15 de diciembre de 2023", "2023-12-15", "dia", "ok"),
    ("primero de enero de 2020", "2020-01-01", "dia", "ok"),
    ("diciembre del 2019", "2019-12", "mes", "ok"),
    ("2019", "2019", "anio", "ok"),
    ("15/12/2023", "2023-12-15", "dia", "ok"),
    ("1/1/19", "2019-01-01", "dia", "ok"),
    ("1/1/55", "", "dia", "anio_ambiguo"),
    ("15 de enero", "", "dia", "parcial"),
    ("29 de febrero de 2020", "2020-02-29", "dia", "ok"),
    ("29 de febrero de 2021", "", "dia", "invalida"),
    ("31 de febrero de 2021", "", "dia", "invalida"),
])
def test_analizar_fecha(texto, iso, precision, estado):
    a = reglas.analizar_fecha(texto)
    assert (a["fecha_iso"], a["precision"], a["estado"]) == (iso, precision, estado)


def test_31_de_febrero_se_detecta_pero_no_se_resuelve():
    assert textos("FECHA", "se dijo el 31 de febrero de 2021 que") == ["31 de febrero de 2021"]
    assert reglas.analizar_fecha("31 de febrero de 2021")["estado"] == "invalida"


def test_intervalo_y_modificador_relativo():
    a = reglas.analizar_fecha("1 al 15 de enero de 2021")
    assert (a["precision"], a["fecha_inicio"], a["fecha_fin"], a["fecha_iso"]) == (
        "intervalo", "2021-01-01", "2021-01-15", "")
    assert reglas.analizar_fecha("próximo 15 de enero")["modificador"] == "proximo"


@pytest.mark.xfail(strict=True, reason="PRD §6.7.1: fechas completamente en palabras no cubiertas")
def test_fecha_en_palabras_no_cubierta():
    assert textos("FECHA", "el quince de enero llegó") == ["quince de enero"]


@pytest.mark.xfail(strict=True, reason="PRD §6.7.1: 'de 2019 a 2024' emite dos años, no un intervalo")
def test_rango_de_anios_no_es_intervalo():
    assert textos("FECHA", "de 2019 a 2024 hubo") == ["2019 a 2024"]


# ------------------------------------------------------------------ MONTO (PRD §6.7.2)
MONTO_POS = [
    "20 mil millones de pesos", "2 mil 500 millones de pesos", "1,200 millones de pesos",
    "$1,200 millones", "$ 5 mil", "5 mil pesos", "500 pesos", "2 mil millones de dólares",
    "100 millones de dólares", "1.5 billones de pesos", "6 mil 300 pesos", "mil 200 pesos",
    "un millón de pesos", "dos mil millones de pesos",
]
MONTO_NEG = ["20 mil personas", "15 millones de dosis", "3 millones de árboles", "20 por ciento",
             "20%", "página 20"]


@pytest.mark.parametrize("monto", MONTO_POS)
def test_monto_positivos_span_completo(monto):
    assert textos("MONTO", f"se invirtieron {monto} en total") == [monto]


@pytest.mark.parametrize("neg", MONTO_NEG)
def test_monto_negativos(neg):
    assert textos("MONTO", f"hubo {neg} en total") == []


def test_monto_no_empieza_a_mitad_de_cifra():
    assert textos("MONTO", "pagó 1500 pesos ayer") == ["1500 pesos"]


def test_monto_conserva_el_signo_de_pesos():
    assert textos("MONTO", "son $1,200 millones") == ["$1,200 millones"]


# ------------------------------------------------------------------ auxiliares (D11)
def test_porcentajes_y_cantidades_son_auxiliares_no_entidades():
    t = "El 20% y 3.5 por ciento; 15 millones de dosis y 100 mil litros; 200 mil sembradores"
    assert all(e.tipo in reglas.TIPOS for e in reglas.extraer_reglas(t, 0))
    assert textos("MONTO", t) == []
    aux = {a["texto"]: a for a in reglas.extraer_auxiliares(t)}
    assert aux["20%"]["tipo_aux"] == "PORCENTAJE" and aux["20%"]["valor_num"] == Decimal(20)
    assert aux["3.5 por ciento"]["valor_num"] == Decimal("3.5")
    assert aux["3.5 por ciento"]["unidad"] == "porcentaje"
    d = aux["15 millones de dosis"]
    assert (d["tipo_aux"], d["valor_num"], d["unidad"]) == ("CANTIDAD", Decimal(15000000), "dosis")
    assert aux["100 mil litros"]["valor_num"] == Decimal(100000)
    assert aux["200 mil sembradores"]["unidad"] == "sembradores"


def test_auxiliares_no_incluyen_montos_y_respetan_offsets():
    t = "gastó 500 pesos y repartió 30 mil elementos en 10 sucursales"
    aux = reglas.extraer_auxiliares(t)
    assert [a["texto"] for a in aux] == ["30 mil elementos", "10 sucursales"]
    assert all(t[a["inicio"]:a["fin"]] == a["texto"] for a in aux)


@pytest.mark.parametrize("expr,valor", [
    ("20 mil millones", Decimal(20000000000)), ("2 mil 500 millones", Decimal(2500000000)),
    ("mil 200", Decimal(1200)), ("1,200 millones", Decimal(1200000000)),
    ("un millón", Decimal(1000000)), ("dos mil millones", Decimal(2000000000)),
    ("1.5 billones", Decimal(1500000000000)), ("6 mil 300", Decimal(6300)),
])
def test_valor_de_cifras_habladas(expr, valor):
    assert reglas.valor_cifra(expr) == valor


# ------------------------------------------------------------------ gazetteer
@pytest.fixture(scope="module")
def gaz():
    return reglas.cargar_gazetteer()


def test_gazetteer_entradas_obligatorias(gaz):
    obligatorias = ["IMSS", "ISSSTE", "Pemex", "CFE", "Sedena", "Semar", "Conagua", "Fonatur",
                    "Insabi", "Cofepris", "Birmex", "Pfizer", "AstraZeneca", "CanSino", "Sputnik V",
                    "COVAX", "Coparmex", "CCE", "Concanaco", "Conasami", "Morena", "PAN", "PRI",
                    "PRD", "ONU", "OMS", "OPS", "FMI", "Banco Mundial", "Banxico", "SAT",
                    "Guardia Nacional", "Secretaría del Bienestar", "STPS", "SICT", "Sener",
                    "Sedatu", "Grupo Carso", "ICA"]
    faltan = [o for o in obligatorias if o not in gaz.terminos("ORG")]
    assert faltan == []


def test_d14_farmaceuticas_son_org(gaz):
    for nombre in ["Pfizer", "BioNTech", "AstraZeneca", "CanSino", "Sputnik V", "Gamaleya",
                   "Sinovac", "Moderna", "Janssen", "Johnson & Johnson", "Abdala", "Patria", "COVAX"]:
        assert nombre in gaz.terminos("ORG"), nombre


def test_loc_32_entidades_y_obras(gaz):
    locs = gaz.terminos("LOC")
    assert len(gaz.estados) == 32
    for n in ["Ciudad de México", "CDMX", "Estado de México", "Edomex", "Michoacán de Ocampo",
              "Veracruz de Ignacio de la Llave", "Coahuila de Zaragoza", "Palenque", "Cancún",
              "Tren Maya", "Dos Bocas", "refinería Olmeca", "AIFA", "Tren Interoceánico",
              "Corredor Interoceánico", "Estados Unidos", "Washington", "Cuba",
              "Istmo de Tehuantepec"]:
        assert n in locs, n


@pytest.mark.parametrize("texto,tipo,esperado", [
    ("anunció el IMSS que", "ORG", "IMSS"),
    ("con Pemex y la CFE", "ORG", "Pemex"),
    ("la Secretaría de Salud informó", "ORG", "Secretaría de Salud"),
    ("vacunas de Pfizer y Sputnik V llegaron", "ORG", "Pfizer"),
    ("el Tren Maya avanza", "LOC", "Tren Maya"),
    ("en Ciudad de México hubo", "LOC", "Ciudad de México"),
    ("la refinería de Dos Bocas, Tabasco", "LOC", "Dos Bocas"),
])
def test_gazetteer_positivos(texto, tipo, esperado):
    assert esperado in textos(tipo, texto)


def test_secretaria_de_salud_de_tabasco_es_una_sola_org():
    t = "informó la Secretaría de Salud de Tabasco ayer"
    assert textos("ORG", t) == ["Secretaría de Salud de Tabasco"]
    assert "Tabasco" not in textos("LOC", t)


def test_longest_match_dentro_del_gazetteer():
    t = "el Aeropuerto Internacional Felipe Ángeles abrió"
    assert textos("LOC", t) == ["Aeropuerto Internacional Felipe Ángeles"]


def test_siglas_cortas_son_sensibles_a_mayusculas():
    assert textos("ORG", "comimos pan y sat en la mesa") == []
    assert textos("ORG", "el PAN y el SAT opinaron") == ["PAN", "SAT"]


def test_palabras_comunes_no_se_marcan_en_minusculas():
    assert textos("ORG", "la patria y la morena del cuadro") == []
    assert textos("ORG", "la vacuna Patria llegó") == ["Patria"]


def test_limites_de_palabra_respetan_acentos():
    assert textos("LOC", "Cuba") == ["Cuba"]
    assert textos("LOC", "cubáno y Cubana de aviación") == []
    assert textos("ORG", "el IMSSé y PANes") == []


def test_gazetteer_acepta_texto_en_mayusculas():
    assert "TREN MAYA" in textos("LOC", "EL TREN MAYA AVANZA")


# ------------------------------------------------------------------ marca de interlocutor
def marca(label, cuerpo="Buenos días a todos y a todas."):
    texto = f"{label}: {cuerpo}"
    return [(e.tipo, e.texto, e.fuente, e.en_marca) for e in reglas.extraer_reglas(texto, len(label) + 2)
            if e.en_marca]


def test_marca_con_coma_toma_lo_que_sigue_a_la_ultima_coma():
    assert ("PER", "JORGE ALCOCER VARELA", "marca", True) in marca(
        "SECRETARIO DE SALUD, JORGE ALCOCER VARELA")


def test_marca_con_cargo_conocido_quita_el_cargo():
    assert ("PER", "ANDRÉS MANUEL LÓPEZ OBRADOR", "marca", True) in marca(
        "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR")


def test_marca_sin_coma_que_coincide_con_gazetteer_es_org():
    ents = marca("PEMEX")
    assert any(t == "ORG" and s == "PEMEX" for t, s, *_ in ents)


@pytest.mark.parametrize("label", ["PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA", "REPORTERA"])
def test_marcas_genericas_sin_entidad(label):
    assert marca(label) == []


def test_marca_no_supone_que_todo_tras_la_coma_es_persona():
    assert marca("DIRECTOR GENERAL, DE LA OFICINA CENTRAL DE ADMINISTRACION GENERAL") == []


def test_marca_nombre_coma_cargo_no_toma_el_cargo_como_persona():
    # Formato real del corpus: «NOMBRE, CARGO». Solo el nombre es PER.
    pers = [t for tipo, t, *_ in marca("RICARDO SHEFFIELD PADILLA, PROCURADOR FEDERAL DEL CONSUMIDOR")
            if tipo == "PER"]
    assert pers == ["RICARDO SHEFFIELD PADILLA"]
    pers = [t for tipo, t, *_ in marca("ZOÉ ROBLEDO ABURTO, DIRECTOR GENERAL DEL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS)")
            if tipo == "PER"]
    assert pers == ["ZOÉ ROBLEDO ABURTO"]


def test_marca_solo_nombre_sin_cargo_es_per():
    assert ("PER", "JESÚS RAMÍREZ CUEVAS", "marca", True) in marca("JESÚS RAMÍREZ CUEVAS")
    assert ("PER", "HUGO LÓPEZ-GATELL RAMÍREZ", "marca", True) in marca("HUGO LÓPEZ-GATELL RAMÍREZ")


def test_entidades_de_marca_cumplen_el_invariante():
    texto = "SECRETARIO DE SALUD, JORGE ALCOCER VARELA: Hoy en Tabasco hubo 5 mil pesos."
    for e in reglas.extraer_reglas(texto, texto.index("Hoy")):
        assert texto[e.inicio:e.fin] == e.texto and 0 <= e.inicio < e.fin <= len(texto)


# ------------------------------------------------------------------ colisiones
def test_gana_el_span_mas_largo_y_se_registra():
    t = "la Secretaría de Salud de Tabasco informó"
    ents, cols = reglas.extraer_reglas_con_colisiones(t, 0)
    assert [e.texto for e in ents if e.tipo == "ORG"] == ["Secretaría de Salud de Tabasco"]
    assert any(c["fuente_suprimida"] == "gazetteer_loc" and c["texto_suprimido"] == "Tabasco"
               for c in cols)


def test_empate_de_longitud_se_resuelve_por_jerarquia():
    cands = [Entidad("ORG", "XX", 0, 2, fuente="gazetteer_org"),
             Entidad("LOC", "XX", 0, 2, fuente="gazetteer_loc"),
             Entidad("FECHA", "XX", 0, 2, fuente="regex_fecha")]
    ganadoras, cols = reglas.resolver_colisiones(cands)
    assert [e.fuente for e in ganadoras] == ["regex_fecha"]
    assert {c["fuente_suprimida"] for c in cols} == {"gazetteer_org", "gazetteer_loc"}
    cands = [Entidad("ORG", "XX", 0, 2, fuente="gazetteer_org"),
             Entidad("LOC", "XX", 0, 2, fuente="gazetteer_loc")]
    assert [e.fuente for e in reglas.resolver_colisiones(cands)[0]] == ["gazetteer_loc"]


def test_sin_solape_no_hay_colision():
    ents, cols = reglas.extraer_reglas_con_colisiones("el IMSS y Pemex en 2019", 0)
    assert cols == [] and {e.texto for e in ents} >= {"IMSS", "Pemex", "2019"}


# ------------------------------------------------------------------ invariante en pasajes reales
@pytest.mark.skipif(not config.PASAJES_PARQUET.exists(), reason="falta data/pasajes.parquet")
def test_invariante_de_offsets_en_200_pasajes_reales():
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["texto", "inicio_cuerpo"]).sample(
        200, random_state=config.SEMILLA)
    n = 0
    for texto, ic in zip(p["texto"], p["inicio_cuerpo"], strict=True):
        for e in reglas.extraer_reglas(texto, int(ic)):
            assert texto[e.inicio:e.fin] == e.texto and 0 <= e.inicio < e.fin <= len(texto)
            assert e.tipo in reglas.TIPOS and e.texto == e.texto.strip()
            n += 1
    assert n > 0


# ------------------------------------------------------------------ minado de siglas
def test_minar_siglas_excluye_conocidas_romanos_y_marca():
    p = pd.DataFrame({
        "texto": (["PRESIDENTE JUAN PEREZ: el INAI y el IMSS opinan en el siglo XIX sobre el INAI"] * 6),
        "inicio_cuerpo": [len("PRESIDENTE JUAN PEREZ: ")] * 6})
    s = reglas.minar_siglas(p, min_frecuencia=5)
    assert list(s["sigla"]) == ["INAI"]  # IMSS ya está en el gazetteer; XIX es romano
    assert s.loc[0, "frecuencia"] == 6 and "INAI" in s.loc[0, "ejemplo"]


def test_minar_siglas_toma_nombre_propuesto_del_patron():
    t = "la Comisión Nacional de los Derechos Humanos (CNDH) emitió"
    p = pd.DataFrame({"texto": [t] * 5, "inicio_cuerpo": [0] * 5})
    s = reglas.minar_siglas(p, min_frecuencia=5)
    assert s.loc[0, "nombre_propuesto"] == "Comisión Nacional de los Derechos Humanos"
