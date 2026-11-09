"""Hoja de cálculo para repartir juicios de relevancia entre compañeros (trabajo colaborativo).

`generar()` escribe un .xlsx con una pestaña por consulta pendiente: consulta, pregunta, criterio,
una celda para el nombre del anotador y una fila por pasaje con una columna `relevante` vacía.
La hoja es ciega al modelo: no incluye variantes, rangos, puntajes ni `en_ventana`. Nunca
precarga un valor. `leer()` recupera lo que llenaron para que `scripts/importar_juicios_hoja.py`
lo valide y lo registre con el almacén de la app (escritura atómica y gate de criterios).

Este módulo no produce ni sugiere juicios: solo mueve los que escriben las personas.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from . import pool

FILA_ANOTADOR = 5
FILA_ENCABEZADO = 7
ENCABEZADOS = ["orden", "passage_id", "doc_id", "titulo", "interlocutor", "fecha", "texto",
               "relevante"]
COL_RELEVANTE = 8
INSTRUCCION = ("Escribe 1 si el pasaje es relevante y 0 si no lo es. Si no lo juzgas, déjalo "
               "vacío. Lee el pasaje completo; la fecha y el modelo no cuentan.")


def consultas_pendientes(pool_df: pd.DataFrame, juicios: pd.DataFrame) -> list[str]:
    """Consultas con al menos un par sin 0/1 (la hoja no revela los juicios ya hechos)."""
    validos = {(q, p) for q, p, v in zip(juicios["query_id"], juicios["passage_id"],
                                         juicios["relevante"], strict=True) if v in ("0", "1")}
    return [q for q in dict.fromkeys(pool_df["query_id"])
            if any((q, p) not in validos for p in pool_df[pool_df["query_id"] == q]["passage_id"])]


def generar(destino: Path, pool_df: pd.DataFrame, cons: pd.DataFrame, meta: pd.DataFrame,
            criterios: str, consultas: list[str]) -> Path:
    """Escribe el libro. `meta` trae `titulo` e `interlocutor` indexado por `passage_id`."""
    orden = pool.orden_presentacion(pool_df)
    wb = Workbook()
    wb.remove(wb.active)
    gris = PatternFill("solid", fgColor="E5E7EB")
    for q in consultas:
        ws = wb.create_sheet(q)
        c = cons.set_index("query_id").loc[q]
        ws["A1"], ws["A1"].font = f"{q}: {c['consulta']}", Font(bold=True, size=14)
        ws["A2"] = f"Pregunta de extracción (ayuda): {c['pregunta_extraccion']}"
        ws["A3"] = "Criterio: " + " ".join(criterios.replace("# Criterios de relevancia", "").split())
        ws["A4"] = INSTRUCCION
        ws["A4"].font = Font(bold=True)
        ws[f"A{FILA_ANOTADOR}"], ws[f"B{FILA_ANOTADOR}"] = "Anotador (tu nombre):", None
        ws[f"B{FILA_ANOTADOR}"].fill = PatternFill("solid", fgColor="FEF3C7")
        for i, h in enumerate(ENCABEZADOS, start=1):
            celda = ws.cell(row=FILA_ENCABEZADO, column=i, value=h)
            celda.font, celda.fill = Font(bold=True), gris
        g = pool_df[pool_df["query_id"] == q].set_index("passage_id")
        for n, pid in enumerate(orden[q], start=1):
            fila = FILA_ENCABEZADO + n
            valores = [n, pid, int(g.loc[pid, "doc_id"]), meta.loc[pid, "titulo"],
                       meta.loc[pid, "interlocutor"], g.loc[pid, "fecha"] or "desconocida",
                       g.loc[pid, "texto"], None]
            for col, v in enumerate(valores, start=1):
                celda = ws.cell(row=fila, column=col, value=v)
                if isinstance(v, str):
                    celda.data_type = "s"  # texto literal: nada se interpreta como fórmula o fecha
                celda.alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=fila, column=COL_RELEVANTE).fill = PatternFill("solid", fgColor="FEF3C7")
        ultima = FILA_ENCABEZADO + len(orden[q])
        validacion = DataValidation(type="list", formula1='"1,0"', allow_blank=True,
                                    showErrorMessage=True, errorTitle="Valor no válido",
                                    error="Solo 1 (relevante) o 0 (no relevante); vacío = sin juzgar.")
        ws.add_data_validation(validacion)
        validacion.add(f"H{FILA_ENCABEZADO + 1}:H{ultima}")
        for col, ancho in zip("ABCDEFGH", (7, 11, 8, 30, 24, 12, 110, 11), strict=True):
            ws.column_dimensions[col].width = ancho
        ws.freeze_panes = f"A{FILA_ENCABEZADO + 1}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)
    return destino


def leer(ruta: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Lee un libro descargado: DataFrame `query_id, passage_id, doc_id, relevante` y anotadores.

    `relevante` queda como `"1"`, `"0"`, `""` (sin juzgar) o el texto literal si es inválido
    (para que el validador lo reporte). Las pestañas que no son una consulta se ignoran.
    """
    wb = load_workbook(ruta, data_only=True)
    filas, anotadores = [], {}
    for ws in wb.worksheets:
        if not ws.title.startswith("Q"):
            continue
        anotadores[ws.title] = str(ws.cell(row=FILA_ANOTADOR, column=2).value or "").strip()
        if [ws.cell(row=FILA_ENCABEZADO, column=i).value for i in range(1, 9)] != ENCABEZADOS:
            raise ValueError(f"Pestaña {ws.title}: encabezados distintos a los esperados")
        for r in range(FILA_ENCABEZADO + 1, ws.max_row + 1):
            pid = ws.cell(row=r, column=2).value
            if pid is None:
                continue
            filas.append({"query_id": ws.title, "passage_id": str(pid).strip(),
                          "doc_id": _entero(ws.cell(row=r, column=3).value),
                          "relevante": _normalizar(ws.cell(row=r, column=COL_RELEVANTE).value)})
    return pd.DataFrame(filas, columns=pool.COLUMNAS_JUICIOS[:1] + ["passage_id", "doc_id",
                                                                    "relevante"]), anotadores


