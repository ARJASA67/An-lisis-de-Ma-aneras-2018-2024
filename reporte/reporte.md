---
title: "Recuperación y extracción de información en discursos presidenciales (2018 a 2024)"
author: "Arturo Jaramillo Salmerón · Minería de Textos, UNAM FES Acatlán"
date: "11 de noviembre de 2026"
---

Repositorio: https://github.com/ARJASA67/An-lisis-de-Ma-aneras-2018-2024

<!-- CORTE 1 [VALIDAR]: esqueleto sin prosa. Los párrafos se agregan en el corte 2, sección por
sección, con aprobación del alumno. 11_reporte.py nunca sobrescribe este archivo. -->

# Datos, limpieza y segmentación

El corpus es el snapshot `carevies/discursos_AMLO` (commit 2c463bb, 2,294 versiones estenográficas). El formato real de las marcas de interlocutor difiere del que supone el kit: el patrón del kit reconoce marcas en 0 de 2,294 discursos, así que el sistema canoniza las marcas a una intervención por línea antes de segmentar. La limpieza elimina solo las acotaciones de una lista cerrada (video, audio, inaudible, himno, falla de transmisión), 7,338 en total y el 0.12 % de los caracteres; los paréntesis con siglas como (IMSS) se conservan. Se excluyen 4 duplicados exactos y 1 casi duplicado (Jaccard 0.986) y se reparan 10 fechas con el título del discurso (`salida/01_limpieza.json`, `salida/01_fechas_reparadas.csv`).

Cada intervención se parte en ventanas de 200 palabras con paso de 150; una ventana de menos de 40 palabras se descarta. El pasaje conserva la marca del interlocutor al inicio y el desplazamiento donde empieza el cuerpo, de modo que el índice y la extracción distinguen quién habla. Las intervenciones de reporteros se indexan, pero el 64.9 % queda bajo el mínimo de 40 palabras y se pierde; los reporteros aportan el 15.5 % de los pasajes. Ese es el costo de la decisión de segmentación y afecta sobre todo a preguntas breves con siglas o cifras.

Tabla 1. Corpus, limpieza e índice (`salida/01_*.json`, `data/indice_meta.json`).

<!-- tabla:corpus -->

# Preprocesamiento e índice invertido

El texto se normaliza a NFC y minúsculas; un token es una secuencia de letras y dígitos con a lo sumo un guion interno, lo que conserva formas como covid-19. Se descartan los tokens de dos caracteres o menos que no son números y las palabras de una stoplist de 313 palabras funcionales del español más 24 propias de la estenográfica (336 distintas), como presidente, pregunta, interlocutora, gracias, bueno y pues (`config/stoplist_extra.txt`). Después se aplica el stemmer Snowball para español: refinería y refinerías comparten el stem refin. Se eligió stemming sobre lematización por costo (127,739 pasajes) y porque las consultas son cortas. Al indexar solo se tokeniza el cuerpo del pasaje, sin la marca del interlocutor, para que el nombre del presidente no pese en todos los pasajes. El índice invertido resultante tiene 35,891 stems y una longitud media de 72.2 tokens por pasaje. Los stems más frecuentes después de la stoplist siguen siendo verbos y sustantivos generales (hac, mexic, pued, trabaj; `salida/02_vocabulario_top.csv`), que reciben un idf bajo y casi no discriminan.

Tabla 2. Postings de cuatro términos de las consultas (`salida/02_postings.md`).

<!-- tabla:postings -->

# Ranking y evaluación de recuperación

[Prosa del corte 2: fórmulas de BM25 y TF-IDF, diferencia con rank_bm25, P@k, AP y MAP; discusión por consulta a partir de la tabla 4.]

Tabla 3. P@5, P@10 y MAP por variante; vista oficial y vista con ventana (`salida/resultados_ir.csv`, `salida/05_resultados_ir_ventana.csv`).

<!-- tabla:ir -->

Tabla 4. AP por consulta de las variantes con filtro y etiquetas calculadas (`salida/05_ir_ganador_por_consulta.csv`).

<!-- tabla:ir_consulta -->

![AP por consulta, variantes con filtro (`reporte/figuras/ir_ap_por_consulta.png`)](figuras/ir_ap_por_consulta.png){width=85%}

# Extracción con reglas y con modelo

[Prosa del corte 2: regex de FECHA y MONTO y casos no cubiertos, gazetteers (tamaño y origen), modelo `mrm8488/bert-spanish-cased-finetuned-ner` elegido por criterio técnico, normalización y fusión por span exacto.]

# Evaluación de extracción y análisis de errores

[Prosa del corte 2: fórmulas de P, R y F1 con coincidencia exacta; 20 pasajes evaluados por el kit y por la complementaria; un caso real por categoría de `salida/09_analisis_errores.csv`.]

Tabla 5. Precisión, recall y F1 por tipo y método (`salida/09_ie_detalle.csv`; s/c: el NER no predice ese tipo).

<!-- tabla:ie -->

Tabla 6. Errores de la extracción combinada por categoría, no excluyentes (`salida/09_resumen_errores.csv`).

<!-- tabla:errores -->

![F1 por tipo y método (`reporte/figuras/ie_f1_por_tipo_metodo.png`)](figuras/ie_f1_por_tipo_metodo.png){width=85%}

# Tablas de respuesta

[Corte 2: tablas compactas Q1 a Q10 desde `salida/tablas_respuesta/` con la valoración del alumno de `anotaciones/valoraciones.yaml`.]

Tabla 7. Estado de la evidencia por consulta (`salida/respuestas.csv`).

<!-- tabla:respuestas -->

# Uso de IA, limitaciones y reproducibilidad

[Prosa del corte 2: autoría (D21), pendientes y cómo reproducir.]
