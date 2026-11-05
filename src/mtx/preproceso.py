"""Preprocesamiento para IR (PRD §6.2, D03).

Cadena exacta: NFC y minúsculas; tokens alfanuméricos; stoplist; descarte de tokens de longitud
2 o menos salvo numéricos; stemming Snowball en español. Los pasajes se indexan con
`tokenizar_pasaje`, que solo ve el cuerpo (`texto[inicio_cuerpo:]`); las consultas con `tokenizar`.

Se usa stemming y no lematización por velocidad (127 mil pasajes), por no depender de spaCy y
porque basta para consultas cortas.

Política de tokens: `RE_TOKEN` conserva letras (con acentos y ñ), dígitos y un guion interno
(`covid-19`). Las siglas y los nombres propios no se retiran; el texto se pasa a minúsculas.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from functools import lru_cache

from nltk.stem.snowball import SnowballStemmer

from . import config

RE_TOKEN = re.compile(r"[a-záéíóúñü0-9]+(?:-[a-záéíóúñü0-9]+)?", re.IGNORECASE)

_STEMMER = SnowballStemmer("spanish")


@lru_cache(maxsize=1)
def stoplist() -> frozenset[str]:
    """Stoplist efectiva: lista de NLTK en español (copia versionada) ∪ estenográfica.

    `config/stopwords_es.txt` es una copia exacta de `nltk.corpus.stopwords.words("spanish")`
    (313 palabras): se usa siempre esta copia para que el resultado no dependa de `nltk_data`.
    """
    palabras: set[str] = set()
    for nombre in ("stopwords_es.txt", "stoplist_extra.txt"):
        texto = (config.DIR_CONFIG / nombre).read_text(encoding="utf-8")
        palabras.update(unicodedata.normalize("NFC", p.strip().lower())
                        for p in texto.splitlines() if p.strip())
    return frozenset(palabras)


@lru_cache(maxsize=1)
def hash_stoplist() -> str:
    return hashlib.sha256("\n".join(sorted(stoplist())).encode("utf-8")).hexdigest()


def configuracion_efectiva() -> dict:
    """Parámetros congelados del preprocesamiento, para el manifiesto y `tokens.parquet`."""
    return {
        "regex_token": RE_TOKEN.pattern,
        "stemmer": "SnowballStemmer('spanish')",
        "longitud_minima_no_numerica": 3,
        "stoplist_palabras": len(stoplist()),
        "stoplist_sha256": hash_stoplist(),
    }


@lru_cache(maxsize=500_000)
def _raiz(token: str) -> str:
    return _STEMMER.stem(token)


def tokenizar_sin_stem(texto: str) -> list[str]:
    """Tokens tras stoplist y filtro de longitud, sin stemming (para mostrar su efecto)."""
    paradas = stoplist()
    salida = []
    for tok in RE_TOKEN.findall(unicodedata.normalize("NFC", texto).lower()):
        if tok in paradas:
            continue
        if len(tok) <= 2 and not tok.isdigit():
            continue
        salida.append(tok)
    return salida


def tokenizar(texto: str) -> list[str]:
    """Tokens finales (con stemming). Se usa para consultas y, vía `tokenizar_pasaje`, pasajes."""
    return [_raiz(t) for t in tokenizar_sin_stem(texto)]


def tokenizar_pasaje(texto: str, inicio_cuerpo: int) -> list[str]:
    """Tokeniza solo `texto[inicio_cuerpo:]`: la marca de interlocutor no entra al índice (D03)."""
    return tokenizar(texto[inicio_cuerpo:])
