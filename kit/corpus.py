# -*- coding: utf-8 -*-
"""Carga y segmentación del corpus de conferencias matutinas (carevies/discursos_AMLO).

Uso rápido:
    from corpus import cargar_corpus, segmentar_pasajes
    df = cargar_corpus()                 # un renglón por discurso
    pasajes = segmentar_pasajes(df)      # un renglón por pasaje

El corpus se descarga una sola vez y se guarda en data/discursos.parquet.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE = DATA_DIR / "discursos.parquet"

# Columnas tal como vienen en el dataset; se renombran a nombres sin acentos.
RENOMBRES = {"título": "titulo", "titulo": "titulo", "fecha": "fecha", "texto": "texto",
             "url": "url", "loop": "loop"}


def cargar_corpus(forzar: bool = False) -> pd.DataFrame:
    """Devuelve un DataFrame con columnas doc_id, url, titulo, fecha, texto."""
    if CACHE.exists() and not forzar:
        return pd.read_parquet(CACHE)

    from datasets import load_dataset  # import tardío: solo hace falta la primera vez

    ds = load_dataset("carevies/discursos_AMLO", split="train")
    df = ds.to_pandas()
    df = df.rename(columns={c: RENOMBRES.get(c, c) for c in df.columns})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["texto"]).reset_index(drop=True)
    df.insert(0, "doc_id", range(len(df)))
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(CACHE, index=False)
    return df


# Marca de interlocutor en versiones estenográficas: línea que empieza con
# nombre en mayúsculas (con acentos) seguido de dos puntos. Ej.:
# "PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR:", "PREGUNTA:", "INTERLOCUTOR:"
RE_INTERLOCUTOR = re.compile(r"^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ ,.\-\(\)]{2,80}):\s*", re.MULTILINE)
RE_ESPACIOS = re.compile(r"[ \t]+")
RE_LINEAS = re.compile(r"\n{2,}")


def limpiar_basico(texto: str) -> str:
    """Normaliza espacios y saltos de línea. No quita marcas de interlocutor."""
    texto = texto.replace("\r", "\n")
    texto = RE_ESPACIOS.sub(" ", texto)
    texto = RE_LINEAS.sub("\n\n", texto)
    return texto.strip()


def partir_por_interlocutor(texto: str) -> list[tuple[str, str]]:
    """Parte el discurso en intervenciones: lista de (interlocutor, texto).

    Si el texto no trae marcas, regresa una sola intervención con interlocutor ''.
    """
    partes = RE_INTERLOCUTOR.split(texto)
    if len(partes) == 1:
        return [("", texto.strip())]
    intervenciones = []
    # partes = [prefacio, interlocutor1, texto1, interlocutor2, texto2, ...]
    if partes[0].strip():
        intervenciones.append(("", partes[0].strip()))
    for i in range(1, len(partes) - 1, 2):
        quien, que = partes[i].strip(), partes[i + 1].strip()
        if que:
            intervenciones.append((quien, que))
    return intervenciones


def ventanas(tokens: list[str], tam: int, paso: int) -> list[str]:
    """Ventanas deslizantes de `tam` tokens con desplazamiento `paso`."""
    if len(tokens) <= tam:
        return [" ".join(tokens)]
    out = []
    for ini in range(0, len(tokens) - tam + paso, paso):
        out.append(" ".join(tokens[ini:ini + tam]))
        if ini + tam >= len(tokens):
            break
    return out


def segmentar_pasajes(df: pd.DataFrame, tam: int = 200, paso: int = 150,
                      min_tokens: int = 40) -> pd.DataFrame:
    """Convierte discursos en pasajes.

    Estrategia por defecto: primero se parte por intervención (interlocutor), y las
    intervenciones largas se cortan en ventanas de `tam` palabras con traslape.
    Pasajes con menos de `min_tokens` palabras se descartan (saludos, "Gracias", etc.).

    Columnas de salida: passage_id, doc_id, fecha, titulo, posicion, interlocutor, texto.
    Cambiar esta estrategia (y justificarlo) es parte del examen.
    """
    filas = []
    for row in df.itertuples(index=False):
        texto = limpiar_basico(row.texto)
        pos = 0
        for quien, que in partir_por_interlocutor(texto):
            toks = que.split()
            for trozo in ventanas(toks, tam, paso):
                if len(trozo.split()) < min_tokens:
                    continue
                filas.append({
                    "passage_id": f"{row.doc_id}_{pos}",
                    "doc_id": row.doc_id,
                    "fecha": row.fecha,
                    "titulo": row.titulo,
                    "posicion": pos,
                    "interlocutor": quien,
                    "texto": trozo,
                })
                pos += 1
    return pd.DataFrame(filas)


if __name__ == "__main__":
    df = cargar_corpus()
    print(f"{len(df)} discursos; fechas {df['fecha'].min()} a {df['fecha'].max()}; "
          f"{df['fecha'].isna().sum()} sin fecha")
    print("Longitud en palabras:", df["texto"].str.split().str.len().describe().round(0).to_dict())
    p = segmentar_pasajes(df)
    print(f"{len(p)} pasajes; interlocutores más frecuentes:")
    print(p["interlocutor"].value_counts().head(10))
