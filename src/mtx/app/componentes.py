"""Lógica de la app de anotación sin Streamlit (la reutilizan las vistas y la CLI).

Persistencia atómica con respaldo y número de revisión, resaltado seguro desde offsets, modo
ciego, almacén de juicios y estado de artefactos. PRD §7, D19, T15.

Reglas que este módulo hace cumplir:
- La app nunca sugiere ni precarga juicios: `AlmacenJuicios` solo escribe lo que el alumno elige.
- No se registra ningún juicio mientras `config/criterios_relevancia.md` no exista (D07).
- Juicios es ciego al modelo: el pool se lee sin `variantes` ni `mejor_rango_*`.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .. import adaptadores_kit, config, pool, preproceso

CRITERIOS_RELEVANCIA = config.DIR_CONFIG / "criterios_relevancia.md"
CIERRE_GOLD = config.DIR_ANOTACIONES / "cierre_gold.json"
POOL_META = config.DIR_DATA / "pool_meta.json"
COLUMNAS_PUBLICAS_POOL = ["query_id", "passage_id", "doc_id", "fecha", "texto", "texto_sha256"]
"""Únicas columnas del pool que ve la vista de Juicios (sin variantes, rangos ni `en_ventana`)."""

ESTADOS = ("pendiente humano", "pendiente técnico", "válido", "obsoleto", "error")


# --------------------------------------------------------------------------- persistencia


class ConflictoRevision(RuntimeError):
    """El archivo cambió en disco desde que esta sesión lo cargó (T15, dos pestañas)."""


def _ruta_meta(ruta: Path) -> Path:
    return ruta.with_suffix(".meta.json")


def leer_meta(ruta: Path) -> dict:
    """Metadatos de un CSV de anotaciones: `revision` (0 si no existe) y `pool_sha256`."""
    meta = _ruta_meta(ruta)
    if not meta.exists():
        return {"revision": 0}
    return json.loads(meta.read_text(encoding="utf-8"))


def _reemplazar_atomico(destino: Path, contenido: bytes) -> None:
    """Escribe a un temporal en el mismo directorio, lo sincroniza y hace `os.replace`."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, prefix=f".{destino.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, destino)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def escribir_csv_atomico(ruta: Path, df: pd.DataFrame, revision_esperada: int,
                         extra_meta: dict | None = None) -> int:
    """Escribe `df` como CSV (UTF-8 sin BOM, `\\n`) y devuelve la nueva revisión.

    Antes de escribir relee la revisión del disco: si no coincide con `revision_esperada` lanza
    `ConflictoRevision` y no toca nada. Guarda el archivo anterior en `respaldo/` con su revisión.
    """
    actual = leer_meta(ruta)["revision"]
    if actual != revision_esperada:
        raise ConflictoRevision(
            f"{ruta.name}: la revisión en disco es {actual} y esta sesión cargó "
            f"{revision_esperada}. Editado desde otra pestaña: recarga antes de guardar.")
    if ruta.exists():
        respaldo = ruta.parent / "respaldo" / f"{ruta.stem}.r{actual:05d}{ruta.suffix}"
        respaldo.parent.mkdir(parents=True, exist_ok=True)
        respaldo.write_bytes(ruta.read_bytes())
    contenido = df.to_csv(index=False, lineterminator="\n").encode("utf-8")
    _reemplazar_atomico(ruta, contenido)
    nueva = actual + 1
    meta = {"revision": nueva, "sha256": hashlib.sha256(contenido).hexdigest(), **(extra_meta or {})}
    _reemplazar_atomico(_ruta_meta(ruta), (json.dumps(meta, indent=2) + "\n").encode("utf-8"))
    return nueva


# --------------------------------------------------------------------------- resaltado


