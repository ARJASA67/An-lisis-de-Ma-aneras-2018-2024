"""Pestaña Juicios: relevancia 1/0, ciega al modelo, autoguardado atómico (PRD §6.6, D07).

No muestra puntajes, rangos, variante ni `en_ventana`; no sugiere ni preselecciona nada.
"""
from __future__ import annotations

import streamlit as st

from mtx import adaptadores_kit, config, consultas, pool
from mtx.app import componentes

RECORDATORIO = ("**Criterio:** relevancia temática. La fecha y el modelo que recuperó el pasaje "
                "no cuentan para el juicio; la ventana de fechas se aplica después, en el análisis.")

CSS = """
<style>
mark.termino { background:#fde68a; color:inherit; padding:0 2px; border-radius:2px; }
mark.marca { background:#e5e7eb; color:#4b5563; padding:0 2px; border-radius:2px; }
.pasaje { white-space:pre-wrap; line-height:1.55; font-size:1.05rem; }
</style>
"""


@st.cache_data(show_spinner=False)
def _cargar():
    pl = componentes.cargar_pool_ciego()
    cons = consultas.cargar().set_index("query_id")
    meta = componentes.metadatos_pasajes(list(pl["passage_id"]))
    orden = pool.orden_presentacion(pl)
    return pl, cons, meta, orden, adaptadores_kit.sha256_archivo(pool.POOL_CSV)


def _almacen(pl, hash_pool) -> componentes.AlmacenJuicios:
    if "almacen" not in st.session_state:
        st.session_state.almacen = componentes.AlmacenJuicios(pl, hash_pool=hash_pool)
    return st.session_state.almacen


def mostrar() -> None:
    if not pool.POOL_CSV.exists():
        st.warning("Falta el pool. Corre `make pool` y recarga.")
        return
    if not componentes.criterios_listos():
        st.info("Antes del primer juicio: escribe `config/criterios_relevancia.md` y apruébalo. "
                "La app no registra juicios sin ese archivo.")
        return
    st.markdown(CSS, unsafe_allow_html=True)
    pl, cons, meta, orden, hash_pool = _cargar()
    alm = _almacen(pl, hash_pool)

    with st.sidebar:
        st.header("Juicios")
        q = st.selectbox("Consulta", list(cons.index), key="consulta")
        for qq in cons.index:
            h, t = alm.progreso(qq)
            st.progress(h / t if t else 0.0, text=f"{qq}: {h} de {t}")
        h, t = alm.progreso()
        st.metric("Avance global", f"{h} de {t}")
        if st.button("Recargar desde disco"):
            alm.cargar()
            st.session_state.pop("idx", None)
            st.rerun()
        st.caption(f"Revisión del archivo: {alm.revision}. Cada clic guarda al instante.")

    ids = orden[q]
    clave = f"idx_{q}"
    if clave not in st.session_state:
        inicio = componentes.primer_pendiente(ids, lambda p: alm.estado(q, p))
        st.session_state[clave] = 0 if inicio is None else inicio
    idx = st.session_state[clave]
    pid = ids[idx]
    fila = pl[(pl["query_id"] == q) & (pl["passage_id"] == pid)].iloc[0]
    m = meta.loc[pid]
    c = cons.loc[q]

    st.title(c["consulta"])
    st.caption(f"Pregunta de extracción (ayuda): {c['pregunta_extraccion']}")
    st.markdown(RECORDATORIO)
    st.progress((idx + 1) / len(ids), text=f"Pasaje {idx + 1} de {len(ids)} en esta consulta")
    st.markdown(f"`doc_id` {fila['doc_id']} · {m['titulo']} · interlocutor: {m['interlocutor']} · "
                f"fecha: {fila['fecha'] or 'desconocida'}")
    st.markdown(f"<div class='pasaje'>{componentes.html_pasaje(fila['texto'], c['consulta'], int(m['inicio_cuerpo']))}</div>",
                unsafe_allow_html=True)

    actual = alm.estado(q, pid)
    if componentes.juicios_congelados():
        _solo_lectura(q, pid, idx, ids, clave, actual)
        return
    etiqueta = {None: "sin juzgar", "": "omitido (sin juzgar)", "0": "No relevante (0)",
                "1": "Relevante (1)"}[actual]
    st.write(f"Estado de este pasaje: **{etiqueta}**")

    def decidir(valor: str, avanzar: bool = True) -> None:
        try:
            alm.registrar(q, pid, valor)
        except componentes.ConflictoRevision as e:
            st.session_state.conflicto = str(e)
            return
        if avanzar:
            j = componentes.siguiente_pendiente(ids, lambda p: alm.estado(q, p), idx)
            st.session_state[clave] = idx if j is None else j

    def anterior() -> None:
        st.session_state[clave] = max(idx - 1, 0)

    b1, b0, bo, ba = st.columns(4)
    b1.button("Relevante (1)", on_click=decidir, args=("1",), width="stretch")
    b0.button("No relevante (0)", on_click=decidir, args=("0",), width="stretch")
    bo.button("Omitir por ahora", on_click=decidir, args=("",), width="stretch")
    ba.button("Anterior", on_click=anterior, width="stretch")

    if "conflicto" in st.session_state:
        st.error(st.session_state.conflicto)
    if componentes.siguiente_pendiente(ids, lambda p: alm.estado(q, p), idx, False) is None:
        st.success(f"{q} no tiene pasajes pendientes.")
    with st.expander("Criterios de relevancia (tu archivo)"):
        st.markdown(componentes.CRITERIOS_RELEVANCIA.read_text(encoding="utf-8"))
    st.caption(f"Dirección de datos: {config.DIR_ANOTACIONES.name}/juicios_relevancia.csv")


def _solo_lectura(q: str, pid: str, idx: int, ids: list[str], clave: str, actual) -> None:
    """Juicios congelados (H4 cerrado): se pueden consultar, no cambiar."""
    etiqueta = {None: "sin juzgar", "": "omitido (sin juzgar)", "0": "No relevante (0)",
                "1": "Relevante (1)"}[actual]
    st.info("Los juicios están **congelados** desde que se eligió el mejor modelo de IR "
            "(`data/mejor_modelo.json`). Esta pestaña es de solo lectura: cambiar un juicio "
            "alteraría las métricas IR y el ganador.")
    st.write(f"Juicio registrado: **{etiqueta}**")

    def mover(paso: int) -> None:
        st.session_state[clave] = (idx + paso) % len(ids)

    c1, c2 = st.columns(2)
    c1.button("◀ Pasaje anterior", on_click=mover, args=(-1,), width="stretch", key="ro_ant")
    c2.button("Pasaje siguiente ▶", on_click=mover, args=(1,), width="stretch", key="ro_sig")
