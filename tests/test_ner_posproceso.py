"""Pruebas del NER con modelo (PRD §6.8, U15, T12), rápidas y sin red.

El pipeline de Hugging Face se sustituye por un doble: un tokenizador por palabras con offsets y
un "modelo" que etiqueta palabras de un diccionario. Los textos son sintéticos y no son
anotaciones del corpus.
"""
from __future__ import annotations

import json
import re

import pytest

from mtx import ner_modelo as nm

CFG = {
    "version_posproceso": "1",
    "fragmentacion": {"solapamiento": 2, "margen": 0},
    "inferencia": {"aggregation_strategy": "simple", "device": -1, "lote": 8},
    "mapa_etiquetas": {"PER": "PER", "PERSON": "PER", "ORG": "ORG", "LOC": "LOC", "GPE": "LOC"},
    "descartadas": ["MISC", "OTH"],
}
MODELO = {"slug": "doble", "repo_id": "prueba/doble", "revision": "abcdef1234567890",
          "principal": True}


class TokenizadorDoble:
    """Un subtoken por palabra o signo; `offset_mapping` exacto."""
    model_max_length = 10**30

    def __call__(self, texto, add_special_tokens=False, return_offsets_mapping=True):
        return {"offset_mapping": [m.span() for m in re.finditer(r"\w+|[^\w\s]", texto)]}

    def num_special_tokens_to_add(self, pair=False):
        return 2


class ConfigDoble:
    def __init__(self, posiciones, id2label):
        self.max_position_embeddings = posiciones
        self.model_type = "bert"
        self.id2label = id2label


class ModeloDoble:
    def __init__(self, posiciones, id2label):
        self.config = ConfigDoble(posiciones, id2label)


class PipelineDoble:
    """Etiqueta cada palabra que esté en `lexico`; agrupa palabras contiguas del mismo tipo."""

    def __init__(self, lexico: dict[str, str], posiciones: int = 12,
                 id2label: dict | None = None):
        self.lexico = lexico
        self.tokenizer = TokenizadorDoble()
        etiquetas = id2label or {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG", 4: "I-ORG",
                                 5: "B-LOC", 6: "I-LOC", 7: "B-MISC", 8: "I-MISC"}
        self.model = ModeloDoble(posiciones, etiquetas)
        self.llamadas = 0
        self.textos_vistos: list[str] = []

    def _uno(self, texto: str) -> list[dict]:
        salida = []
        for m in re.finditer(r"\w+", texto):
            etq = self.lexico.get(m.group())
            if etq:
                salida.append({"entity_group": etq, "score": 0.9, "word": m.group(),
                               "start": m.start(), "end": m.end()})
        return salida

    def __call__(self, textos, batch_size=8):
        self.llamadas += 1
        self.textos_vistos += list(textos)
        return [self._uno(t) for t in textos]


def _post(texto, crudas, **kw):
    return nm.posprocesar(texto, crudas, CFG, {"PER", "ORG", "LOC", "MISC"}, **kw)


def _c(etq, ini, fin, conf=0.9):
    return {"etiqueta": etq, "inicio": ini, "fin": fin, "confianza": conf}


# --- mapa de etiquetas ------------------------------------------------------------------------

def test_mapa_person_gpe_y_misc_descartado_y_contado():
    texto = "Ana viajó a Tabasco con Fonatur y el Tren"
    crudas = [_c("PERSON", 0, 3), _c("GPE", 12, 19), _c("B-ORG", 24, 31), _c("MISC", 37, 41)]
    ents, _, desc = nm.posprocesar(texto, crudas, CFG, {"PERSON", "GPE", "ORG", "MISC"})
    assert [(e.tipo, e.texto) for e in ents] == [("PER", "Ana"), ("LOC", "Tabasco"),
                                                  ("ORG", "Fonatur")]
    assert desc["MISC"] == 1


def test_etiqueta_que_el_modelo_no_emite_no_se_mapea():
    texto = "Ana en Tabasco"
    ents, _, desc = nm.posprocesar(texto, [_c("GPE", 7, 14)], CFG, {"PER", "LOC"})
    assert ents == [] and desc["sin_mapa:GPE"] == 1


def test_etiquetas_del_modelo_desde_id2label():
    assert nm.etiquetas_del_modelo({0: "O", 1: "B-PER", 2: "I-PER", 3: "B-OTH"}) == {"PER", "OTH"}


# --- recorte e invariante ---------------------------------------------------------------------

