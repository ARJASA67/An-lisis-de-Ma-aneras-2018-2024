"""Pestaña Gold: anotación de entidades en modo ciego (PRD §6.11, D10, D19).

No lee ni muestra predicciones del sistema. Cada acción guarda al instante con escritura atómica.
Modo principal: búsqueda por texto exacto con elección de la aparición. Modo secundario:
selección por tokens. El conjunto de selección (P1) no existe: no hay segundo NER que comparar.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx import config, consultas, gold, muestreo
from mtx.app import componentes

CSS = """
<style>
mark.marca { background:#e5e7eb; color:#4b5563; padding:0 2px; border-radius:2px; }
mark.PER { background:#bfdbfe; } mark.ORG { background:#fde68a; } mark.LOC { background:#bbf7d0; }
mark.FECHA { background:#fbcfe8; } mark.MONTO { background:#ddd6fe; }
.pasaje { white-space:pre-wrap; line-height:1.6; font-size:1.05rem; }
</style>
"""
CRITERIOS = config.DIR_CONFIG / "criterios_anotacion.md"


@st.cache_data(show_spinner=False)
def _cargar():
    muestra = muestreo.leer_muestra()
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "inicio_cuerpo", "titulo", "fecha"],
                          filters=[("passage_id", "in", list(muestra["passage_id"]))])
    pas = pas.set_index("passage_id")
    cons = consultas.cargar().set_index("query_id")
    return muestra, pas, cons


def _almacen(muestra, textos) -> gold.AlmacenGold:
    if "almacen_gold" not in st.session_state:
        st.session_state.almacen_gold = gold.AlmacenGold(muestra, textos)
    return st.session_state.almacen_gold


def _html(texto: str, inicio_cuerpo: int, ents: list[dict]) -> str:
    """Marca en gris y entidades del alumno coloreadas; los solapes se muestran sin color."""
    spans, ocupado = [], []
    if inicio_cuerpo > 0:
        cand = [(0, inicio_cuerpo, "marca")]
    else:
        cand = []
    cand += [(int(e["inicio"]), int(e["fin"]), e["tipo"]) for e in ents]
    for ini, fin, clase in sorted(cand, key=lambda x: (x[0], -x[1])):
        if clase != "marca" and any(a < fin and ini < b for a, b in ocupado):
            continue
        if clase == "marca":
            continue
        spans.append((ini, fin, clase))
        ocupado.append((ini, fin))
    # La marca se pinta solo en los tramos que no cubre una entidad.
    if inicio_cuerpo > 0:
        cursor = 0
        for a, b in sorted(ocupado):
            if a >= inicio_cuerpo:
                break
            if a > cursor:
                spans.append((cursor, a, "marca"))
            cursor = max(cursor, b)
        if cursor < inicio_cuerpo:
            spans.append((cursor, inicio_cuerpo, "marca"))
    return componentes.resaltar_html(texto, spans)


def _agregar(alm: gold.AlmacenGold, pid: str, tipo: str, ini: int, fin: int) -> None:
    try:
        alm.agregar(pid, tipo, ini, fin)
        st.session_state.msg_gold = ("ok", f"Agregada {tipo} «{alm.textos[pid][ini:fin]}»")
    except componentes.ConflictoRevision as e:
        st.session_state.msg_gold = ("error", str(e))
    except (ValueError, PermissionError) as e:
        st.session_state.msg_gold = ("error", f"No se agregó: {e}")


def mostrar() -> None:
    if not muestreo.MUESTRA_GOLD.exists():
        st.warning("Falta la muestra. Corre `python scripts/08b_muestra_gold.py` y recarga.")
        return
    st.markdown(CSS, unsafe_allow_html=True)
    muestra, pas, cons = _cargar()
    textos = pas["texto"].to_dict()
    alm = _almacen(muestra, textos)
    cerrado = componentes.gold_cerrado()

    with st.sidebar:
        st.header("Gold")
        st.caption("Conjunto: Evaluación (20). No hay conjunto de selección.")
        hechos, total = alm.progreso()
        st.metric("Pasajes cerrados", f"{hechos} de {total}")
        for q in cons.index:
            ids_q = list(muestra[muestra["query_id"] == q]["passage_id"])
            h, t = alm.progreso(ids_q)
            st.progress(h / t if t else 0.0, text=f"{q}: {h} de {t}")
        cuenta = alm.gold["tipo"].value_counts()
        st.write(" · ".join(f"{t}: {int(cuenta.get(t, 0))}" for t in gold.TIPOS))
        if st.button("Recargar desde disco", key="recargar_gold"):
            alm.cargar()
            st.rerun()
        st.caption(f"Revisión gold {alm.rev_gold}, estado {alm.rev_estado}.")
        with st.expander("Convenciones de anotación"):
            if CRITERIOS.exists():
                st.markdown(CRITERIOS.read_text(encoding="utf-8"))

    etiquetas = [f"{q} · {p} · {alm.estado(p)}" for q, p in
                 zip(muestra["query_id"], muestra["passage_id"], strict=True)]
    i = st.selectbox("Pasaje", range(len(etiquetas)), format_func=lambda k: etiquetas[k],
                     key="pasaje_gold")
    q, pid = muestra["query_id"].iloc[i], muestra["passage_id"].iloc[i]
    texto, ic = textos[pid], int(pas.at[pid, "inicio_cuerpo"])
    st.subheader(cons.at[q, "consulta"])
    st.caption(f"{pid} · {pas.at[pid, 'titulo']} · {str(pas.at[pid, 'fecha'])[:10]} · estado: "
               f"**{alm.estado(pid)}**. Gris = marca de interlocutor (sus entidades también se "
               "anotan).")
    ents = alm.entidades(pid)
    st.markdown(f"<div class='pasaje'>{_html(texto, ic, ents)}</div>", unsafe_allow_html=True)

    if cerrado:
        st.info("El gold está cerrado (`anotaciones/cierre_gold.json`). Solo lectura.")
    else:
        tipo = st.radio("Tipo", gold.TIPOS, horizontal=True, key="tipo_gold")
        modo_buscar, modo_tokens = st.tabs(["Buscar por texto", "Seleccionar tokens"])
        with modo_buscar:
            buscado = st.text_input("Texto exacto de la entidad", key=f"buscar_{pid}")
            occ = gold.buscar_ocurrencias(texto, buscado)
            if buscado and not occ:
                st.warning("No aparece tal cual en el pasaje (revisa acentos y mayúsculas).")
            for k, o in enumerate(occ):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"…{o.antes}**[{texto[o.inicio:o.fin]}]**{o.despues}… "
                            f"`({o.inicio}, {o.fin})`")
                c2.button("Agregar", key=f"add_{pid}_{k}", on_click=_agregar,
                          args=(alm, pid, tipo, o.inicio, o.fin))
        with modo_tokens:
            toks = gold.tokens(texto)
            nombres = [f"{k}: {t[2]}" for k, t in enumerate(toks)]
            a = st.selectbox("Primer token", range(len(toks)), format_func=lambda k: nombres[k],
                             key=f"tok_a_{pid}")
            b = st.selectbox("Último token", range(len(toks)), index=a,
                             format_func=lambda k: nombres[k], key=f"tok_b_{pid}")
            recortar = st.checkbox("Recortar puntuación final (nunca quita $)", value=True,
                                   key=f"rec_{pid}")
            if b >= a:
                ini, fin = gold.span_de_tokens(texto, toks, a, b, recortar)
                st.write(f"Span: «{texto[ini:fin]}» `({ini}, {fin})`")
                st.button("Agregar", key=f"add_tok_{pid}", on_click=_agregar,
                          args=(alm, pid, tipo, ini, fin))
            else:
                st.warning("El último token va después del primero.")

    if "msg_gold" in st.session_state:
        nivel, msg = st.session_state.pop("msg_gold")
        (st.success if nivel == "ok" else st.error)(msg)

    st.markdown("**Entidades de este pasaje**")
    if not ents:
        st.caption("Ninguna todavía. Cerrar un pasaje con cero entidades es válido.")
    for k, e in enumerate(ents):
        c1, c2 = st.columns([5, 1])
        c1.write(f"{e['tipo']} · «{e['texto']}» `({e['inicio']}, {e['fin']})`")
        if not cerrado and c2.button("Borrar", key=f"del_{pid}_{k}"):
            try:
                alm.borrar(pid, e["tipo"], int(e["inicio"]), int(e["fin"]))
            except componentes.ConflictoRevision as err:
                st.session_state.msg_gold = ("error", str(err))
            st.rerun()

    if not cerrado:
        if st.button("Pasaje revisado completo", type="primary", key=f"cerrar_{pid}"):
            try:
                alm.cerrar_pasaje(pid)
            except componentes.ConflictoRevision as err:
                st.session_state.msg_gold = ("error", str(err))
            st.rerun()
        st.divider()
        errores, avisos = gold.validar_gold(muestra, textos)
        for a in avisos:
            st.caption(f"Aviso: {a}")
        if errores:
            st.caption("Para cerrar el gold falta: " + "; ".join(errores))
        elif st.button("Cerrar gold (levanta el modo ciego; no se puede deshacer)"):
            gold.cerrar_gold(muestra, textos)
            gold.exportar_gold()
            st.rerun()
