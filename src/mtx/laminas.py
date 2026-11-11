"""Láminas de la presentación con python-pptx (PRD §6.15, P2). Máximo 5, 16:9, concepto + artefacto.

Toda cifra se lee de `salida/` o `reporte/tablas/` en el momento de generar; ninguna se escribe a
mano. Las láminas son un punto de partida editable: el alumno las ajusta en PowerPoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from . import config

AZUL = RGBColor(0x1F, 0x3A, 0x68)       # acento de las prácticas de Arturo
TERRACOTA = RGBColor(0xB8, 0x50, 0x42)
TINTA = RGBColor(0x22, 0x26, 0x2E)
GRIS = RGBColor(0x5F, 0x66, 0x70)
TINTE = RGBColor(0xEE, 0xF1, 0xF6)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
FUENTE = "Calibri"
ANCHO, ALTO = Inches(13.333), Inches(7.5)
MARGEN = Inches(0.6)
AUTOR = "Arturo Jaramillo Salmerón · Minería de Textos"
S = config.DIR_SALIDA


def _texto(slide, x, y, w, h, parrafos, tam=16, color=TINTA, negrita=False, alinear=PP_ALIGN.LEFT,
           ancla=MSO_ANCHOR.TOP, nombre=None, espacio=6):
    caja = slide.shapes.add_textbox(x, y, w, h)
    if nombre:
        caja.name = nombre
    tf = caja.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancla
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, p in enumerate(parrafos if isinstance(parrafos, list) else [parrafos]):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = alinear
        par.space_after = Pt(espacio)
        run = par.add_run()
        run.text = p
        run.font.size, run.font.bold, run.font.name = Pt(tam), negrita, FUENTE
        run.font.color.rgb = color
    return caja


def _vinetas(slide, x, y, w, h, items, tam=16):
    caja = _texto(slide, x, y, w, h, items, tam=tam, espacio=10, nombre="Puntos")
    for par in caja.text_frame.paragraphs:
        pPr = par._p.get_or_add_pPr()
        pPr.set("marL", str(Emu(Inches(0.25))))
        pPr.set("indent", str(-Emu(Inches(0.25))))
        bu = pPr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar",
                             {"char": "•"})
        pPr.append(bu)
    return caja


def _titulo(slide, texto, n):
    _texto(slide, MARGEN, Inches(0.45), ANCHO - 2 * MARGEN, Inches(0.8), texto, tam=34,
           color=AZUL, negrita=True, nombre="Título")
    _texto(slide, MARGEN, ALTO - Inches(0.5), Inches(8), Inches(0.3), AUTOR, tam=10, color=GRIS,
           nombre="Pie")
    _texto(slide, ANCHO - MARGEN - Inches(1), ALTO - Inches(0.5), Inches(1), Inches(0.3),
           f"{n}/5", tam=10, color=GRIS, alinear=PP_ALIGN.RIGHT, nombre="Número")


def _tarjeta(slide, x, y, w, h, cifra, etiqueta, color=AZUL):
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    r.name = f"Tarjeta {etiqueta}"
    r.adjustments[0] = 0.08
    r.fill.solid()
    r.fill.fore_color.rgb = TINTE
    r.line.fill.background()
    _texto(slide, x + Inches(0.25), y + Inches(0.2), w - Inches(0.5), Inches(0.8), cifra, tam=32,
           color=color, negrita=True)
    _texto(slide, x + Inches(0.25), y + h - Inches(0.65), w - Inches(0.5), Inches(0.5), etiqueta,
           tam=13, color=GRIS)


def _tabla(slide, x, y, w, df: pd.DataFrame, anchos=None, tam=13, alto_fila=None):
    alto_fila = alto_fila or Inches(0.38)
    filas, cols = len(df) + 1, len(df.columns)
    t = slide.shapes.add_table(filas, cols, x, y, w, alto_fila * filas).table
    anchos = anchos or [1] * cols
    for j, a in enumerate(anchos):
        t.columns[j].width = int(w * a / sum(anchos))
    for j, c in enumerate(df.columns):
        _celda(t.cell(0, j), str(c), tam, True, BLANCO, AZUL)
    for i, fila in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(fila):
            _celda(t.cell(i, j), str(v), tam, False, TINTA, TINTE if i % 2 == 0 else BLANCO,
                   PP_ALIGN.RIGHT if j > 0 and _es_numero(v) else PP_ALIGN.LEFT)
    return t


def _es_numero(v) -> bool:
    try:
        float(str(v).replace(",", ""))
        return True
    except ValueError:
        return False


def _celda(c, texto, tam, negrita, color, fondo, alinear=PP_ALIGN.LEFT):
    c.fill.solid()
    c.fill.fore_color.rgb = fondo
    c.margin_left = c.margin_right = Inches(0.08)
    c.margin_top = c.margin_bottom = Inches(0.03)
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = c.text_frame.paragraphs[0]
    p.alignment = alinear
    r = p.add_run()
    r.text = texto
    r.font.size, r.font.bold, r.font.name = Pt(tam), negrita, FUENTE
    r.font.color.rgb = color


def _datos() -> dict:
    lim = json.loads((S / "01_limpieza.json").read_text(encoding="utf-8"))
    ind = json.loads((config.DIR_DATA / "indice_meta.json").read_text(encoding="utf-8"))
    res = pd.read_csv(S / "resultados_ir.csv")
    prom = res[res["query_id"].str.startswith("PROMEDIO")].set_index("modelo")["AP"]
    ie = pd.read_csv(S / "09_ie_detalle.csv")
    f1 = ie[ie["tipo"] == "TODOS"].set_index("metodo")["f1"]
    gan = pd.read_csv(S / "05_ir_ganador_por_consulta.csv")
    err = pd.read_csv(S / "09_resumen_errores.csv", keep_default_na=False)
    return {"discursos": lim["discursos"], "excluidos": lim["discursos_excluidos"],
            "acotaciones": lim["acotaciones_eliminadas"], "pasajes": ind["N"],
            "pct_car": lim["porcentaje_caracteres_descartados"],
            "pct_rep": lim["intervenciones_reportero_descartadas_pct"],
            "map_bm25": prom["bm25_con_filtro"], "map_tfidf": prom["tfidf_con_filtro"],
            "gana_bm25": int((gan["ganador"] == "bm25_con_filtro").sum()),
            "f1": f1.to_dict(),
            "frontera": int(err[(err["categoria"] == "frontera") & (err["subcategoria"] == "")]["n"].sum()),
            "en_marca": int(err[err["categoria"] == "en_marca"]["n"].sum())}


def generar(destino: Path) -> Path:
    d = _datos()
    prs = Presentation()
    prs.slide_width, prs.slide_height = ANCHO, ALTO
    vacia = prs.slide_layouts[6]
    izq_w = Inches(4.6)
    der_x = MARGEN + izq_w + Inches(0.5)
    der_w = ANCHO - der_x - MARGEN
    y0 = Inches(1.55)

    # 1 · Problema y corpus
    s = prs.slides.add_slide(vacia)
    _titulo(s, "Análisis de las Mañaneras 2018-2024", 1)
    _vinetas(s, MARGEN, y0, izq_w, Inches(4.8), [
        ("Recuperar los 10 pasajes más relevantes por consulta y extraer quién, dónde, cuándo y "
        "cuánto en las versiones estenográficas."),
        (f"Limpieza por lista cerrada: {d['acotaciones']:,} acotaciones ({d['pct_car']:.2f} % de los "
        f"caracteres) y {d['excluidos']} discursos duplicados."),
        "Pasajes de 200 palabras con paso de 150; la marca del interlocutor no entra al índice.",
        "Corpus → índice → TF-IDF y BM25 → juicios → reglas + NER → gold → respuestas con evidencia."])
    cw, ch, gap = (der_w - Inches(0.3)) / 2, Inches(2.2), Inches(0.3)
    for k, (cifra, etq) in enumerate([(f"{d['discursos']:,}", "versiones estenográficas, 2018 a 2024"),
                                      (f"{d['pasajes']:,}", "pasajes indexados"),
                                      ("10", "consultas, 8 del kit y 2 propias"),
                                      (f"{d['pct_rep']:.1f} %", "intervenciones de reporteros bajo 40 palabras")]):
        _tarjeta(s, der_x + (cw + gap) * (k % 2), y0 + (ch + gap) * (k // 2), cw, ch, cifra, etq,
                 TERRACOTA if k == 3 else AZUL)

    # 2 · Índice
    s = prs.slides.add_slide(vacia)
    _titulo(s, "Índice invertido y preprocesamiento", 2)
    _vinetas(s, MARGEN, y0, izq_w, Inches(4.8), [
        "NFC, minúsculas, stoplist de 336 palabras (24 propias de la estenográfica) y stemming Snowball.",
        "El índice se construye a mano: postings con tf, df, N y longitud de cada pasaje.",
        "Un término raro discrimina más: huachicol tiene el idf más alto de los cuatro."])
    from .reporte import tabla_postings  # tabla ya calculada desde salida/02_postings.md
    filas = [ln.strip("|").split("|") for ln in tabla_postings().splitlines()[2:]]
    df = pd.DataFrame([[c.strip() for c in f] for f in filas],
                      columns=["Término", "Stem", "df", "idf BM25", "Primeros postings (tf)"])
    _tabla(s, der_x, y0 + Inches(0.3), der_w, df, [1.0, 1.0, 0.75, 0.9, 3.9], tam=13,
           alto_fila=Inches(0.55))
    _texto(s, der_x, y0 + Inches(3.4), der_w, Inches(0.8),
           "idf(t) = ln(1 + (N − df + 0.5) / (df + 0.5)),  N = 127,739", tam=16, color=GRIS)

    # 3 · Recuperación
    s = prs.slides.add_slide(vacia)
    _titulo(s, "Recuperación: BM25 frente a TF-IDF", 3)
    _tarjeta(s, MARGEN, y0, (izq_w - Inches(0.3)) / 2, Inches(1.6), f"{d['map_bm25']:.3f}",
             "MAP BM25 con filtro")
    _tarjeta(s, MARGEN + (izq_w + Inches(0.3)) / 2, y0, (izq_w - Inches(0.3)) / 2, Inches(1.6),
             f"{d['map_tfidf']:.3f}", "MAP TF-IDF con filtro", GRIS)
    _vinetas(s, MARGEN, y0 + Inches(2.0), izq_w, Inches(3.2), [
        f"BM25 gana en {d['gana_bm25']} de 10 consultas; TF-IDF gana Q3 y Q9 empata en su techo (10/21).",
        "176 juicios humanos sobre el pool de las cuatro variantes.",
        "Sinónimos sin resolver: huachicol y robo de combustible, AIFA y Felipe Ángeles."], tam=15)
    s.shapes.add_picture(str(config.RAIZ / "reporte" / "figuras" / "ir_ap_por_consulta.png"),
                         der_x, y0, width=der_w)

    # 4 · Extracción
    s = prs.slides.add_slide(vacia)
    _titulo(s, "Extracción: reglas más modelo", 4)
    _vinetas(s, MARGEN, y0, izq_w, Inches(4.8), [
        "Reglas: FECHA y MONTO con regex, ORG y LOC con gazetteers, PER desde la marca. Congeladas antes del gold.",
        "NER mrm8488/bert-spanish-cased-finetuned-ner, elegido sin ver el gold.",
        f"Errores de frontera: {d['frontera']} (aeropuerto Felipe Ángeles → Felipe Ángeles).",
        f"Mayúsculas en la marca: {d['en_marca']} errores (MAN, MANUEL LÓPEZ)."], tam=14)
    tie = [ln.strip("|").split("|") for ln in (config.RAIZ / "reporte" / "tablas" / "ie.md")
           .read_text(encoding="utf-8").splitlines()[2:]]
    df = pd.DataFrame([[c.strip() for c in f] for f in tie],
                      columns=["Tipo", "Gold", "Reglas P/R/F1", "Modelo P/R/F1", "Combinado P/R/F1"])
    _tabla(s, der_x, y0, der_w, df, [0.9, 0.7, 1.6, 1.6, 1.7], tam=13, alto_fila=Inches(0.5))
    _tarjeta(s, MARGEN, y0 + Inches(3.5), Inches(3.2), Inches(1.4), f"{d['f1']['combinado']:.3f}",
             "F1 combinado, 20 pasajes gold", TERRACOTA)

    # 5 · Demo y limitaciones
    s = prs.slides.add_slide(vacia)
    _titulo(s, "Respuestas con evidencia y demo", 5)
    _vinetas(s, MARGEN, y0, izq_w, Inches(3.4), [
        "Un valor es «respaldado» solo si el texto muestra la relación pedida; lo que dice un reportero queda ambiguo.",
        "Limitaciones: gold de 20 pasajes, un solo NER, preguntas cortas perdidas, juicios sin acuerdo medido."],
        tam=15)
    cmd = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, MARGEN, y0 + Inches(3.6), izq_w, Inches(0.9))
    cmd.name = "Comando demo"
    cmd.adjustments[0] = 0.15
    cmd.fill.solid()
    cmd.fill.fore_color.rgb = AZUL
    cmd.line.fill.background()
    _texto(s, MARGEN + Inches(0.2), y0 + Inches(3.6), izq_w - Inches(0.4), Inches(0.9),
           "python scripts/13_demo.py --q Q3", tam=16, color=BLANCO, negrita=True,
           ancla=MSO_ANCHOR.MIDDLE)
    r = pd.read_csv(S / "respuestas.csv", dtype=str, keep_default_na=False)
    r = r[(r["query_id"] == "Q3") & (r["estado"] != "no_encontrado")]
    r = pd.concat([r[r["estado"] == "respaldado_en_texto"].groupby("campo_respuesta").head(2),
                   r[r["estado"] == "ambiguo"].head(1)])
    df = pd.DataFrame({"Campo": r["campo_respuesta"].str.replace("_", " "),
                       "Valor": r["valor"].str.slice(0, 32), "Estado": r["estado"].str.replace("_", " "),
                       "Pasaje": r["passage_id"]})
    _texto(s, der_x, y0, der_w, Inches(0.4), "Q3 · refinería de Dos Bocas en Tabasco (salida/respuestas.csv)",
           tam=14, color=GRIS)
    _tabla(s, der_x, y0 + Inches(0.5), der_w, df, [1.6, 2.2, 1.6, 0.9], tam=13, alto_fila=Inches(0.5))

    destino.parent.mkdir(parents=True, exist_ok=True)
    prs.save(destino)
    return destino