def test_recorte_quita_espacios_y_puntuacion_pero_conserva_pesos():
    texto = "Dijo: «Pemex», y luego $1,200 millones."
    crudas = [_c("ORG", 5, 13), _c("ORG", 22, 29)]
    ents, _, _ = _post(texto, crudas)
    assert [e.texto for e in ents] == ["Pemex", "$1,200"]
    for e in ents:
        assert texto[e.inicio:e.fin] == e.texto


def test_span_solo_de_puntuacion_se_descarta():
    ents, _, desc = _post("hola , adiós", [_c("PER", 4, 7)])
    assert ents == [] and desc["vacia_tras_recorte"] == 1


# --- uniones ----------------------------------------------------------------------------------

def test_union_intrapalabra_siempre_sin_registro():
    texto = "Andrés Manuel"
    ents, uniones, _ = _post(texto, [_c("PER", 0, 3), _c("PER", 3, 6)], unir_interpalabra=False)
    assert [e.texto for e in ents] == ["Andrés"] and uniones == []


def test_union_interpalabra_registrada_y_opcional():
    texto = "habló López Obrador hoy"
    crudas = [_c("PER", 6, 11, 0.8), _c("PER", 12, 19, 0.95)]
    ents, uniones, _ = _post(texto, crudas)
    assert [e.texto for e in ents] == ["López Obrador"] and ents[0].unida
    assert ents[0].confianza == pytest.approx(0.8)
    assert uniones == [{"tipo": "PER", "inicio_1": 6, "fin_1": 11, "inicio_2": 12, "fin_2": 19,
                        "inicio_union": 6, "fin_union": 19, "texto_union": "López Obrador",
                        "confianza_1": 0.8, "confianza_2": 0.95}]
    sin, uniones_sin, _ = _post(texto, crudas, unir_interpalabra=False)
    assert [e.texto for e in sin] == ["López", "Obrador"] and uniones_sin == []


def test_no_une_tipos_distintos_ni_separados_por_coma():
    texto = "Pemex, Tabasco Sener"
    crudas = [_c("ORG", 0, 5), _c("ORG", 7, 14), _c("LOC", 7, 14), _c("ORG", 15, 20)]
    ents, _, _ = _post(texto, [crudas[0], crudas[2], crudas[3]])
    assert [(e.tipo, e.texto) for e in ents] == [("ORG", "Pemex"), ("LOC", "Tabasco"),
                                                  ("ORG", "Sener")]


# --- fragmentación (T12) ----------------------------------------------------------------------

def test_fragmentar_cubre_todo_y_respeta_solapamiento():
    offsets = [(i * 2, i * 2 + 1) for i in range(23)]
    vs = nm.fragmentar(offsets, limite=10, solapamiento=3)
    assert [(v.tok_inicio, v.tok_fin) for v in vs] == [(0, 10), (7, 17), (14, 23)]
    assert vs[0].primera and vs[-1].ultima and not vs[1].primera
    assert vs[-1].fin == offsets[-1][1]


def test_fragmentar_parametros_invalidos():
    with pytest.raises(ValueError):
        nm.fragmentar([(0, 1)], limite=4, solapamiento=4)


def test_t12_oracion_enorme_entidad_en_borde_y_determinismo():
    # Una sola "oración" de 40 palabras sin puntos; límite real 12-2 = 10 subtokens por ventana.
    palabras = [f"p{i}" for i in range(40)]
    palabras[9], palabras[10] = "Olga", "Sánchez"  # cruza el borde de la primera ventana
    palabras[-1] = "Pemex"  # último subtoken: no debe perderse
    texto = " ".join(palabras)
    pipe = PipelineDoble({"Olga": "PER", "Sánchez": "PER", "Pemex": "ORG"})
    res = nm.inferir([("x_1", texto)], pipe, CFG)["x_1"]
    assert res["ventanas"] > 3
    spans = {(c["etiqueta"], texto[c["inicio"]:c["fin"]]) for c in res["crudas"]}
    assert ("ORG", "Pemex") in spans
    ents, _, _ = nm.posprocesar(texto, res["crudas"], CFG, {"PER", "ORG"})
    assert [(e.tipo, e.texto) for e in ents] == [("PER", "Olga Sánchez"), ("ORG", "Pemex")]
    # Sin duplicados en el traslape y resultado idéntico en una segunda corrida.
    assert len({(c["inicio"], c["fin"]) for c in res["crudas"]}) == len(res["crudas"])
    otra = nm.inferir([("x_1", texto)], PipelineDoble(pipe.lexico), CFG)["x_1"]
    assert (otra["crudas"], otra["ventanas"]) == (res["crudas"], res["ventanas"])


