"""Carga, limpieza auditada y segmentación del corpus (PRD §6.1, D02 a D05).

Flujo: `cargar()` -> `limpiar_ruido()` -> `segmentar()`.

El corpus real no sigue el formato que suponía el PRD. Las marcas de interlocutor son
`~~~ETIQUETA texto` (sin dos puntos, con espacios duros) para el presidente y los reporteros, y
`NOMBRE, CARGO: texto` en línea para los demás; casi no hay saltos de línea. Por eso
`limpiar_ruido()` canoniza las marcas a un formato con una intervención por línea:

    "\\nQUIEN: texto de la intervención\\nOTRO: texto..."

y `partir_canonico()` las separa sin ambigüedad (la expresión del kit no reconoce ninguna marca
del corpus real; ver `docs/contratos_kit.md` y `docs/decisiones.md`). `ventanas()` sí se
reutiliza del kit, a través de `adaptadores_kit`.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import adaptadores_kit, config

COLUMNAS_PASAJES = [
    "passage_id", "doc_id", "fecha", "fecha_original", "fecha_fuente", "titulo", "url",
    "posicion", "interlocutor", "texto", "inicio_cuerpo", "n_palabras", "es_reportero",
    "marca_reinyectada", "texto_sha256", "intervencion_id", "token_inicio", "token_fin",
]

_INI = "\u0001"  # centinelas internos: inicio de marca ...
_FIN = "\u0002"  # ... y fin de la etiqueta de la marca

_ABREVIATURAS = {"DR", "DRA", "LIC", "ING", "GRAL", "MTRO", "MTRA", "PROF", "SR", "SRA", "SRITA",
                 "ARQ", "GEN", "COL", "CAP", "TTE", "ALM", "SEN", "DIP", "CP", "DON", "DOÑA"}


# --------------------------------------------------------------------------- utilidades


def sin_acentos(texto: str) -> str:
    """Quita diacríticos (NFKD) conservando la ñ como n."""
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar_para_hash(texto: str) -> str:
    """Minúsculas, sin acentos, sin marcas `~~~` y con espacios colapsados (PRD §6.1.2 punto 4)."""
    t = sin_acentos(texto.replace("~~~", " ")).lower()
    return re.sub(r"\s+", " ", t).strip()


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _kit_corpus():
    return adaptadores_kit.cargar_modulo_corpus()


# --------------------------------------------------------------------------- carga y huella


def cargar() -> pd.DataFrame:
    """Corpus del snapshot con `doc_id` 0..N-1, vía el kit. Nunca reordena ni filtra."""
    return _kit_corpus().cargar_corpus()


def commit_dataset() -> str | None:
    """Commit del dataset en Hugging Face si la red lo permite; `None` en caso contrario."""
    try:
        from huggingface_hub import HfApi
        return HfApi().dataset_info("carevies/discursos_AMLO").sha
    except Exception:  # noqa: BLE001  cualquier fallo de red o de la biblioteca: se declara desconocido
        return None


def huella_corpus(df: pd.DataFrame, ruta_parquet: Path) -> dict:
    """Contenido de `data/corpus_meta.json` (PRD §6.1.1)."""
    ruta_parquet = Path(ruta_parquet)
    return {
        "dataset": "carevies/discursos_AMLO",
        "sha256_parquet": adaptadores_kit.sha256_archivo(ruta_parquet),
        "filas": len(df),
        "fecha_descarga": date.fromtimestamp(ruta_parquet.stat().st_mtime).isoformat(),
        "commit_dataset": commit_dataset(),
        "columnas": list(df.columns),
    }


# --------------------------------------------------------------------------- limpieza de texto


def _compilar(cfg: dict) -> dict:
    """Expresiones compiladas a partir de `config/limpieza.yaml`."""
    m = cfg["marcas"]
    et = "|".join(re.escape(e) for e in m["etiquetas_tilde"])
    lemas = "|".join(re.escape(x) for x in cfg["lemas"])
    n = int(m["max_caracteres_etiqueta"])
    return {
        "acotacion_parentesis": re.compile(r"\(\s*([^()]{1,120}?)\s*\)"),
        "acotaciones": [re.compile(p, re.IGNORECASE) for p in cfg["acotaciones"]],
        "lema": re.compile(rf"(?:20\d\d:\s*)?(?:{lemas})", re.IGNORECASE),
        "tilde": re.compile(rf"~~~\s*({et})\s*"),
        "una_palabra": set(m["etiquetas_en_linea_una_palabra"]),
        "max_etiqueta": n,
    }


def _recortar_a_ultima_oracion(corrida: str) -> tuple[str, str]:
    """Si la corrida mayúscula arrastra una oración previa ("... IMSS. ZOÉ ROBLEDO"), la parte.

    Devuelve (prefijo, etiqueta). Un punto tras una abreviatura (DR., LIC.) o una inicial no corta.
    """
    corte = 0
    for mt in re.finditer(r"([A-ZÁÉÍÓÚÑÜ0-9]{2,})([.?!…])\s+", corrida):
        if mt.group(1) in _ABREVIATURAS:
            continue
        corte = mt.end()
    return corrida[:corte], corrida[corte:]


_CARACTERES_ETIQUETA = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑÜ0123456789 ,.-/()&'’‘“”\"")
_MAYUSCULAS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑÜ")


def _marcar_en_linea(t: str, rx: dict, etiquetas: Counter) -> str:
    """Convierte `NOMBRE, CARGO: texto` en línea en marcas canónicas.

    Para cada ":" seguido de espacio recorre hacia atrás la corrida de mayúsculas y la recorta a
    la última oración. Es equivalente a una expresión regular perezosa, pero lineal.
    """
    piezas: list[str] = []
    cursor = 0
    for mt in re.finditer(r":(?=\s|$)", t):
        fin = mt.start()
        if fin < cursor:
            continue
        j = fin
        limite = max(cursor, fin - rx["max_etiqueta"])
        while j > limite and t[j - 1] in _CARACTERES_ETIQUETA:
            j -= 1
        while j < fin and not (t[j] in _MAYUSCULAS and (j == 0 or t[j - 1] == " ")):
            j += 1
        if j >= fin or (j > 0 and t[j - 1] not in " \u0001\u0002"):
            continue
        prefijo, etiqueta = _recortar_a_ultima_oracion(t[j:fin])
        etiqueta = etiqueta.strip(" ,.")
        palabras = etiqueta.split()
        letras = sum(c.isalpha() for c in etiqueta)
        valida = (letras >= 4 and _parentesis_balanceados(etiqueta)
                  and (len(palabras) >= 2 or etiqueta in rx["una_palabra"]))
        if not valida:
            continue
        etiquetas[("en_linea", etiqueta)] += 1
        piezas.append(t[cursor:j])
        piezas.append(f"{prefijo}{_INI}{etiqueta}{_FIN}")
        cursor = fin + 1
    piezas.append(t[cursor:])
    return "".join(piezas)


def _parentesis_balanceados(texto: str) -> bool:
    """Cierto si cada ")" cierra un "(" previo y no queda ninguno abierto."""
    prof = 0
    for c in texto:
        prof += (c == "(") - (c == ")")
        if prof < 0:
            return False
    return prof == 0


def limpiar_texto(texto: str, rx: dict) -> tuple[str, dict]:
    """Limpia y canoniza un discurso. Devuelve (texto_canonico, conteos).

    Orden: Unicode y espacios; acotaciones; lemas; marcas `~~~`; marcas en línea.
    Los saltos de línea originales se convierten en espacios: en el canónico, cada salto separa
    dos intervenciones.
    """
    cont: Counter = Counter()
    cont["caracteres_originales"] = len(texto)

    t = unicodedata.normalize("NFC", texto)
    cont["saltos_originales"] = t.count("\n") + t.count("\r")
    cont["espacios_duros"] = len(re.findall("[\u00a0\u2007\u2009\u202f]", t))
    t = re.sub("[\u200b\ufeff]", "", t)
    t = re.sub("[\u00a0\u2007\u2009\u202f\r\n\t]", " ", t)
    t = re.sub(r" {2,}", " ", t)

    tipos_acot: Counter = Counter()

    def quitar_acotacion(mt: re.Match) -> str:
        contenido = re.sub(r"\s+", " ", mt.group(1)).strip()
        if any(p.fullmatch(contenido) for p in rx["acotaciones"]):
            tipos_acot[contenido.lower()] += 1
            cont["caracteres_descartados"] += len(mt.group(0))
            return " "
        return mt.group(0)

    t = rx["acotacion_parentesis"].sub(quitar_acotacion, t)

    def quitar_lema(mt: re.Match) -> str:
        cont["lemas"] += 1
        cont["caracteres_descartados"] += len(mt.group(0))
        return " "

    t = rx["lema"].sub(quitar_lema, t)

    etiquetas: Counter = Counter()

    def marca_tilde(mt: re.Match) -> str:
        etiquetas[("tilde", mt.group(1))] += 1
        return f"{_INI}{mt.group(1)}{_FIN} "

    t = rx["tilde"].sub(marca_tilde, t)
    cont["tildes_sin_etiqueta"] = t.count("~~~")
    t = t.replace("~~~", " ")

    t = _marcar_en_linea(t, rx, etiquetas)

    t = t.replace(_INI, "\n").replace(_FIN, ":")
    t = re.sub(r"[ ]+\n", "\n", t)
    t = re.sub(r"\n:", "\n", t)
    t = re.sub(r" {2,}", " ", t).rstrip()
    cont["caracteres_canonicos"] = len(t)
    cont["acotaciones"] = sum(tipos_acot.values())
    cont["marcas_tilde"] = sum(v for (k, _), v in etiquetas.items() if k == "tilde")
    cont["marcas_en_linea"] = sum(v for (k, _), v in etiquetas.items() if k == "en_linea")
    return t, {"conteos": cont, "tipos_acotacion": tipos_acot, "etiquetas": etiquetas}


def partir_canonico(texto: str) -> list[tuple[str, str]]:
    """Separa un texto canónico en intervenciones `(interlocutor, texto)`.

    El canónico usa "\\n" solo como frontera de intervención. Lo anterior a la primera marca
    (si lo hay) es una intervención sin interlocutor. Un texto sin marcas es una sola.
    """
    piezas = texto.split("\n")
    salida: list[tuple[str, str]] = []
    if piezas[0].strip():
        salida.append(("", piezas[0].strip()))
    for pieza in piezas[1:]:
        pieza = pieza.strip()
        if not pieza:
            continue
        if ": " in pieza:
            quien, _, que = pieza.partition(": ")
        elif pieza.endswith(":"):
            quien, que = pieza[:-1], ""
        else:  # no debería ocurrir: toda línea nace de una marca
            quien, que = "", pieza
        salida.append((quien.strip(), que.strip()))
    return salida


# --------------------------------------------------------------------------- fechas


def _fecha_valida(y: int, m: int, d: int, rango: tuple[pd.Timestamp, pd.Timestamp]):
    try:
        f = pd.Timestamp(y, m, d)
    except (ValueError, OverflowError):
        return None
    return f if rango[0] <= f <= rango[1] else None


def candidata_titulo(titulo: str, rango) -> pd.Timestamp | None:
    """Fecha al inicio del título (`DD.MM.AA` o `DD.MM.AAAA`) si es válida y está en rango."""
    mt = re.match(r"\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4}|\d{2})\b", titulo or "")
    if not mt:
        return None
    anio = int(mt.group(3))
    anio = anio + 2000 if anio < 100 else anio
    return _fecha_valida(anio, int(mt.group(2)), int(mt.group(1)), rango)


def candidata_url(url: str, rango) -> pd.Timestamp | None:
    """Fecha en la URL (`DD-MM-AA-` o `AAAA/MM/DD`) si es válida y está en rango."""
    mt = re.search(r"/(\d{2})-(\d{2})-(\d{2})-", url or "")
    if mt:
        return _fecha_valida(2000 + int(mt.group(3)), int(mt.group(2)), int(mt.group(1)), rango)
    mt = re.search(r"(20\d\d)[/-](\d{2})[/-](\d{2})", url or "")
    if mt:
        return _fecha_valida(int(mt.group(1)), int(mt.group(2)), int(mt.group(3)), rango)
    return None


def reparar_fecha(fecha, titulo: str, url: str, rango, tolerancia: int) -> dict:
    """Aplica las reglas del PRD §6.1.2 punto 5. Nunca inventa una fecha.

    Una candidata fuera de [rango] (por ejemplo un título `03.03.30`) se descarta: así un error
    tipográfico del año no sustituye a una fecha original correcta.
    """
    c_tit, c_url = candidata_titulo(titulo, rango), candidata_url(url, rango)
    original = None if pd.isna(fecha) else pd.Timestamp(fecha)
    en_rango = original is not None and rango[0] <= original <= rango[1]
    res = {"fecha": original, "fecha_fuente": "original" if original is not None else "ninguna",
           "candidata_titulo": c_tit, "candidata_url": c_url, "motivo": ""}

    if c_tit is not None and c_url is not None and abs((c_tit - c_url).days) > tolerancia:
        res["motivo"] = "titulo_y_url_se_contradicen"  # no se corrige, solo se señala
        return res

    cand, fuente = (c_tit, "titulo") if c_tit is not None else (c_url, "url")
    if cand is None:
        res["motivo"] = "sin_candidata" if not en_rango else ""
        return res
    if original is None:
        res.update(fecha=cand, fecha_fuente=fuente, motivo="fecha_ausente")
    elif not en_rango:
        res.update(fecha=cand, fecha_fuente=fuente, motivo="fecha_fuera_de_rango")
    elif abs((cand - original).days) > tolerancia:
        res.update(fecha=cand, fecha_fuente=fuente, motivo="fecha_difiere_de_la_candidata")
    return res


# --------------------------------------------------------------------------- duplicados


def _shingles(texto_norm: str, k: int) -> set[int]:
    pal = texto_norm.split()
    out = set()
    for i in range(len(pal) - k + 1):
        h = hashlib.blake2b(" ".join(pal[i:i + k]).encode("utf-8"), digest_size=8).digest()
        out.add(int.from_bytes(h, "big"))
    return out


def detectar_duplicados(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Duplicados exactos y casi duplicados. Se conserva el menor `doc_id`.

    Requiere columnas `doc_id`, `fecha` (ya reparada), `texto_norm`. Devuelve filas
    `doc_id_excluido, doc_id_conservado, tipo, similitud, fecha, titulo`.
    """
    k = int(cfg["duplicados"]["shingle_palabras"])
    umbral = float(cfg["duplicados"]["jaccard_minimo"])
    revertidos = {int(x) for x in cfg["duplicados"].get("reversiones", [])}
    filas = []
    excluidos: set[int] = set()

    vistos: dict[str, int] = {}
    for r in df.sort_values("doc_id").itertuples(index=False):
        h = hashlib.sha256(r.texto_norm.encode("utf-8")).hexdigest()
        if h in vistos:
            if r.doc_id not in revertidos:
                excluidos.add(r.doc_id)
                filas.append({"doc_id_excluido": r.doc_id, "doc_id_conservado": vistos[h],
                              "tipo": "exacto", "similitud": 1.0, "fecha": r.fecha,
                              "titulo": r.titulo})
        else:
            vistos[h] = r.doc_id

    restantes = df[~df["doc_id"].isin(excluidos)].sort_values("doc_id")
    for _, grupo in restantes.dropna(subset=["fecha"]).groupby("fecha", sort=True):
        if len(grupo) < 2:
            continue
        conjuntos = {r.doc_id: _shingles(r.texto_norm, k) for r in grupo.itertuples(index=False)}
        conservados: list[int] = []
        for r in grupo.itertuples(index=False):
            mejor, sim_mejor = None, 0.0
            for c in conservados:
                a, b = conjuntos[r.doc_id], conjuntos[c]
                if not a or not b:
                    continue
                sim = len(a & b) / len(a | b)
                if sim > sim_mejor:
                    mejor, sim_mejor = c, sim
            if mejor is not None and sim_mejor >= umbral and r.doc_id not in revertidos:
                filas.append({"doc_id_excluido": r.doc_id, "doc_id_conservado": mejor,
                              "tipo": "casi_duplicado", "similitud": round(sim_mejor, 4),
                              "fecha": r.fecha, "titulo": r.titulo})
            else:
                conservados.append(r.doc_id)
    cols = ["doc_id_excluido", "doc_id_conservado", "tipo", "similitud", "fecha", "titulo"]
    return pd.DataFrame(filas, columns=cols)


