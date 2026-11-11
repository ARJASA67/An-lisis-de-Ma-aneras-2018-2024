"""NER con modelo de Hugging Face (PRD §6.8, D09, D18, U15, T12).

Flujo por pasaje: fragmentación en ventanas de subtokens con solapamiento, inferencia con
`pipeline("token-classification", aggregation_strategy="simple")`, proyección de offsets al texto
canónico, deduplicación en el traslape y caché JSON versionada con las predicciones crudas. El
posproceso (mapa de etiquetas, recorte de extremos, uniones intra e interpalabra) se recalcula
siempre desde lo crudo con su propia versión, de modo que cambiarlo nunca obliga a reinferir.

La construcción del pipeline es inyectable (`construir`) para que las pruebas usen un doble sin red.
"""
from __future__ import annotations

import hashlib
import json
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from mtx import config

NER_YAML = "ner.yaml"
DIR_CACHE = config.DIR_DATA / "cache_ner"
VERSION_FRAGMENTACION = "1"
"""Versión del algoritmo de ventanas; entra en la clave de la caché."""


# --------------------------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------------------------

def cargar_config(dir_config: Path = config.DIR_CONFIG) -> dict:
    """Lee `config/ner.yaml` y valida que cada modelo tenga una revisión fija."""
    cfg = config.cargar_yaml(NER_YAML, dir_config)
    for m in cfg["modelos"]:
        rev = str(m.get("revision") or "")
        if len(rev) < 7 or rev == "main":
            raise ValueError(f"El modelo {m['slug']} necesita una revisión fija (hash), no {rev!r}")
    return cfg


def modelo_por_slug(cfg: dict, slug: str | None = None) -> dict:
    """Devuelve el modelo con ese `slug` o, sin slug, el marcado como principal."""
    for m in cfg["modelos"]:
        if (slug is None and m.get("principal")) or m["slug"] == slug:
            return m
    raise KeyError(f"No hay modelo {slug!r} en config/{NER_YAML}")


def etiqueta_base(etiqueta: str) -> str:
    """`B-PER` → `PER`; `I-LOC` → `LOC`; `MISC` → `MISC`."""
    return etiqueta.split("-", 1)[1] if etiqueta[:2] in ("B-", "I-", "E-", "S-") else etiqueta


def etiquetas_del_modelo(id2label: dict) -> set[str]:
    """Conjunto de etiquetas base que el modelo realmente emite (sin `O`)."""
    return {etiqueta_base(str(e)) for e in id2label.values()} - {"O"}


# --------------------------------------------------------------------------------------------
# Caché
# --------------------------------------------------------------------------------------------

def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def parametros_cache(modelo: dict, cfg: dict) -> dict:
    """Parámetros que cambian el resultado crudo (el lote no entra: no cambia la salida)."""
    frag = cfg["fragmentacion"]
    return {
        "repo_id": modelo["repo_id"],
        "revision": modelo["revision"],
        "tokenizador": f"{modelo['repo_id']}@{modelo['revision']}",
        "version_fragmentacion": VERSION_FRAGMENTACION,
        "solapamiento": int(frag["solapamiento"]),
        "margen": int(frag["margen"]),
        "aggregation_strategy": cfg["inferencia"]["aggregation_strategy"],
    }