def resaltar_html(texto: str, spans: list[tuple[int, int, str]]) -> str:
    """HTML seguro desde offsets: cada tramo pasa por `html.escape` y los spans van en `<mark>`.

    `spans` = `(inicio, fin, clase)` con índices de carácter Python, `fin` exclusivo. Se ordenan
    por `inicio`; un span inválido, solapado o anidado lanza `ValueError` (nunca se oculta).
    Nunca se usa `str.replace` ni regex sobre el texto.
    """
    previo = 0
    partes = []
    for inicio, fin, clase in sorted(spans):
        if not 0 <= inicio < fin <= len(texto):
            raise ValueError(f"Span fuera del texto: ({inicio}, {fin}) con len={len(texto)}")
        if inicio < previo:
            raise ValueError(f"Spans solapados o anidados en {inicio}")
        partes.append(html.escape(texto[previo:inicio]))
        partes.append(f'<mark class="{html.escape(clase)}">{html.escape(texto[inicio:fin])}</mark>')
        previo = fin
    partes.append(html.escape(texto[previo:]))
    return "".join(partes)


def spans_terminos(texto: str, consulta: str, inicio_cuerpo: int = 0) -> list[tuple[int, int, str]]:
    """Spans de los tokens del cuerpo cuya raíz coincide con alguna raíz de la consulta.

    Mismo preprocesamiento del índice (`preproceso.tokenizar`), aplicado token por token sobre el
    texto original, así los offsets son del `texto` completo. La marca de interlocutor
    (`texto[:inicio_cuerpo]`) no se busca (D03).
    """
    raices = set(preproceso.tokenizar(consulta))
    spans = []
    for m in preproceso.RE_TOKEN.finditer(texto, inicio_cuerpo):
        if set(preproceso.tokenizar(m.group())) & raices:
            spans.append((m.start(), m.end(), "termino"))
    return spans


def html_pasaje(texto: str, consulta: str, inicio_cuerpo: int) -> str:
    """Pasaje completo con la marca de interlocutor en gris y los términos de la consulta marcados."""
    spans = spans_terminos(texto, consulta, inicio_cuerpo)
    if inicio_cuerpo > 0:
        spans.append((0, inicio_cuerpo, "marca"))
    return resaltar_html(texto, spans)


# --------------------------------------------------------------------------- modo ciego


def gold_cerrado(ruta: Path = CIERRE_GOLD) -> bool:
    """Única comprobación del modo ciego: existe `anotaciones/cierre_gold.json`."""
    return ruta.exists()


def cargar_pool_ciego(ruta: Path = pool.POOL_CSV) -> pd.DataFrame:
    """Pool sin procedencia: la vista de Juicios no recibe variantes, rangos ni `en_ventana`."""
    return pd.read_csv(ruta, usecols=COLUMNAS_PUBLICAS_POOL,
                       dtype={"passage_id": str, "fecha": str, "texto": str, "texto_sha256": str},
                       keep_default_na=False)


def metadatos_pasajes(ids: list[str], ruta: Path = config.PASAJES_PARQUET) -> pd.DataFrame:
    """`titulo`, `interlocutor` e `inicio_cuerpo` de los pasajes pedidos (lectura filtrada)."""
    df = pd.read_parquet(ruta, columns=["passage_id", "titulo", "interlocutor", "inicio_cuerpo"],
                         filters=[("passage_id", "in", list(ids))])
    return df.set_index("passage_id")


# --------------------------------------------------------------------------- juicios


def criterios_listos(ruta: Path | None = None) -> bool:
    """Los criterios los escribe el alumno; sin archivo no se registra ningún juicio."""
    ruta = ruta or CRITERIOS_RELEVANCIA
    return ruta.exists() and ruta.read_text(encoding="utf-8").strip() != ""


