"""Gold de evaluación: almacén de anotaciones, validador y cierre (PRD §6.11, D10, D15, P04, T10).

Sin Streamlit: lo usan la pestaña Gold, la CLI y `scripts/99_validar.py`. El asistente construye la
herramienta; el contenido del gold lo escribe solo el alumno desde la app. Nada aquí lee
predicciones del sistema.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mtx import config, muestreo
from mtx.app import componentes

GOLD_CSV = config.DIR_ANOTACIONES / "gold_entidades.csv"
ESTADO_CSV = config.DIR_ANOTACIONES / "estado_gold.csv"
CIERRE = componentes.CIERRE_GOLD
GOLD_RAIZ = config.RAIZ / "gold_entidades.csv"
COLUMNAS_GOLD = ["passage_id", "tipo", "texto", "inicio", "fin"]
COLUMNAS_ESTADO = ["passage_id", "texto_sha256", "estado", "n_entidades", "revision"]
TIPOS = ("PER", "ORG", "LOC", "FECHA", "MONTO")
CONTEXTO = 40
PUNTUACION_FINAL = '.,;:!?)"»'
ETIQUETA_CONGELADA = "reglas-congeladas"


# --------------------------------------------------------------------------- búsqueda de spans


@dataclass(frozen=True)
class Ocurrencia:
    inicio: int
    fin: int
    antes: str
    despues: str


def buscar_ocurrencias(texto: str, buscado: str, contexto: int = CONTEXTO) -> list[Ocurrencia]:
    """Todas las apariciones exactas de `buscado` (`str.find` iterado, con solapes) y su contexto."""
    if not buscado:
        return []
    res, i = [], texto.find(buscado)
    while i != -1:
        f = i + len(buscado)
        res.append(Ocurrencia(i, f, texto[max(0, i - contexto):i], texto[f:f + contexto]))
        i = texto.find(buscado, i + 1)
    return res


def tokens(texto: str) -> list[tuple[int, int, str]]:
    """Tokens por espacios con offsets reales (modo secundario de selección)."""
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", texto)]


def span_de_tokens(texto: str, toks: list[tuple[int, int, str]], i: int, j: int,
                   recortar: bool = True) -> tuple[int, int]:
    """Span del token `i` al `j` (inclusivos); recorta la puntuación final sin quitar `$`."""
    if not 0 <= i <= j < len(toks):
        raise ValueError("Tokens fuera de rango o en orden inverso")
    ini, fin = toks[i][0], toks[j][1]
    if recortar:
        while fin > ini + 1 and texto[fin - 1] in PUNTUACION_FINAL:
            fin -= 1
        while ini < fin - 1 and texto[ini] in '("«¿¡':
            ini += 1
    return ini, fin


# --------------------------------------------------------------------------- validación de filas


def problemas_fila(texto: str, fila: dict, otras: list[dict]) -> list[str]:
    """Errores que impiden agregar `fila` (invariante, tipo, duplicado, anidamiento)."""
    err = []
    ini, fin, tipo = int(fila["inicio"]), int(fila["fin"]), fila["tipo"]
    if tipo not in TIPOS:
        err.append(f"Tipo inválido: {tipo}")
    if not 0 <= ini < fin <= len(texto):
        return err + [f"Offsets fuera del pasaje: ({ini}, {fin})"]
    if texto[ini:fin] != fila["texto"]:
        err.append("El texto no coincide con texto[inicio:fin]")
    if not fila["texto"].strip():
        err.append("Texto vacío")
    for o in otras:
        oi, of = int(o["inicio"]), int(o["fin"])
        if (oi, of, o["tipo"]) == (ini, fin, tipo):
            err.append("Duplicado: ya existe esa entidad")
        elif (oi <= ini and fin <= of) or (ini <= oi and of <= fin):
            err.append(f"Anidada con {o['tipo']} «{o['texto']}» ({oi}, {of})")
    return err


# --------------------------------------------------------------------------- almacén


class AlmacenGold:
    """Lectura y escritura de `gold_entidades.csv` y `estado_gold.csv` para una sesión.

    Cada cambio se guarda de inmediato con escritura atómica, respaldo y revisión; una edición
    desde otra pestaña provoca `componentes.ConflictoRevision`.
    """

    def __init__(self, muestra: pd.DataFrame, textos: dict[str, str], ruta_gold: Path = GOLD_CSV,
                 ruta_estado: Path = ESTADO_CSV, ruta_cierre: Path = CIERRE):
        self.muestra = muestra
        self.textos = textos
        self.ruta_gold, self.ruta_estado, self.ruta_cierre = ruta_gold, ruta_estado, ruta_cierre
        self.hash_de = dict(zip(muestra["passage_id"], muestra["texto_sha256"], strict=True))
        self.cargar()

    def cargar(self) -> None:
        self.rev_gold = componentes.leer_meta(self.ruta_gold)["revision"]
        self.rev_estado = componentes.leer_meta(self.ruta_estado)["revision"]
        self.gold = (pd.read_csv(self.ruta_gold, dtype={"passage_id": str}, keep_default_na=False)
                     if self.ruta_gold.exists() else pd.DataFrame(columns=COLUMNAS_GOLD))
        self.gold = self.gold[COLUMNAS_GOLD].reset_index(drop=True)
        if self.ruta_estado.exists():
            self.estado_df = pd.read_csv(self.ruta_estado, dtype={"passage_id": str})
        else:
            self.estado_df = pd.DataFrame({
                "passage_id": self.muestra["passage_id"], "texto_sha256": self.muestra[
                    "texto_sha256"], "estado": "pendiente", "n_entidades": 0, "revision": 0})
        self.estado_df = self.estado_df[COLUMNAS_ESTADO].reset_index(drop=True)

    def _comprobar_abierto(self) -> None:
        if self.ruta_cierre.exists():
            raise PermissionError("El gold está cerrado: un cambio exige revisión explícita del "
                                  "alumno con motivo y nueva versión (PRD §6.11).")

    def entidades(self, pid: str) -> list[dict]:
        df = self.gold[self.gold["passage_id"] == pid]
        return df.sort_values(["inicio", "fin"]).to_dict("records")

    def estado(self, pid: str) -> str:
        fila = self.estado_df[self.estado_df["passage_id"] == pid]
        return "pendiente" if fila.empty else str(fila.iloc[0]["estado"])

    def _guardar(self, gold: pd.DataFrame, pid: str, estado: str | None = None) -> None:
        gold = gold.sort_values(["passage_id", "inicio", "fin", "tipo"]).reset_index(drop=True)
        est = self.estado_df.copy()
        m = est["passage_id"] == pid
        est.loc[m, "n_entidades"] = int((gold["passage_id"] == pid).sum())
        est.loc[m, "revision"] = est.loc[m, "revision"].astype(int) + 1
        if estado is not None:
            est.loc[m, "estado"] = estado
        self.rev_gold = componentes.escribir_csv_atomico(self.ruta_gold, gold, self.rev_gold)
        self.rev_estado = componentes.escribir_csv_atomico(self.ruta_estado, est, self.rev_estado)
        self.gold, self.estado_df = gold, est

    def agregar(self, pid: str, tipo: str, inicio: int, fin: int) -> None:
        """Agrega una entidad elegida por el alumno; lanza ValueError con los problemas."""
        self._comprobar_abierto()
        texto = self.textos[pid]
        fila = {"passage_id": pid, "tipo": tipo, "texto": texto[inicio:fin], "inicio": int(inicio),
                "fin": int(fin)}
        errores = problemas_fila(texto, fila, self.entidades(pid))
        if errores:
            raise ValueError("; ".join(errores))
        gold = pd.concat([self.gold, pd.DataFrame([fila])], ignore_index=True)
        # Agregar reabre el pasaje: el alumno vuelve a marcarlo revisado completo.
        self._guardar(gold, pid, "en_progreso")

    def borrar(self, pid: str, tipo: str, inicio: int, fin: int) -> None:
        self._comprobar_abierto()
        m = ((self.gold["passage_id"] == pid) & (self.gold["tipo"] == tipo)
             & (self.gold["inicio"].astype(int) == inicio) & (self.gold["fin"].astype(int) == fin))
        if not m.any():
            raise KeyError("No existe esa entidad")
        self._guardar(self.gold[~m], pid, "en_progreso")

    def cerrar_pasaje(self, pid: str) -> None:
        """'Pasaje revisado completo'; válido con cero entidades (P04)."""
        self._comprobar_abierto()
        self._guardar(self.gold, pid, "cerrado")

    def progreso(self, ids: list[str] | None = None) -> tuple[int, int]:
        ids = list(self.muestra["passage_id"]) if ids is None else ids
        return sum(self.estado(p) == "cerrado" for p in ids), len(ids)


# --------------------------------------------------------------------------- validador


def _commits(ruta: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "log", "--format=%H", "--", str(ruta)], cwd=config.RAIZ,
                             capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return []
    return out


def etiqueta_precede_gold(rutas: list[Path]) -> tuple[bool, str]:
    """La etiqueta `reglas-congeladas` es ancestro del primer commit de cada archivo gold."""
    try:
        subprocess.run(["git", "rev-parse", "--verify", f"{ETIQUETA_CONGELADA}^{{commit}}"],
                       cwd=config.RAIZ, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False, f"No existe la etiqueta {ETIQUETA_CONGELADA}"
    for ruta in rutas:
        commits = _commits(ruta)
        if not commits:
            continue  # aún sin commit: se comprobará cuando exista
        primero = commits[-1]
        r = subprocess.run(["git", "merge-base", "--is-ancestor", ETIQUETA_CONGELADA, primero],
                           check=False, cwd=config.RAIZ, capture_output=True)
        if r.returncode != 0:
            return False, f"{ruta.name}: su primer commit no desciende de {ETIQUETA_CONGELADA}"
    return True, ""


def validar_gold(muestra: pd.DataFrame, textos: dict[str, str], ruta_gold: Path = GOLD_CSV,
                 ruta_estado: Path = ESTADO_CSV, comprobar_git: bool = True,
                 n_esperado: int = 20, por_consulta: int = 2) -> tuple[list[str], list[str]]:
    """(errores, avisos) del gold; sin errores el gold puede cerrarse y exportarse."""
    errores, avisos = [], []
    ids = list(muestra["passage_id"])
    if len(ids) != n_esperado or len(set(ids)) != n_esperado:
        errores.append(f"El manifiesto debe tener {n_esperado} IDs distintos (tiene {len(set(ids))})")
    cuenta = muestra.groupby("query_id").size()
    malas = cuenta[cuenta != por_consulta]
    if not malas.empty:
        errores.append(f"Consultas sin exactamente {por_consulta} pasajes: {list(malas.index)}")
    for pid, h in zip(muestra["passage_id"], muestra["texto_sha256"], strict=True):
        if hashlib.sha256(textos[pid].encode("utf-8")).hexdigest() != h:
            errores.append(f"{pid}: el hash del texto ya no coincide con el manifiesto")

    if not ruta_estado.exists():
        errores.append("Falta anotaciones/estado_gold.csv")
    else:
        est = pd.read_csv(ruta_estado, dtype={"passage_id": str}).set_index("passage_id")
        abiertos = [p for p in ids if p not in est.index or est.at[p, "estado"] != "cerrado"]
        if abiertos:
            errores.append(f"Pasajes sin cerrar: {len(abiertos)} de {len(ids)}")

    if ruta_gold.exists():
        gold = pd.read_csv(ruta_gold, dtype={"passage_id": str}, keep_default_na=False)
        if list(gold.columns) != COLUMNAS_GOLD:
            errores.append(f"Columnas del gold: {list(gold.columns)} (esperadas {COLUMNAS_GOLD})")
        else:
            fuera = set(gold["passage_id"]) - set(ids)
            if fuera:
                errores.append(f"Filas de pasajes fuera de la muestra: {sorted(fuera)}")
            for f in gold.itertuples(index=False):
                if f.passage_id not in textos:
                    continue
                t = textos[f.passage_id]
                ini, fin = int(f.inicio), int(f.fin)
                if f.tipo not in TIPOS:
                    errores.append(f"{f.passage_id}: tipo inválido {f.tipo}")
                if not f.texto.strip():
                    errores.append(f"{f.passage_id}: fila con texto vacío")
                if not (0 <= ini < fin <= len(t)) or t[ini:fin] != f.texto:
                    errores.append(f"{f.passage_id}: offsets rotos en «{f.texto}» ({ini}, {fin})")
            if gold.duplicated(["passage_id", "tipo", "inicio", "fin"]).any():
                errores.append("Hay filas duplicadas (passage_id, tipo, inicio, fin)")
            vacios = [p for p in ids if p not in set(gold["passage_id"])]
            if vacios:
                avisos.append(f"{len(vacios)} pasaje(s) cerrados con cero entidades: el evaluador "
                              "oficial no los cuenta (P04); van a la evaluación de 20 IDs")
    if comprobar_git:
        ok, motivo = etiqueta_precede_gold([ruta_gold, ruta_estado])
        if not ok:
            errores.append(motivo)
    return errores, avisos


def cerrar_gold(muestra: pd.DataFrame, textos: dict[str, str], ruta_gold: Path = GOLD_CSV,
                ruta_estado: Path = ESTADO_CSV, ruta_cierre: Path = CIERRE,
                ruta_muestra: Path = muestreo.MUESTRA_GOLD, **kw) -> dict:
    """Escribe `cierre_gold.json` solo si `validar_gold()` pasa; desde ahí se levanta el modo ciego."""
    errores, avisos = validar_gold(muestra, textos, ruta_gold, ruta_estado, **kw)
    if errores:
        raise ValueError("No se puede cerrar el gold: " + "; ".join(errores))

    def sha(r: Path) -> str:
        return hashlib.sha256(r.read_bytes()).hexdigest() if r.exists() else ""

    cierre = {
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sha256_muestra": sha(ruta_muestra), "sha256_gold": sha(ruta_gold),
        "sha256_estado": sha(ruta_estado), "sha256_protocolo": sha(muestreo.PROTOCOLO),
        "textos_sha256": dict(zip(muestra["passage_id"], muestra["texto_sha256"], strict=True)),
        "avisos": avisos,
    }
    ruta_cierre.parent.mkdir(parents=True, exist_ok=True)
    ruta_cierre.write_text(json.dumps(cierre, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    return cierre


def exportar_gold(origen: Path = GOLD_CSV, destino: Path = GOLD_RAIZ) -> None:
    """Copia validada a la raíz (UTF-8 sin BOM, `\\n`)."""
    destino.write_bytes(origen.read_bytes())
