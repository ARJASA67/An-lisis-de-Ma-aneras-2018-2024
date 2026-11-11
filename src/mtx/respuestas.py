"""Tablas de respuesta con evidencia (PRD §6.13, D17, U14, T14).

Una lista de entidades es un inventario: una respuesta exige que el texto citado muestre la relación
(patrón de contexto a ±60 caracteres o en la oración del span y sus contiguas). «Respaldado en
texto» significa que el corpus lo afirma, no que sea verdad. Nada aquí modifica `entidades.csv`,
`entidades_enriquecidas.csv` ni `cantidades_auxiliares.csv`, y nada redacta valoraciones: esas las
escribe el alumno en `anotaciones/valoraciones.yaml`.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

COLUMNAS = ["query_id", "campo_respuesta", "valor", "unidad", "relacion", "estado", "passage_id",
            "doc_id", "fecha_documento", "evidencia_inicio", "evidencia_fin", "cita",
            "entidades_referencia", "regla_relacion", "grupo_evento", "interlocutor"]
ESTADOS = ("respaldado_en_texto", "contradictorio", "ambiguo", "no_encontrado")
RANGO_ESTADO = {e: i for i, e in enumerate(ESTADOS)}
TIPOS_ENTIDAD = {"PER", "ORG", "LOC", "FECHA", "MONTO"}
TIPOS_AUX = {"CANTIDAD", "PORCENTAJE"}
_FIN_ORACION = re.compile(r"[.!?;](?=\s|$)")


def plano(texto: str) -> str:
    """Minúsculas sin acentos ni espacios repetidos."""
    s = unicodedata.normalize("NFD", str(texto).lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").split())


# --------------------------------------------------------------------------- contexto


def oraciones(texto: str) -> list[tuple[int, int]]:
    """Límites `(inicio, fin)` de las oraciones del pasaje, sin espacios en los bordes."""
    limites, ini = [], 0
    for m in _FIN_ORACION.finditer(texto):
        limites.append((ini, m.end()))
        ini = m.end()
    if ini < len(texto):
        limites.append((ini, len(texto)))
    out = []
    for a, b in limites:
        while a < b and texto[a].isspace():
            a += 1
        while b > a and texto[b - 1].isspace():
            b -= 1
        if b > a:
            out.append((a, b))
    return out or [(0, len(texto))]


def contexto(texto: str, ini: int, fin: int, ventana: int = 60
             ) -> tuple[str, tuple[int, int]]:
    """Texto de contexto (±`ventana` ∪ oración del span y contiguas) y la oración del span."""
    ors = oraciones(texto)
    k = next((i for i, (a, b) in enumerate(ors) if a <= ini < b), None)
    if k is None:  # el span empieza en un espacio entre oraciones
        k = min(range(len(ors)), key=lambda i: abs(ors[i][0] - ini))
    a = min(max(0, ini - ventana), ors[max(0, k - 1)][0])
    b = max(min(len(texto), fin + ventana), ors[min(len(ors) - 1, k + 1)][1])
    return texto[a:b], ors[k]


def buscar_patron(ctx: str, patrones: list[str]) -> str | None:
    """Primer patrón (regex en minúsculas sin acentos) que aparece en el contexto."""
    p = plano(ctx)
    return next((pat for pat in patrones if re.search(pat, p)), None)


# --------------------------------------------------------------------------- filtros y exclusiones


def filtros_gazetteer(gaz_ext: pd.DataFrame, gaz_loc: pd.DataFrame) -> dict[str, set[str]]:
    """Conjuntos de nombres planos para `farmaceutica`, `organizacion_empresarial` y estados."""
    def nombres(df: pd.DataFrame, cols: tuple[str, ...]) -> set[str]:
        out = set()
        for _, f in df.iterrows():
            for c in cols:
                out |= {plano(n) for n in str(f.get(c, "") or "").split("|") if n.strip()
                        and n.strip().lower() != "nan"}
        return out
    return {
        "farmaceutica": nombres(gaz_ext[gaz_ext["tipo"] == "farmacéutica"],
                                ("nombre", "variantes", "siglas")),
        "organizacion_empresarial": nombres(gaz_ext[gaz_ext["tipo"] == "organización empresarial"],
                                            ("nombre", "variantes", "siglas")),
        "entidad_federativa": nombres(gaz_loc[gaz_loc["categoria"] == "estado"],
                                      ("nombre", "variantes")),
    }


def excluir(ents: pd.DataFrame, per_excluidas: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """U14: quita entidades en la marca y PER de la lista. Devuelve (filtradas, conteos)."""
    en_marca = ents["en_marca"].astype(str).str.lower() == "true"
    lista = {plano(x) for x in per_excluidas}
    por_lista = ~en_marca & (ents["tipo"] == "PER") & ents["texto_normalizado"].map(
        lambda t: plano(t) in lista)
    conteos = []
    for q in sorted(ents["query_id"].unique(), key=lambda x: int(x[1:])):
        m = ents["query_id"] == q
        conteos += [{"query_id": q, "motivo": "en_marca", "n": int((m & en_marca).sum())},
                    {"query_id": q, "motivo": "lista_excluir", "n": int((m & por_lista).sum())}]
    return ents[~en_marca & ~por_lista].copy(), pd.DataFrame(conteos)


# --------------------------------------------------------------------------- candidatos


def candidatos_entidades(ents: pd.DataFrame) -> pd.DataFrame:
    """Entidades con `clave` de agrupación (canónico verificado o texto normalizado) y `valor`."""
    e = ents.copy()
    verificado = (e["estado_identidad"] == "gazetteer") & e["canonico"].notna()
    e["valor"] = e["texto"].where(~verificado, e["canonico"])
    e["clave"] = e["valor"].map(plano).where(verificado, e["texto_normalizado"].map(plano))
    return e[["query_id", "passage_id", "tipo", "texto", "inicio", "fin", "valor", "clave"]]


def candidatos_auxiliares(aux: pd.DataFrame, inicio_cuerpo: dict[str, int]) -> pd.DataFrame:
    """Cantidades auxiliares (D11) como candidatos; fuera las que caen en la marca."""
    a = aux.rename(columns={"tipo_aux": "tipo"}).copy()
    a = a[a["fin"] > a["passage_id"].map(inicio_cuerpo)]
    a["valor"] = a["texto"]
    a["clave"] = a["texto"].map(plano)
    return a[["query_id", "passage_id", "tipo", "texto", "inicio", "fin", "valor", "clave",
              "unidad"]]


def _del_campo(campo: dict, ents: pd.DataFrame, aux: pd.DataFrame, filtros: dict[str, set[str]]
               ) -> pd.DataFrame:
    if campo["tipo"] in TIPOS_AUX:
        c = aux[aux["tipo"] == campo["tipo"]]
        if campo.get("unidad"):
            c = c[c["unidad"].fillna("").map(lambda u: bool(re.search(campo["unidad"], plano(u))))]
        return c
    c = ents[ents["tipo"] == campo["tipo"]]
    if campo.get("filtro"):
        nombres = filtros[campo["filtro"]]
        c = c[c["clave"].isin(nombres) | c["texto"].map(plano).isin(nombres)]
    return c


# --------------------------------------------------------------------------- respuestas


@dataclass
class Pasaje:
    texto: str
    doc_id: str
    fecha: str
    interlocutor: str
    es_reportero: bool
    intervencion_id: str
    token_inicio: int
    token_fin: int
    orgs: list[tuple[int, int, str]] = field(default_factory=list)


def _evidencia(fila, campo: dict, p: Pasaje, ventana: int) -> dict:
    ctx, (oi, of) = contexto(p.texto, int(fila.inicio), int(fila.fin), ventana)
    patron = buscar_patron(ctx, campo["patrones_contexto"])
    estado = "respaldado_en_texto" if patron else "ambiguo"
    relacion = campo["relacion"]
    if p.es_reportero:
        # T14: lo que pregunta un reportero no se atribuye al presidente ni cuenta como afirmado.
        relacion, estado = f"pregunta de reportero: {relacion}", "ambiguo"
    refs = ""
    if campo["tipo"] in {"MONTO", "CANTIDAD", "PORCENTAJE"}:
        refs = "|".join(dict.fromkeys(t for a, b, t in p.orgs if oi <= a and b <= of))
    return {"estado": estado, "relacion": relacion, "evidencia_inicio": oi, "evidencia_fin": of,
            "cita": p.texto[oi:of], "regla_relacion": f"contexto:{patron}" if patron
            else "sin_patron", "entidades_referencia": refs}


def _grupos_evento(filas: list[dict], pasajes: dict[str, Pasaje]) -> None:
    """Asigna `grupo_evento`: misma clave en ventanas solapadas de la misma intervención."""
    for f in filas:
        f["_p"] = pasajes[f["passage_id"]]
    filas.sort(key=lambda f: (f["_clave"], f["_p"].intervencion_id, f["_p"].token_inicio))
    n, prev = 0, None
    for f in filas:
        p = f["_p"]
        if prev is None or prev["_clave"] != f["_clave"] or \
                prev["_p"].intervencion_id != p.intervencion_id or \
                p.token_inicio >= prev["_fin_grupo"]:
            n += 1
            f["_fin_grupo"] = p.token_fin
        else:
            f["_fin_grupo"] = max(prev["_fin_grupo"], p.token_fin)
        f["_grupo"] = n
        prev = f


def responder_campo(qid: str, campo: dict, cands: pd.DataFrame, pasajes: dict[str, Pasaje],
                    ventana: int) -> tuple[list[dict], pd.DataFrame]:
    """Filas de `respuestas.csv` de un campo (una por grupo de evento) y su tabla de frecuencias."""
    nombre = campo["campo"]
    unidad = campo.get("unidad_respuesta", "")
    if cands.empty:
        fila = dict.fromkeys(COLUMNAS, "")
        fila.update({"query_id": qid, "campo_respuesta": nombre, "unidad": unidad,
                     "relacion": campo["relacion"], "estado": "no_encontrado"})
        return [fila], pd.DataFrame()
    filas = []
    for c in cands.itertuples(index=False):
        p = pasajes[c.passage_id]
        ev = _evidencia(c, campo, p, ventana)
        filas.append({"query_id": qid, "campo_respuesta": nombre, "valor": c.valor,
                      "unidad": unidad, "passage_id": c.passage_id, "doc_id": p.doc_id,
                      "fecha_documento": p.fecha, "interlocutor": p.interlocutor,
                      "_clave": c.clave, **ev})
    _grupos_evento(filas, pasajes)
    # Una fila por grupo de evento: la de mejor estado (y la primera en el texto si empatan).
    mejor: dict[tuple, dict] = {}
    for f in filas:
        k = (f["_clave"], f["_grupo"])
        if k not in mejor or RANGO_ESTADO[f["estado"]] < RANGO_ESTADO[mejor[k]["estado"]]:
            mejor[k] = f
    elegidas = list(mejor.values())
    if campo.get("unico"):
        por_doc: dict[str, set[str]] = {}
        for f in elegidas:
            if f["estado"] == "respaldado_en_texto":
                por_doc.setdefault(f["doc_id"], set()).add(f["_clave"])
        for f in elegidas:
            if f["estado"] == "respaldado_en_texto" and len(por_doc[f["doc_id"]]) > 1:
                f["estado"] = "contradictorio"
                f["_grupo_evento"] = f"{qid}-{nombre}-doc{f['doc_id']}"
    for f in elegidas:
        f["grupo_evento"] = f.pop("_grupo_evento", f"{qid}-{nombre}-{f['_grupo']}")
    frec = (pd.DataFrame([{"clave": f["_clave"], "valor": f["valor"], "passage_id": f["passage_id"],
                           "doc_id": f["doc_id"], "estado": f["estado"]} for f in filas])
            .assign(rango=lambda d: d["estado"].map(RANGO_ESTADO))
            .groupby("clave")
            .agg(valor=("valor", "first"), n_menciones=("passage_id", "size"),
                 n_pasajes=("passage_id", "nunique"), n_discursos=("doc_id", "nunique"),
                 mejor_rango=("rango", "min"))
            .reset_index())
    # El estado del valor sale de sus filas elegidas (incluye `contradictorio`).
    est = {}
    for f in elegidas:
        r = RANGO_ESTADO[f["estado"]]
        est[f["_clave"]] = min(est.get(f["_clave"], r), r)
    frec["mejor_rango"] = frec["clave"].map(est)
    frec["estado"] = frec["mejor_rango"].map(dict(enumerate(ESTADOS)))
    frec.insert(0, "campo_respuesta", nombre)
    frec.insert(0, "query_id", qid)
    salida = [{k: f.get(k, "") for k in COLUMNAS} for f in elegidas]
    salida.sort(key=lambda f: (RANGO_ESTADO[f["estado"]], plano(f["valor"]), f["passage_id"]))
    return salida, frec.sort_values(["mejor_rango", "n_discursos", "n_menciones"],
                                    ascending=[True, False, False]).drop(columns="mejor_rango")


def validar_respuestas(df: pd.DataFrame, textos: dict[str, str]) -> list[str]:
    """Contrato de `respuestas.csv`: 16 columnas, estados válidos, citas exactas, vacíos coherentes."""
    if list(df.columns) != COLUMNAS:
        return [f"Columnas {list(df.columns)}; se esperan {COLUMNAS}"]
    errores = []
    fuera = set(df["estado"]) - set(ESTADOS)
    if fuera:
        errores.append(f"Estados fuera de dominio: {fuera}")
    for f in df.itertuples(index=False):
        if f.estado == "no_encontrado":
            if any(str(getattr(f, c)) not in ("", "nan") for c in
                   ("valor", "passage_id", "cita", "evidencia_inicio", "evidencia_fin")):
                errores.append(f"{f.query_id} {f.campo_respuesta}: no_encontrado con evidencia")
        elif f.passage_id not in textos:
            errores.append(f"{f.query_id} {f.campo_respuesta}: pasaje {f.passage_id!r} desconocido")
        elif textos[f.passage_id][int(f.evidencia_inicio):int(f.evidencia_fin)] != f.cita:
            errores.append(f"{f.query_id} {f.campo_respuesta} {f.passage_id}: cita no coincide")
    return errores


# --------------------------------------------------------------------------- Markdown


def _celda(s, n: int | None = None) -> str:
    s = " ".join(str(s).split()).replace("|", "\\|")
    return s if n is None or len(s) <= n else s[: n - 1].rstrip() + "…"


def tabla_markdown(qid: str, consulta: dict, campos: list[dict], resp: pd.DataFrame,
                   frec: pd.DataFrame, exclusiones: dict[str, int], modelo: str, max_valores: int
                   ) -> str:
    """Cuerpo de la tabla Markdown de una consulta (sin el bloque de valoración)."""
    lineas = [f"# {qid} · {consulta['consulta']}", "",
              f"**Pregunta:** {consulta['pregunta_extraccion']}", "",
              (f"Modelo: `{modelo}` (top-10 con filtro de fecha {consulta['desde']} a "
               f"{consulta['hasta']}). Exclusiones: {exclusiones.get('en_marca', 0)} entidades en "
               f"la marca de interlocutor y {exclusiones.get('lista_excluir', 0)} PER de la lista "
               "(`config/excluir_tablas.yaml`). «Respaldado» = el texto lo afirma, no que sea "
               "verdad."), ""]
    for campo in campos:
        nombre = campo["campo"]
        lineas += [f"## {nombre.replace('_', ' ')}", "", f"_Relación exigida: {campo['relacion']}._", ""]
        f = frec[frec["campo_respuesta"] == nombre] if not frec.empty else frec
        if f.empty:
            lineas += ["| valor | estado | discursos | pasaje | fecha | cita |", "|---|---|---|---|---|---|",
                       "| — | no_encontrado | 0 | — | — | sin evidencia en el top-10 |", ""]
            continue
        r = resp[resp["campo_respuesta"] == nombre].copy()
        r["_clave"] = r["valor"].map(plano)
        lineas += ["| valor | estado | discursos (pasajes) | pasaje | fecha | cita |",
                   "|---|---|---|---|---|---|"]
        for v in f.head(max_valores).itertuples(index=False):
            ej = r[r["_clave"] == plano(v.valor)]
            ej = ej.sort_values("estado", key=lambda s: s.map(RANGO_ESTADO)).head(1)
            pid, fecha, cita, quien = ("—", "—", "—", "")
            if not ej.empty:
                e = ej.iloc[0]
                pid, fecha, cita = e["passage_id"], e["fecha_documento"], e["cita"]
                quien = f" ({_celda(e['interlocutor'], 40)})" if e["relacion"].startswith(
                    "pregunta de reportero") else ""
            lineas.append(f"| {_celda(v.valor, 60)} | {v.estado} | {v.n_discursos} ({v.n_pasajes}) "
                          f"| {pid} | {fecha} | {_celda(cita, 160)}{quien} |")
        resto = len(f) - max_valores
        if resto > 0:
            lineas.append(f"\n_{resto} valores más en `salida/respuestas.csv`._")
        lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def sha256_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def bloque_valoracion(entrada: dict | None, sha_tabla: str) -> str:
    """Bloque `valoracion:` con el texto del alumno o la leyenda `[VALIDAR]`."""
    if not entrada or not str(entrada.get("texto", "")).strip():
        return "\n## Valoración\n\n[VALIDAR] pendiente del alumno\n"
    aviso = ""
    if entrada.get("tabla_sha256") and entrada["tabla_sha256"] != sha_tabla:
        aviso = ("\n> **Valoración invalidada:** la tabla cambió después de escribirla "
                 "(`tabla_sha256` distinto). [VALIDAR] el alumno debe revisarla.\n")
    return f"\n## Valoración\n{aviso}\n{str(entrada['texto']).strip()}\n"


def validar_valoraciones(valoraciones: dict, hashes: dict[str, str]) -> list[str]:
    """[VALIDAR] previo al reporte: 10 entradas no vacías con el hash de la tabla vigente."""
    problemas = []
    for q, h in hashes.items():
        e = (valoraciones or {}).get(q)
        if not e or not str(e.get("texto", "")).strip():
            problemas.append(f"{q}: falta la valoración del alumno")
        elif e.get("tabla_sha256") != h:
            problemas.append(f"{q}: la valoración no corresponde a la tabla vigente")
    return problemas
