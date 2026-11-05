"""Único punto de contacto con el kit del profesor (`kit/`).

Ningún otro módulo de `mtx` importa de `kit/`. El kit no se edita nunca: cualquier ajuste
vive aquí como adaptador (PRD §0.2 regla 5, §9).

- `cargar_modulo_corpus()` importa `kit/corpus.py` por ruta, sin tocar `sys.path`.
- `ejecutar_evaluador()` corre `kit/evaluar.py` tal cual como subproceso. El evaluador escribe
  `resultados_ir.csv` o `resultados_ie.csv` en el directorio actual y no admite otra ruta de
  salida, así que se ejecuta con `cwd` en el directorio de destino.
- `verificar_hashes()` compara los archivos del kit con los SHA-256 de `docs/contratos_kit.md`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
DIR_KIT = RAIZ / "kit"
DOC_CONTRATOS = RAIZ / "docs" / "contratos_kit.md"

ARCHIVOS_KIT = ("corpus.py", "consultas.csv", "gazetteer_dependencias.csv", "evaluar.py")
"""Los cuatro archivos que el PRD §3 exige conservar idénticos."""

SALIDAS_EVALUADOR = {"ir": "resultados_ir.csv", "ie": "resultados_ie.csv"}


def cargar_modulo_corpus(dir_kit: Path = DIR_KIT) -> ModuleType:
    """Importa `kit/corpus.py` como módulo `kit_corpus`, sin modificar `sys.path`."""
    spec = importlib.util.spec_from_file_location("kit_corpus", dir_kit / "corpus.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def ejecutar_evaluador(modo: str, referencia: Path, prediccion: Path, destino: Path,
                       dir_kit: Path = DIR_KIT) -> Path:
    """Ejecuta `kit/evaluar.py ir|ie` y devuelve la ruta del CSV de resultados en `destino`.

    `referencia` son los juicios (modo `ir`) o el gold (modo `ie`); `prediccion` es
    `ranking.csv` o `entidades.csv`. Lanza `RuntimeError` con la salida del evaluador si falla.
    """
    if modo not in SALIDAS_EVALUADOR:
        raise ValueError(f"Modo desconocido: {modo!r}; use 'ir' o 'ie'")
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    proceso = subprocess.run(
        [sys.executable, str(dir_kit / "evaluar.py"), modo,
         str(Path(referencia).resolve()), str(Path(prediccion).resolve())],
        cwd=destino, capture_output=True, text=True, check=False,
    )
    if proceso.returncode != 0:
        raise RuntimeError(f"evaluar.py {modo} falló (código {proceso.returncode}):\n"
                           f"{proceso.stderr[-2000:]}")
    return destino / SALIDAS_EVALUADOR[modo]


def sha256_archivo(ruta: Path) -> str:
    """SHA-256 hexadecimal del contenido de un archivo."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def hashes_registrados(doc: Path = DOC_CONTRATOS) -> dict[str, str]:
    """Lee de `docs/contratos_kit.md` las líneas `<sha256>  kit/<archivo>` del bloque de hashes."""
    patron = re.compile(r"^([0-9a-f]{64})\s+(?:kit/)?([\w.\-]+)\s*$", re.MULTILINE)
    return {nombre: h for h, nombre in patron.findall(doc.read_text(encoding="utf-8"))}


def verificar_hashes(dir_kit: Path = DIR_KIT, doc: Path = DOC_CONTRATOS) -> list[str]:
    """Devuelve la lista de problemas (vacía si el kit sigue idéntico a los originales)."""
    registrados = hashes_registrados(doc)
    problemas = []
    for nombre in ARCHIVOS_KIT:
        ruta = dir_kit / nombre
        if nombre not in registrados:
            problemas.append(f"{nombre}: sin hash registrado en {doc.name}")
        elif not ruta.exists():
            problemas.append(f"{nombre}: falta en {dir_kit}")
        elif sha256_archivo(ruta) != registrados[nombre]:
            problemas.append(f"{nombre}: el hash no coincide con el original")
    return problemas