class AlmacenJuicios:
    """Lectura y escritura de `anotaciones/juicios_relevancia.csv` para una sesión.

    Estados por `(query_id, passage_id)`: sin fila (nunca visto), `""` (omitido, sin juzgar),
    `"0"` o `"1"`. Omitido nunca se convierte en 0.
    """

    def __init__(self, pool_df: pd.DataFrame, ruta: Path | None = None,
                 ruta_criterios: Path | None = None, hash_pool: str = ""):
        self.ruta = ruta or pool.JUICIOS_CSV
        self.ruta_criterios = ruta_criterios or CRITERIOS_RELEVANCIA
        self.hash_pool = hash_pool
        self.docs = {(q, p): int(d) for q, p, d in
                     zip(pool_df["query_id"], pool_df["passage_id"], pool_df["doc_id"])}
        self.cargar()

    def cargar(self) -> None:
        """(Re)carga desde disco y toma la revisión vigente."""
        self.revision = leer_meta(self.ruta)["revision"]
        if self.ruta.exists():
            df = pd.read_csv(self.ruta, dtype=str, keep_default_na=False)
        else:
            df = pd.DataFrame(columns=pool.COLUMNAS_JUICIOS)
        self.df = df[pool.COLUMNAS_JUICIOS].reset_index(drop=True)

    def estado(self, q: str, pid: str) -> str | None:
        fila = self.df[(self.df["query_id"] == q) & (self.df["passage_id"] == pid)]
        return None if fila.empty else fila.iloc[0]["relevante"]

    def registrar(self, q: str, pid: str, valor: str) -> None:
        """Guarda 1, 0 u omitido (`""`) de inmediato. Lanza `ConflictoRevision` si hay edición ajena."""
        if valor not in {"0", "1", ""}:
            raise ValueError(f"Juicio inválido: {valor!r}")
        if (q, pid) not in self.docs:
            raise ValueError(f"({q}, {pid}) no pertenece al pool")
        if not criterios_listos(self.ruta_criterios):
            raise PermissionError("Falta config/criterios_relevancia.md: el alumno lo escribe y "
                                  "lo aprueba antes del primer juicio (D07).")
        df = self.df.copy()
        mascara = (df["query_id"] == q) & (df["passage_id"] == pid)
        if mascara.any():
            df.loc[mascara, "relevante"] = valor
        else:
            df.loc[len(df)] = [q, str(self.docs[(q, pid)]), pid, valor]
        self.revision = escribir_csv_atomico(self.ruta, df, self.revision,
                                             {"pool_sha256": self.hash_pool})
        self.df = df

    def progreso(self, q: str | None = None) -> tuple[int, int]:
        """`(juzgados con 0/1, total)` de una consulta o de todo el pool."""
        claves = [k for k in self.docs if q is None or k[0] == q]
        hechos = sum(1 for k in claves if self.estado(*k) in ("0", "1"))
        return hechos, len(claves)


def siguiente_pendiente(orden: list[str], estado, idx: int, saltar_actual: bool = True) -> int | None:
    """Índice del siguiente pasaje sin 0/1 después de `idx` (circular); `None` si no queda ninguno.

    `estado` es una función `passage_id -> None|""|"0"|"1"`. Con `saltar_actual` el propio `idx`
    solo se devuelve si es el único pendiente.
    """
    n = len(orden)
    for paso in range(1, n + 1):
        j = (idx + paso) % n
        if j == idx and saltar_actual and paso != n:
            continue
        if estado(orden[j]) not in ("0", "1"):
            return j
    return None


def primer_pendiente(orden: list[str], estado) -> int | None:
    """Punto de reanudación: primer pasaje del orden de presentación sin 0/1."""
    return next((i for i, p in enumerate(orden) if estado(p) not in ("0", "1")), None)


# --------------------------------------------------------------------------- estado


@dataclass
class Artefacto:
    nombre: str
    estado: str
    detalle: str
    siguiente: str