def _entero(v) -> str:
    """`doc_id` tras pasar por Sheets puede llegar como 253.0: se devuelve `"253"`."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v).strip()
    return str(int(f)) if f == int(f) else str(v).strip()


def _normalizar(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, (int, float)) and float(v) in (0.0, 1.0):
        return str(int(v))
    return str(v).strip()


def revisar(hoja: pd.DataFrame, anotadores: dict[str, str], pool_df: pd.DataFrame) -> list[str]:
    """Errores que impiden importar (la hoja no se importa a medias)."""
    errores = []
    en_pool = {(q, p): str(d) for q, p, d in zip(pool_df["query_id"], pool_df["passage_id"],
                                                 pool_df["doc_id"], strict=True)}
    for q, nombre in anotadores.items():
        if not nombre:
            errores.append(f"{q}: falta el nombre del anotador (celda B{FILA_ANOTADOR})")
    for f in hoja.itertuples(index=False):
        esperado = en_pool.get((f.query_id, f.passage_id))
        if esperado is None:
            errores.append(f"Par fuera del pool: {f.query_id} {f.passage_id}")
        elif esperado != f.doc_id:
            errores.append(f"doc_id incoherente en {f.query_id} {f.passage_id}: {f.doc_id}")
        if f.relevante not in ("0", "1", ""):
            errores.append(f"Valor inválido {f.relevante!r} en {f.query_id} {f.passage_id}")
    claves = list(zip(hoja["query_id"], hoja["passage_id"], strict=True))
    errores += [f"Fila repetida: {q} {p}" for q, p in sorted({k for k in claves if claves.count(k) > 1})]
    return errores