# --------------------------------------------------------------------------- limpiar_ruido


def limpiar_ruido(df: pd.DataFrame, cfg: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Limpieza auditada (D05). No renumera ni elimina filas: los excluidos se marcan.

    Devuelve `(df_limpio, informes)`. `df_limpio` añade `texto_canonico`, `fecha_original`,
    `fecha_fuente`, `excluido`, `motivo_exclusion` y `duplicado_de`; `fecha` queda reparada.
    `informes` contiene los DataFrame `auditoria`, `duplicados`, `fechas`, `etiquetas` y el
    diccionario `resumen`.
    """
    cfg = cfg or config.cargar_yaml("limpieza.yaml")
    rx = _compilar(cfg)
    rango = tuple(pd.Timestamp(x) for x in cfg["fechas"]["rango_valido"])
    tol = int(cfg["fechas"]["tolerancia_dias"])

    out = df.copy()
    out["fecha_original"] = out["fecha"]
    canonicos, auditoria, etiquetas_tot, acot_tot = [], [], Counter(), Counter()
    tot: Counter = Counter()
    for r in out.itertuples(index=False):
        canonico, info = limpiar_texto(r.texto, rx)
        canonicos.append(canonico)
        c = info["conteos"]
        auditoria.append({"doc_id": r.doc_id, **{k: int(v) for k, v in c.items()}})
        tot.update({k: int(v) for k, v in c.items()})
        etiquetas_tot.update(info["etiquetas"])
        acot_tot.update(info["tipos_acotacion"])
    out["texto_canonico"] = canonicos
    auditoria = pd.DataFrame(auditoria)

    fechas, nuevas, fuentes = [], [], []
    for r in out.itertuples(index=False):
        rep = reparar_fecha(r.fecha_original, r.titulo, r.url, rango, tol)
        nuevas.append(rep["fecha"] if rep["fecha"] is not None else pd.NaT)
        fuentes.append(rep["fecha_fuente"])
        if rep["motivo"] or rep["fecha_fuente"] != "original":
            fechas.append({"doc_id": r.doc_id, "fecha_original": r.fecha_original,
                           "fecha": rep["fecha"], "fecha_fuente": rep["fecha_fuente"],
                           "candidata_titulo": rep["candidata_titulo"],
                           "candidata_url": rep["candidata_url"], "motivo": rep["motivo"],
                           "titulo": r.titulo})
    out["fecha"] = pd.to_datetime(pd.Series(nuevas, index=out.index))
    out["fecha_fuente"] = fuentes
    fechas = pd.DataFrame(fechas, columns=[
        "doc_id", "fecha_original", "fecha", "fecha_fuente", "candidata_titulo", "candidata_url",
        "motivo", "titulo"])

    out["texto_norm"] = out["texto"].map(normalizar_para_hash)
    duplicados = detectar_duplicados(out, cfg)
    out = out.drop(columns="texto_norm")
    out["excluido"] = out["doc_id"].isin(duplicados["doc_id_excluido"])
    mapa_tipo = dict(zip(duplicados["doc_id_excluido"], duplicados["tipo"], strict=True))
    mapa_orig = dict(zip(duplicados["doc_id_excluido"], duplicados["doc_id_conservado"], strict=True))
    out["motivo_exclusion"] = [mapa_tipo.get(d, "") for d in out["doc_id"]]
    out["duplicado_de"] = pd.array([mapa_orig.get(d, pd.NA) for d in out["doc_id"]], dtype="Int64")

    auditoria["excluido"] = auditoria["doc_id"].isin(duplicados["doc_id_excluido"])
    etiquetas = pd.DataFrame(
        [{"tipo_marca": k[0], "etiqueta": k[1], "apariciones": v} for k, v in etiquetas_tot.items()],
        columns=["tipo_marca", "etiqueta", "apariciones"],
    ).sort_values(["apariciones", "etiqueta"], ascending=[False, True], kind="stable")

    orig, desc = tot["caracteres_originales"], tot["caracteres_descartados"]
    resumen = {
        "discursos": len(out),
        "discursos_excluidos": int(out["excluido"].sum()),
        "duplicados_exactos": int((duplicados["tipo"] == "exacto").sum()),
        "casi_duplicados": int((duplicados["tipo"] == "casi_duplicado").sum()),
        "acotaciones_eliminadas": int(tot["acotaciones"]),
        "acotaciones_por_tipo": {k: int(v) for k, v in acot_tot.most_common()},
        "lemas_eliminados": int(tot["lemas"]),
        "marcas_tilde": int(tot["marcas_tilde"]),
        "marcas_en_linea": int(tot["marcas_en_linea"]),
        "etiquetas_distintas": len(etiquetas),
        "tildes_sin_etiqueta": int(tot["tildes_sin_etiqueta"]),
        "espacios_duros_normalizados": int(tot["espacios_duros"]),
        "saltos_originales_convertidos": int(tot["saltos_originales"]),
        "fechas_reparadas": int((fechas["fecha_fuente"].isin(["titulo", "url"])).sum()),
        "fechas_senaladas": int((fechas["motivo"] != "").sum()),
        "caracteres_originales": int(orig),
        "caracteres_descartados": int(desc),
        "porcentaje_caracteres_descartados": round(100 * desc / orig, 4) if orig else 0.0,
    }
    informes = {"auditoria": auditoria, "duplicados": duplicados, "fechas": fechas,
                "etiquetas": etiquetas, "resumen": resumen}
    return out, informes


# --------------------------------------------------------------------------- segmentación


def es_reportero(interlocutor: str, cfg: dict | None = None) -> bool:
    """Conjunto cerrado de marcas de reportero; una marca desconocida no lo es (PRD §6.1.3)."""
    cfg = cfg or config.cargar_yaml("limpieza.yaml")
    rep = cfg["marcas"]["reportero"]
    return interlocutor in rep["exactas"] or interlocutor.startswith(rep["prefijo"])


def segmentar_con_descartes(df: pd.DataFrame, tam: int = 200, paso: int = 150,
                            min_tokens: int = 40, reinyectar_marca: bool = True,
                            cfg: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Segmenta en pasajes con la marca de interlocutor reinyectada (D02, D03).

    `df` debe traer `doc_id, fecha, fecha_original, fecha_fuente, titulo, url, texto_canonico` y
    `excluido`. Devuelve `(pasajes, descartes)`; los descartes son las ventanas con menos de
    `min_tokens` palabras, con su interlocutor. `posicion` solo avanza con pasajes conservados.
    """
    cfg = cfg or config.cargar_yaml("limpieza.yaml")
    kit = _kit_corpus()
    filas, descartes = [], []
    for r in df.sort_values("doc_id").itertuples(index=False):
        if getattr(r, "excluido", False):
            continue
        pos = 0
        for idx, (quien, que) in enumerate(partir_canonico(r.texto_canonico)):
            toks = que.split()
            intervencion_id = f"{r.doc_id}_i{idx}"
            for k, trozo in enumerate(kit.ventanas(toks, tam, paso)):
                ini = k * paso
                fin = min(ini + tam, len(toks))
                if len(trozo.split()) < min_tokens:
                    descartes.append({
                        "doc_id": r.doc_id, "intervencion_id": intervencion_id,
                        "interlocutor": quien, "es_reportero": es_reportero(quien, cfg),
                        "n_palabras": len(trozo.split()), "ejemplo": trozo[:200]})
                    continue
                con_marca = bool(quien) and reinyectar_marca
                texto = f"{quien}: {trozo}" if con_marca else trozo
                filas.append({
                    "passage_id": f"{r.doc_id}_{pos}", "doc_id": r.doc_id, "fecha": r.fecha,
                    "fecha_original": r.fecha_original, "fecha_fuente": r.fecha_fuente,
                    "titulo": r.titulo, "url": r.url, "posicion": pos, "interlocutor": quien,
                    "texto": texto, "inicio_cuerpo": len(quien) + 2 if con_marca else 0,
                    "n_palabras": len(texto.split()), "es_reportero": es_reportero(quien, cfg),
                    "marca_reinyectada": con_marca, "texto_sha256": sha256_texto(texto),
                    "intervencion_id": intervencion_id, "token_inicio": ini, "token_fin": fin,
                })
                pos += 1
    pasajes = pd.DataFrame(filas, columns=COLUMNAS_PASAJES)
    pasajes["fecha"] = pd.to_datetime(pasajes["fecha"])
    pasajes["fecha_original"] = pd.to_datetime(pasajes["fecha_original"])
    cols_d = ["doc_id", "intervencion_id", "interlocutor", "es_reportero", "n_palabras", "ejemplo"]
    return pasajes, pd.DataFrame(descartes, columns=cols_d)


def segmentar(df: pd.DataFrame, tam: int = 200, paso: int = 150, min_tokens: int = 40,
              reinyectar_marca: bool = True) -> pd.DataFrame:
    """Como `segmentar_con_descartes`, devolviendo solo los pasajes."""
    return segmentar_con_descartes(df, tam, paso, min_tokens, reinyectar_marca)[0]


def hash_pasajes(pasajes: pd.DataFrame) -> str:
    """Huella del contenido, independiente del orden de las filas (determinismo, PRD §6.1.3)."""
    h = hashlib.sha256()
    for fila in pasajes.sort_values("passage_id", key=lambda s: s.map(_clave_id)).itertuples(index=False):
        h.update("\x1f".join(str(x) for x in fila).encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


def _clave_id(passage_id: str) -> tuple[int, int]:
    doc, pos = passage_id.split("_")
    return int(doc), int(pos)


# --------------------------------------------------------------------------- estadísticas


def estadisticas_corpus(df: pd.DataFrame) -> dict:
    """`salida/01_estadisticas_corpus.json` (PRD §6.1.1), sobre el corpus sin tocar."""
    n = df["texto"].str.split().str.len()
    sin_marcas = int((~df["texto"].str.contains("~~~", regex=False)).sum())
    fechas = df["fecha"].dropna()
    return {
        "discursos": len(df),
        "textos_vacios": int((df["texto"].str.strip() == "").sum()),
        "fecha_min": None if fechas.empty else fechas.min().date().isoformat(),
        "fecha_max": None if fechas.empty else fechas.max().date().isoformat(),
        "fecha_nat": int(df["fecha"].isna().sum()),
        "palabras": {
            "minimo": int(n.min()), "p10": float(n.quantile(0.10)), "mediana": float(n.median()),
            "media": round(float(n.mean()), 2), "p90": float(n.quantile(0.90)),
            "maximo": int(n.max()),
        },
        "discursos_sin_marcas_tilde": sin_marcas,
        "discursos_sin_marcas_reconocidas_por_el_kit": int(sum(
            1 for t in df["texto"] if not _kit_corpus().RE_INTERLOCUTOR.search(t))),
    }


def escribir_json(ruta: Path, objeto: dict) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(objeto, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")