def clave_cache(texto_sha: str, params: dict) -> str:
    carga = json.dumps({"texto_sha256": texto_sha, **params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()


def dir_cache_modelo(modelo: dict, raiz: Path = DIR_CACHE) -> Path:
    return raiz / f"{modelo['slug']}@{modelo['revision'][:8]}"


def leer_cache(ruta: Path, clave: str) -> dict | None:
    """El JSON del pasaje si existe y su clave coincide; si no, None (se trata como ausente)."""
    if not ruta.exists():
        return None
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos if datos.get("clave") == clave else None


# --------------------------------------------------------------------------------------------
# Fragmentación (T12)
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Ventana:
    tok_inicio: int
    tok_fin: int
    inicio: int
    """Offset de carácter en el texto canónico (inclusivo)."""
    fin: int
    """Offset de carácter en el texto canónico (exclusivo)."""
    primera: bool
    ultima: bool


def fragmentar(offsets: list[tuple[int, int]], limite: int, solapamiento: int) -> list[Ventana]:
    """Ventanas de a lo sumo `limite` subtokens con `solapamiento` subtokens compartidos.

    `offsets` es el `offset_mapping` del pasaje completo sin tokens especiales. Verifica que las
    ventanas cubren todos los subtokens; si no, lanza un error (nunca trunca en silencio).
    """
    if limite <= 0 or not 0 <= solapamiento < limite:
        raise ValueError(f"Fragmentación inválida: limite={limite}, solapamiento={solapamiento}")
    n = len(offsets)
    ventanas: list[Ventana] = []
    i = 0
    while n:
        j = min(i + limite, n)
        ventanas.append(Ventana(i, j, offsets[i][0], offsets[j - 1][1], i == 0, j == n))
        if j == n:
            break
        i = j - solapamiento
    cubiertos = set()
    for v in ventanas:
        cubiertos.update(range(v.tok_inicio, v.tok_fin))
    if len(cubiertos) != n or (ventanas and ventanas[-1].tok_fin != n):
        raise RuntimeError("Las ventanas no cubren el pasaje completo")
    return ventanas


@dataclass
class Cruda:
    """Predicción del modelo proyectada al texto canónico (antes del posproceso)."""
    etiqueta: str
    inicio: int
    fin: int
    confianza: float
    cortada: bool
    ventana: int = 0

    def a_dict(self) -> dict:
        return {"etiqueta": self.etiqueta, "inicio": self.inicio, "fin": self.fin,
                "confianza": round(self.confianza, 6), "cortada": self.cortada,
                "ventana": self.ventana}


def proyectar(salida: Iterable[dict], v: Ventana, k: int) -> list[Cruda]:
    """Desplaza los offsets de la salida del pipeline sobre `texto[v.inicio:v.fin]`."""
    crudas = []
    for e in salida:
        ini, fin = v.inicio + int(e["start"]), v.inicio + int(e["end"])
        if ini >= fin:
            continue
        cortada = (not v.primera and ini == v.inicio) or (not v.ultima and fin == v.fin)
        etiqueta = str(e.get("entity_group") or e.get("entity"))
        crudas.append(Cruda(etiqueta, ini, fin, float(e["score"]), cortada, k))
    return crudas


def deduplicar(crudas: list[Cruda]) -> list[Cruda]:
    """Resuelve el traslape entre ventanas.

    Prioridad: la no cortada por el borde, después la de mayor confianza. Un candidato se descarta
    si se solapa con otro ya aceptado de una ventana distinta (los idénticos son el caso común).
    """
    orden = sorted(crudas, key=lambda c: (c.cortada, -c.confianza, c.inicio, c.fin, c.ventana))
    aceptadas: list[Cruda] = []
    for c in orden:
        if any(a.ventana != c.ventana and a.inicio < c.fin and c.inicio < a.fin
               for a in aceptadas):
            continue
        aceptadas.append(c)
    return sorted(aceptadas, key=lambda c: (c.inicio, c.fin, c.etiqueta))


# --------------------------------------------------------------------------------------------
# Posproceso (U15)
# --------------------------------------------------------------------------------------------

def _recortable(ch: str) -> bool:
    """Espacios y puntuación (categoría Unicode P*). `$` es símbolo (Sc) y se conserva."""
    return ch.isspace() or unicodedata.category(ch).startswith("P")


@dataclass
class EntidadModelo:
    tipo: str
    inicio: int
    fin: int
    texto: str
    confianza: float
    unida: bool = False
    partes: list[tuple[int, int]] = field(default_factory=list)


def _verificar(texto: str, ents: list[EntidadModelo], etapa: str) -> None:
    for e in ents:
        if not (0 <= e.inicio < e.fin <= len(texto)) or texto[e.inicio:e.fin] != e.texto:
            raise ValueError(f"Offsets rotos tras {etapa}: {e}")


def posprocesar(texto: str, crudas: list[dict], cfg: dict, etiquetas_validas: set[str] | None,
                unir_interpalabra: bool = True) -> tuple[list[EntidadModelo], list[dict], Counter]:
    """Mapa de etiquetas, recorte de extremos y uniones.

    Devuelve (entidades, uniones interpalabra registradas, contador de descartes). `etiquetas_validas`
    es el conjunto real de `id2label`; una etiqueta que el modelo no emite no se mapea.
    """
    mapa: dict = cfg["mapa_etiquetas"]
    descartables = set(cfg.get("descartadas", []))
    descartes: Counter = Counter()
    ents: list[EntidadModelo] = []
    for c in crudas:
        etq = etiqueta_base(c["etiqueta"])
        if etq in descartables:
            descartes[etq] += 1
            continue
        if etq not in mapa or (etiquetas_validas is not None and etq not in etiquetas_validas):
            descartes[f"sin_mapa:{etq}"] += 1
            continue
        ini, fin = int(c["inicio"]), int(c["fin"])
        while ini < fin and _recortable(texto[ini]):
            ini += 1
        while fin > ini and _recortable(texto[fin - 1]):
            fin -= 1
        if ini == fin:
            descartes["vacia_tras_recorte"] += 1
            continue
        ents.append(EntidadModelo(mapa[etq], ini, fin, texto[ini:fin], float(c["confianza"]),
                                  partes=[(ini, fin)]))
    _verificar(texto, ents, "recorte")

    ents.sort(key=lambda e: (e.inicio, e.fin))
    unidas: list[EntidadModelo] = []
    uniones: list[dict] = []
    for e in ents:
        prev = unidas[-1] if unidas else None
        if prev is not None and prev.tipo == e.tipo and e.inicio >= prev.fin:
            hueco = texto[prev.fin:e.inicio]
            intra = hueco == ""
            inter = unir_interpalabra and hueco == " "
            if intra or inter:
                if inter:
                    uniones.append({
                        "tipo": e.tipo, "inicio_1": prev.inicio, "fin_1": prev.fin,
                        "inicio_2": e.inicio, "fin_2": e.fin, "inicio_union": prev.inicio,
                        "fin_union": e.fin, "texto_union": texto[prev.inicio:e.fin],
                        "confianza_1": round(prev.confianza, 6),
                        "confianza_2": round(e.confianza, 6)})
                    prev.unida = True
                prev.fin = e.fin
                prev.texto = texto[prev.inicio:prev.fin]
                prev.confianza = min(prev.confianza, e.confianza)
                prev.partes += e.partes
                continue
        unidas.append(e)
    _verificar(texto, unidas, "union")
    return unidas, uniones, descartes


# --------------------------------------------------------------------------------------------
# Inferencia con caché
# --------------------------------------------------------------------------------------------

def construir_pipeline(modelo: dict, cfg: dict):
    """Pipeline real de transformers (requiere red la primera vez)."""
    from transformers import pipeline

    return pipeline("token-classification", model=modelo["repo_id"], revision=modelo["revision"],
                    aggregation_strategy=cfg["inferencia"]["aggregation_strategy"],
                    device=cfg["inferencia"]["device"])


def limite_subtokens(pipe, margen: int) -> int:
    """Límite real por ventana: posiciones del modelo menos tokens especiales y margen."""
    tok, conf = pipe.tokenizer, pipe.model.config
    maximo = int(getattr(conf, "max_position_embeddings", 512))
    if getattr(conf, "model_type", "") in ("roberta", "xlm-roberta", "camembert"):
        maximo -= 2  # RoBERTa reserva dos posiciones por el relleno
    if 0 < int(getattr(tok, "model_max_length", maximo)) < maximo:
        maximo = int(tok.model_max_length)
    return maximo - tok.num_special_tokens_to_add(pair=False) - margen


def inferir(pasajes: list[tuple[str, str]], pipe, cfg: dict) -> dict[str, dict]:
    """Infiere una lista de (passage_id, texto). Devuelve {passage_id: {crudas, ventanas, s}}."""
    limite = limite_subtokens(pipe, int(cfg["fragmentacion"]["margen"]))
    solape = int(cfg["fragmentacion"]["solapamiento"])
    lote = int(cfg["inferencia"]["lote"])
    trabajos: list[tuple[str, int, Ventana, str]] = []
    ventanas_de: dict[str, int] = {}
    for pid, texto in pasajes:
        enc = pipe.tokenizer(texto, add_special_tokens=False, return_offsets_mapping=True)
        vs = fragmentar([tuple(o) for o in enc["offset_mapping"]], limite, solape)
        ventanas_de[pid] = len(vs)
        trabajos += [(pid, k, v, texto[v.inicio:v.fin]) for k, v in enumerate(vs)]
    t0 = time.perf_counter()
    salidas = pipe([t[3] for t in trabajos], batch_size=lote) if trabajos else []
    seg = (time.perf_counter() - t0) / max(len(pasajes), 1)
    crudas: dict[str, list[Cruda]] = {pid: [] for pid, _ in pasajes}
    for (pid, k, v, _), sal in zip(trabajos, salidas, strict=True):
        crudas[pid] += proyectar(sal, v, k)
    return {pid: {"crudas": [c.a_dict() for c in deduplicar(cs)], "ventanas": ventanas_de[pid],
                  "segundos": round(seg, 4)} for pid, cs in crudas.items()}


@dataclass
class ResultadoNER:
    crudas: dict[str, list[dict]]
    inferidos: int
    cacheados: int
    segundos_carga: float
    segundos_inferencia: float
    etiquetas_modelo: list[str] | None


def ejecutar(pasajes: list[tuple[str, str]], modelo: dict, cfg: dict, raiz_cache: Path = DIR_CACHE,
             forzar: bool = False,
             construir: Callable[[dict, dict], object] = construir_pipeline) -> ResultadoNER:
    """Devuelve las predicciones crudas de cada pasaje, infiriendo solo las claves ausentes."""
    params = parametros_cache(modelo, cfg)
    carpeta = dir_cache_modelo(modelo, raiz_cache)
    crudas: dict[str, list[dict]] = {}
    pendientes: list[tuple[str, str]] = []
    claves: dict[str, str] = {}
    etiquetas: set[str] = set()
    for pid, texto in pasajes:
        claves[pid] = clave_cache(sha256_texto(texto), params)
        datos = None if forzar else leer_cache(carpeta / f"{pid}.json", claves[pid])
        if datos is None:
            pendientes.append((pid, texto))
        else:
            crudas[pid] = datos["crudas"]
            etiquetas.update(datos.get("etiquetas_modelo", []))
    t_carga = t_inf = 0.0
    if pendientes:
        t0 = time.perf_counter()
        pipe = construir(modelo, cfg)
        t_carga = time.perf_counter() - t0
        etiquetas = etiquetas_del_modelo(pipe.model.config.id2label)
        t0 = time.perf_counter()
        nuevos = inferir(pendientes, pipe, cfg)
        t_inf = time.perf_counter() - t0
        try:
            import transformers
            version = transformers.__version__
        except ImportError:  # pragma: no cover - solo con dobles de prueba
            version = None
        carpeta.mkdir(parents=True, exist_ok=True)
        textos = dict(pendientes)
        for pid, res in nuevos.items():
            datos = {"clave": claves[pid], "passage_id": pid,
                     "texto_sha256": sha256_texto(textos[pid]), "parametros": params,
                     "etiquetas_modelo": sorted(etiquetas), "version_transformers": version,
                     **res}
            (carpeta / f"{pid}.json").write_text(
                json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                newline="\n")
            crudas[pid] = res["crudas"]
    return ResultadoNER(crudas, len(pendientes), len(pasajes) - len(pendientes),
                        round(t_carga, 3), round(t_inf, 3), sorted(etiquetas) or None)
