"""Pestaña Estado: un estado por artefacto y el comando que lo desbloquea (skill `app-anotacion`)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mtx.app import componentes


def mostrar() -> None:
    st.subheader("Estado de los artefactos")
    st.caption("Un artefacto no está \"completo\" por existir: cuenta el validador en verde con "
               "hashes vigentes.")
    filas = componentes.estado_artefactos()
    st.dataframe(pd.DataFrame([vars(f) for f in filas]).rename(columns={
        "nombre": "Artefacto", "estado": "Estado", "detalle": "Detalle", "siguiente": "Siguiente"}),
        hide_index=True, width="stretch")
    st.button("Actualizar", key="actualizar_estado")