def estado_artefactos(pasajes_hashes: pd.Series | None = None) -> list[Artefacto]:
    """Un estado por artefacto; nunca "completado" por el solo hecho de que el archivo exista.

    `pasajes_hashes` = serie `passage_id -> texto_sha256` del corpus vigente (se lee si es None).
    Los artefactos de H5 a H7 todavía no tienen validador: se reportan pendientes.
    """
    filas: list[Artefacto] = []

    listos = criterios_listos(CRITERIOS_RELEVANCIA)
    filas.append(Artefacto(
        "Criterios de relevancia", "válido" if listos else "pendiente humano",
        "config/criterios_relevancia.md" + ("" if listos else " no existe"),
        "—" if listos else "Escríbelos y apruébalos antes del primer juicio"))

    if not pool.POOL_CSV.exists():
        filas.append(Artefacto("Pool de relevancia", "pendiente técnico", "falta salida/04_pool.csv",
                               "make pool"))
        return filas + _pendientes_posteriores()
    pl = pool.leer_pool()
    if pasajes_hashes is None:
        pasajes_hashes = pd.read_parquet(
            config.PASAJES_PARQUET, columns=["passage_id", "texto_sha256"]).set_index(
            "passage_id")["texto_sha256"]
    vigente = pasajes_hashes.reindex(pl["passage_id"]).to_numpy()
    n_malos = int((vigente != pl["texto_sha256"].to_numpy()).sum())
    hash_pool = adaptadores_kit.sha256_archivo(pool.POOL_CSV)
    if n_malos:
        filas.append(Artefacto("Pool de relevancia", "obsoleto",
                               f"{n_malos} pasajes con hash distinto al corpus", "make pool"))
    else:
        filas.append(Artefacto("Pool de relevancia", "válido",
                               f"{len(pl)} pares, sha256 {hash_pool[:12]}", "—"))

    filas.append(_estado_juicios(pl, pasajes_hashes, hash_pool, bool(n_malos)))
    return filas + _pendientes_posteriores()


def _estado_juicios(pl: pd.DataFrame, hashes: pd.Series, hash_pool: str, pool_obsoleto: bool,
                    ) -> Artefacto:
    nombre = "Juicios de relevancia"
    if not pool.JUICIOS_CSV.exists():
        return Artefacto(nombre, "pendiente humano", f"0 de {len(pl)} pares juzgados",
                         "Pestaña Juicios (tras aprobar los criterios)")
    meta = leer_meta(pool.JUICIOS_CSV)
    if pool_obsoleto or (meta.get("pool_sha256") and meta["pool_sha256"] != hash_pool):
        return Artefacto(nombre, "obsoleto", "el pool cambió desde que se juzgó",
                         "Revisar con el asistente; los juicios no se borran")
    pasajes = pd.DataFrame({"passage_id": hashes.index, "texto_sha256": hashes.to_numpy()})
    errores, avisos = pool.validar_juicios(pool.JUICIOS_CSV, pl, pasajes)
    if not errores:
        return Artefacto(nombre, "válido", f"{len(pl)} de {len(pl)}"
                         + (f"; {len(avisos)} aviso(s)" if avisos else ""), "make validar")
    cobertura = [e for e in errores if e.startswith("Cobertura incompleta")]
    if len(cobertura) == len(errores):
        return Artefacto(nombre, "pendiente humano", cobertura[0], "Pestaña Juicios")
    return Artefacto(nombre, "error", "; ".join(errores[:3]), "Corregir el formato (revisión humana)")


def _pendientes_posteriores() -> list[Artefacto]:
    """Artefactos de hitos posteriores: sin validador todavía, siempre pendientes."""
    return [
        Artefacto("Gazetteer extendido", "pendiente humano", "H5, sin validador aún",
                  "Pestaña Gazetteer (H5)"),
        Artefacto("Muestra y gold de evaluación", "pendiente técnico", "H5 y H6, sin validador aún",
                  "scripts/08b_muestra_gold.py (H5)"),
        Artefacto("Cierre del gold", "pendiente humano",
                  "existe" if gold_cerrado() else "no existe (modo ciego activo)", "Pestaña Gold (H6)"),
        Artefacto("Caché NER", "pendiente técnico", "H5 y H7, sin validador aún", "make ner (H5)"),
    ]
