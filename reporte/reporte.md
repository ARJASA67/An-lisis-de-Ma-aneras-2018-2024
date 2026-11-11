---
title: "Recuperación y extracción de información en discursos presidenciales (2018 a 2024)"
author: "Arturo Jaramillo Salmerón · Minería de Textos, UNAM FES Acatlán"
date: "11 de noviembre de 2026"
---

Repositorio: https://github.com/ARJASA67/An-lisis-de-Ma-aneras-2018-2024

<!-- CORTE 1 [VALIDAR]: esqueleto sin prosa. Los párrafos se agregan en el corte 2, sección por
sección, con aprobación del alumno. 11_reporte.py nunca sobrescribe este archivo. -->

# Datos, limpieza y segmentación

Tabla 1. Corpus, limpieza e índice (`salida/01_*.json`, `data/indice_meta.json`).

<!-- tabla:corpus -->

# Preprocesamiento e índice invertido

[Prosa del corte 2: tokenización, stoplist con ejemplos, stemming, exclusión de la marca, postings de 4 términos de `salida/02_postings.md`.]

# Ranking y evaluación de recuperación

[Prosa del corte 2: fórmulas de BM25 y TF-IDF, diferencia con rank_bm25, P@k, AP y MAP; discusión por consulta a partir de la tabla 3.]

Tabla 2. P@5, P@10 y MAP por variante; vista oficial y vista con ventana (`salida/resultados_ir.csv`, `salida/05_resultados_ir_ventana.csv`).

<!-- tabla:ir -->

Tabla 3. AP por consulta de las variantes con filtro y etiquetas calculadas (`salida/05_ir_ganador_por_consulta.csv`).

<!-- tabla:ir_consulta -->

![AP por consulta, variantes con filtro (`reporte/figuras/ir_ap_por_consulta.png`)](figuras/ir_ap_por_consulta.png){width=85%}

# Extracción con reglas y con modelo

[Prosa del corte 2: regex de FECHA y MONTO y casos no cubiertos, gazetteers (tamaño y origen), modelo `mrm8488/bert-spanish-cased-finetuned-ner` elegido por criterio técnico, normalización y fusión por span exacto.]

# Evaluación de extracción y análisis de errores

[Prosa del corte 2: fórmulas de P, R y F1 con coincidencia exacta; 20 pasajes evaluados por el kit y por la complementaria; un caso real por categoría de `salida/09_analisis_errores.csv`.]

Tabla 4. Precisión, recall y F1 por tipo y método (`salida/09_ie_detalle.csv`; s/c: el NER no predice ese tipo).

<!-- tabla:ie -->

Tabla 5. Errores de la extracción combinada por categoría, no excluyentes (`salida/09_resumen_errores.csv`).

<!-- tabla:errores -->

![F1 por tipo y método (`reporte/figuras/ie_f1_por_tipo_metodo.png`)](figuras/ie_f1_por_tipo_metodo.png){width=85%}

# Tablas de respuesta

[Corte 2: tablas compactas Q1 a Q10 desde `salida/tablas_respuesta/` con la valoración del alumno de `anotaciones/valoraciones.yaml`.]

Tabla 6. Estado de la evidencia por consulta (`salida/respuestas.csv`).

<!-- tabla:respuestas -->

# Uso de IA, limitaciones y reproducibilidad

[Prosa del corte 2: autoría (D21), pendientes y cómo reproducir.]