def test_deduplicar_prefiere_no_cortada_y_luego_confianza():
    cortada = nm.Cruda("PER", 10, 15, 0.99, cortada=True, ventana=0)
    completa = nm.Cruda("PER", 10, 22, 0.70, cortada=False, ventana=1)
    otra = nm.Cruda("ORG", 30, 35, 0.60, cortada=False, ventana=1)
    gemela_menor = nm.Cruda("ORG", 30, 35, 0.50, cortada=False, ventana=2)
    assert nm.deduplicar([cortada, completa, otra, gemela_menor]) == [completa, otra]


# --- caché ------------------------------------------------------------------------------------

def _constructor(lexico):
    creados = []

    def construir(modelo, cfg):
        pipe = PipelineDoble(lexico)
        creados.append(pipe)
        return pipe
    return construir, creados


def test_cache_misma_clave_no_reinfiere_y_forzar_si(tmp_path):
    pasajes = [("1_1", "Ana visitó Tabasco"), ("1_2", "Pemex informó")]
    construir, creados = _constructor({"Ana": "PER", "Tabasco": "LOC", "Pemex": "ORG"})
    r1 = nm.ejecutar(pasajes, MODELO, CFG, tmp_path, construir=construir)
    assert (r1.inferidos, r1.cacheados, len(creados)) == (2, 0, 1)
    archivo = tmp_path / "doble@abcdef12" / "1_1.json"
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["texto_sha256"] == nm.sha256_texto("Ana visitó Tabasco")
    r2 = nm.ejecutar(pasajes, MODELO, CFG, tmp_path, construir=construir)
    assert (r2.inferidos, r2.cacheados, len(creados)) == (0, 2, 1)
    assert r2.crudas == r1.crudas
    r3 = nm.ejecutar(pasajes, MODELO, CFG, tmp_path, forzar=True, construir=construir)
    assert (r3.inferidos, len(creados)) == (2, 2)


def test_cambio_de_revision_o_fragmentacion_cambia_la_clave():
    base = nm.parametros_cache(MODELO, CFG)
    otra_rev = nm.parametros_cache({**MODELO, "revision": "ffff000011112222"}, CFG)
    otro_frag = nm.parametros_cache(MODELO, {**CFG, "fragmentacion": {"solapamiento": 4,
                                                                       "margen": 0}})
    sha = nm.sha256_texto("texto")
    claves = {nm.clave_cache(sha, p) for p in (base, otra_rev, otro_frag)}
    assert len(claves) == 3
    assert nm.clave_cache(sha, base) != nm.clave_cache(nm.sha256_texto("otro"), base)


def test_cambio_de_version_posproceso_no_reinfiere(tmp_path):
    pasajes = [("1_1", "Ana visitó Tabasco")]
    construir, creados = _constructor({"Ana": "PER"})
    nm.ejecutar(pasajes, MODELO, CFG, tmp_path, construir=construir)
    cfg2 = {**CFG, "version_posproceso": "2"}
    r = nm.ejecutar(pasajes, MODELO, cfg2, tmp_path, construir=construir)
    assert r.inferidos == 0 and len(creados) == 1


def test_clave_distinta_se_trata_como_ausente(tmp_path):
    construir, creados = _constructor({})
    nm.ejecutar([("1_1", "uno")], MODELO, CFG, tmp_path, construir=construir)
    r = nm.ejecutar([("1_1", "uno cambiado")], MODELO, CFG, tmp_path, construir=construir)
    assert r.inferidos == 1 and len(creados) == 2


# --- configuración ----------------------------------------------------------------------------

def test_config_real_tiene_revision_fija_y_principal():
    cfg = nm.cargar_config()
    principal = nm.modelo_por_slug(cfg)
    assert principal["revision"] != "main" and len(principal["revision"]) == 40


def test_config_rechaza_revision_main(tmp_path):
    (tmp_path / "ner.yaml").write_text(
        "modelos:\n  - {slug: x, repo_id: a/b, revision: main}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        nm.cargar_config(tmp_path)


def test_limite_subtokens_descuenta_especiales_y_margen():
    pipe = PipelineDoble({}, posiciones=512)
    assert nm.limite_subtokens(pipe, 16) == 512 - 2 - 16
