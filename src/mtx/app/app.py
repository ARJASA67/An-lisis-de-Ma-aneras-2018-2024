"""Punto de entrada de la app de anotación: `make app` (PRD §7). Solo registra las pestañas."""
from __future__ import annotations

import streamlit as st

from mtx.app import vista_estado, vista_gold, vista_juicios

st.set_page_config(page_title="Anotación · Minería de textos", layout="wide")

tab_estado, tab_juicios, tab_gold = st.tabs(["Estado", "Juicios", "Gold"])
with tab_estado:
    vista_estado.mostrar()
with tab_juicios:
    vista_juicios.mostrar()
with tab_gold:
    vista_gold.mostrar()
