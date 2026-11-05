---
name: reporte-pdf
description: "Usa esta skill cuando vayas a redactar, compilar, recortar o revisar el reporte del examen (reporte/reporte.md a reporte/reporte.pdf con pandoc y XeLaTeX, src/mtx/reporte.py, scripts/11_reporte.py, scripts/lint_estilo.py), insertar tablas y figuras de salida/, aplicar la guía de estilo, contar páginas o regenerar la sección 8 de resultados del README."
---
# Reporte en PDF del examen

El reporte es la evidencia escrita de todo el proyecto: entre 4 y 6 páginas, sin código, con cifras que salen de `salida/` y prosa validada por el alumno. Esta skill condensa PRD §6.14, D21 y el anexo A en reglas ejecutables.

## Cuándo usarla

1. Al crear o modificar `src/mtx/reporte.py`, `scripts/11_reporte.py`, `scripts/lint_estilo.py` o `reporte/plantilla.tex`.
2. Al redactar o corregir prosa de `reporte/reporte.md` en cualquiera de los tres cortes.
3. Al compilar `reporte/reporte.pdf`, contar páginas o recortar para caber en 6.
4. Al regenerar la sección 8 del README entre `<!-- resultados:inicio -->` y `<!-- resultados:fin -->`.
5. Al revisar que el reporte cumple la condición 11 de entrega (PRD §13).

## Prerrequisitos

1. `make resultados` corrió sin errores: existen `salida/resultados_ir.csv`, `salida/05_ir_por_consulta.csv`, `salida/05_ir_ganador_por_consulta.csv`, `salida/resultados_ie.csv`, `salida/09_analisis_errores.csv`, `salida/09_resumen_errores.csv`, `salida/respuestas.csv`, `salida/tablas_respuesta/*.md` y `anotaciones/valoraciones.yaml`.
2. Figuras generadas sin TeX en `reporte/figuras/`: `ir_map_por_modelo.png`, `ir_ap_por_consulta.png`, `ir_con_vs_sin_filtro.png`, `ie_f1_por_tipo_metodo.png`, `ie_errores_por_categoria.png`.
3. Tablas compactas en `reporte/tablas/`, producidas por `11_reporte.py` a partir de los CSV de `salida/`.
4. `pandoc` y una distribución TeX con `xelatex` instalados; solo `make reporte` los necesita. Verifica con `pandoc --version` y `xelatex --version` antes de decir que faltan.
5. `data/mejor_modelo.json`, `data/corpus_meta.json` y `salida/manifiesto_ejecucion.json` disponibles para la sección de reproducibilidad.
6. Si una cifra o archivo no existe, la sección correspondiente lleva la frase "pendiente" y se avisa al alumno. Nunca se rellena con un valor estimado (PRD §0, regla 6).

## Formato y compilación

1. Comando canónico (PRD §6.14): `cd reporte && pandoc reporte.md -o reporte.pdf --pdf-engine=xelatex --template=plantilla.tex`. Otra ruta que produzca el mismo PDF es válida si se documenta en el README.
2. `reporte/plantilla.tex` es sobria: márgenes de 2.2 cm, fuente del sistema, paquete `booktabs` para tablas, figuras con ancho máximo de la caja de texto. Sin colores de encabezado ni logotipos.
3. `11_reporte.py` cuenta páginas con `pypdf` (`len(PdfReader(ruta).pages)`) o con `pdfinfo` como alternativa, e imprime el total. Menos de 4 o más de 6 páginas es un error de salida, no una advertencia.
4. Si excede 6 páginas, el orden de recorte es fijo: primero anexos, después ejemplos redundantes (un ejemplo por categoría de error basta), después tablas de respuesta Q9 y Q10 resumidas con el resto en el repo. Nunca se quita la evidencia de un rubro ni se reduce la tipografía o los márgenes para ganar espacio.
5. Las tablas y figuras se generan con `make resultados`, sin TeX. `make reporte` solo compila.
6. Tras cada compilación se revisan visualmente todas las páginas: cortes de tablas entre páginas, fórmulas que se salen del margen, figuras ilegibles. La revisión se hace abriendo el PDF o convirtiendo páginas a imagen, nunca por suposición.
7. Prohibición del examen (EX): sin bloques de código ni fragmentos en línea con sintaxis de programa. Se permiten pseudocódigo en prosa ("para cada término de la consulta se suma su idf por el factor de saturación") y fórmulas en LaTeX. Rutas y nombres de archivo en texto plano están bien.

## Estructura del reporte (8 secciones)

| Núm. | Sección | Páginas | Contenido obligatorio (fuente en `salida/`) |
|---|---|---|---|
| 1 | Portada compacta | 0.25 | Título, nombre, materia, fecha, enlace al repo. |
| 2 | Datos, limpieza y segmentación | 0.75 | Estadísticas del corpus, conteos de limpieza (acotaciones, duplicados, fechas reparadas), decisión de segmentación y tabla de sensibilidad si existe, tratamiento de marcas y reporteros, intervenciones cortas descartadas. |
| 3 | Preprocesamiento e índice invertido | 0.75 | Tokenización, stoplist con ejemplos tomados de la estenográfica, stemming, exclusión de la marca del índice, postings de 4 términos. |
| 4 | Ranking y evaluación de IR | 1.25 | TF-IDF frente a BM25, con y sin filtro; tabla de P@5, P@10 y MAP en las dos vistas (oficial y con ventana); figura por consulta; discusión por consulta: dónde gana cada uno y por qué, consultas largas y cortas, sinónimos, qué cambiaría con embeddings densos. |
| 5 | Extracción con reglas y con modelo | 0.75 | Regex y casos no cubiertos, gazetteers (tamaño y origen), modelo elegido y criterio (o comparación sobre el conjunto de selección), normalización, fusión. |
| 6 | Evaluación de IE y análisis de errores | 1.0 | Tabla P/R/F1 por tipo y método, evaluación de 20 IDs, cambios posteriores al congelamiento si los hubo, categorías de error con ejemplos reales de `09_analisis_errores.csv`. |
| 7 | Tablas de respuesta | 0.75 | Las diez tablas en formato compacto con la valoración del alumno; si no caben, Q1 a Q8 completas y Q9 y Q10 resumidas con el resto en el repo. |
| 8 | Uso de IA, limitaciones y reproducibilidad | 0.5 | Resumen del README, autoría de la prosa (D21), qué quedó pendiente, cómo reproducir con `make resultados`. |

Reglas sobre la tabla:

1. La suma es 6 páginas; el mínimo aceptable es 4. Cada sección puede moverse ±0.25 páginas si otra lo compensa.
2. La discusión de IR (sección 4) se escribe después de ver las etiquetas calculadas de `salida/05_ir_ganador_por_consulta.csv`, no antes.
3. Para cada categoría de error del enunciado (entidad partida, sigla no reconocida, monto sin unidad, obra LOC u ORG, efecto de mayúsculas) la sección 6 incluye un caso observado o declara que no apareció. No se inventan errores para llenar una cuota.
4. Las cifras de IR se presentan como propias de esta colección, sin generalizar.

## Guía de estilo obligatoria

La prosa que escribe el asistente cumple estas reglas sin excepción (PRD §6.14):

1. Español de México, tono directo e impersonal: se habla de "el sistema", "el pipeline", "el índice". Sin "nosotros", sin "yo", sin "tú".
2. Sin rayas ni guiones largos como puntuación. Se usan comas, puntos, paréntesis o dos puntos.
3. Títulos y encabezados con mayúscula inicial solamente (nombres propios y siglas conservan la suya).
4. Sin el patrón "no es X, es Y" ni sus variantes con "sino".
5. Sin cierres sentenciosos ni frases de remate al final de párrafos o secciones. El párrafo termina cuando termina el dato.
6. Discusión en prosa y cifras en tablas. Las listas con negritas como sustituto de párrafos están prohibidas en el cuerpo del reporte.
7. Sin adjetivos vacíos ("robusto", "significativo", "notable") sin una cifra al lado que los respalde.
8. Cada afirmación comparativa cita la cifra y la tabla o figura: "BM25 con filtro supera a TF-IDF con filtro en MAP (0.xx frente a 0.yy, tabla 2)".
9. Toda cifra y todo ejemplo proviene de un archivo de `salida/`; lo que falte se declara pendiente. Está prohibido inventar, redondear hacia arriba o completar de memoria.

`scripts/lint_estilo.py` (P2) recorre `reporte/reporte.md` y reporta:

1. Rayas y guiones largos (U+2014, U+2013) usados como puntuación.
2. Encabezados con más de dos palabras capitalizadas que no sean nombres propios.
3. Coincidencias con la expresión `/no es .*?, (es|sino)/i`.
4. Frases o palabras listadas en `config/estilo_prohibido.txt`, una por línea.
5. Bloques de código (líneas con tres acentos graves) o fragmentos en línea con sintaxis de programa.

El lint ayuda pero no sustituye la lectura: si se recorta o se reescribe una sección, se vuelve a leer completa antes de darla por buena.

## Flujo en tres cortes con el alumno

Cada corte es un punto `[VALIDAR]`: el asistente muestra el resultado y espera aprobación explícita antes de seguir.

1. Corte 1, esqueleto. `11_reporte.py` genera `reporte/reporte.md` con los ocho títulos, las tablas compactas de `reporte/tablas/` y las figuras de `reporte/figuras/` insertadas en su sección, sin prosa. Se compila y se cuenta páginas para saber cuánto espacio queda para texto. El alumno aprueba el orden y qué tablas entran.
2. Corte 2, borrador de prosa. El asistente redacta sección por sección, una a la vez, leyendo los CSV correspondientes antes de escribir. El alumno corrige tono y conclusiones; el asistente aplica los cambios tal cual y no discute matices que el alumno quiera. Las conclusiones sobre IR e IE son del alumno; el asistente propone un texto base a partir de las etiquetas y categorías calculadas.
3. Corte 3, PDF final. Se corre `lint_estilo.py`, se compila, se cuenta páginas (entre 4 y 6), se revisan todas las páginas visualmente y se entrega al alumno el PDF con el conteo. Si hay recorte, se sigue el orden fijo de la sección "Formato y compilación".

Reglas de versionado de la prosa:

1. La prosa aprobada vive en `reporte/reporte.md`, versionada en git, y no se vuelve a generar en cada compilación. `11_reporte.py` solo regenera tablas, figuras y los bloques marcados como autogenerados; nunca sobrescribe párrafos aprobados.
2. Si una cifra cambia después de aprobar una sección (por ejemplo, tras un cambio posterior al congelamiento), se actualiza la tabla, se avisa al alumno qué párrafos dependen de esa cifra y se vuelve a validar solo esos párrafos.
3. La sección 8 del README (resultados principales: MAP por variante y F1 combinado por tipo) se autogenera entre `<!-- resultados:inicio -->` y `<!-- resultados:fin -->` en cada corrida de `11_reporte.py`. Nada fuera de los marcadores se toca.
4. La autoría se declara en "Uso de IA" (D21): quién redactó la prosa, quién la validó, qué partes se generaron de forma automática y con qué herramienta.

## Fórmulas que deben aparecer

Las fórmulas van en LaTeX dentro del Markdown, sin código, con la notación del anexo A del PRD. Se verifica que las ocho estén y que compilen sin salirse del margen.

1. idf de BM25: $\mathrm{idf}(t) = \ln\left(1 + \frac{N - df_t + 0.5}{df_t + 0.5}\right)$.
2. Puntaje BM25 con $k_1 = 1.5$ y $b = 0.75$, sumando sobre los términos únicos de la consulta: $\mathrm{score}(q, p) = \sum_{t \in q} \mathrm{idf}(t) \cdot \frac{tf_{t,p}\,(k_1 + 1)}{tf_{t,p} + k_1\left(1 - b + b \cdot \frac{|p|}{\mathrm{avgdl}}\right)}$.
3. TF-IDF sublineal con idf suavizado, normalizado L2 y similitud del coseno con la consulta: $w_{t,p} = \left(1 + \ln tf_{t,p}\right) \cdot \left(\ln\frac{1 + N}{1 + df_t} + 1\right)$. Se menciona que equivale a scikit-learn con `sublinear_tf=True` y `smooth_idf=True`.
4. Diferencia con `rank_bm25.BM25Okapi`: esa librería usa $\ln\frac{N - df_t + 0.5}{df_t + 0.5}$ con un piso $\varepsilon$ para términos con $df_t > N/2$. Se explica en una oración por qué el sistema usa la variante con el 1 sumado.
5. P@k = relevantes en los primeros k dividido entre k.
6. AP@10 = $\sum_{r=1}^{10} P@r \cdot rel(r) / R$, con R el número de relevantes del pool de esa consulta (denominador confirmado contra el kit en H0).
7. MAP = promedio de AP entre las diez consultas.
8. Precisión = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R); una predicción es TP cuando coincide exactamente en `(passage_id, tipo, inicio, fin)`.

## Lista de verificación antes de entregar

1. `reporte/reporte.pdf` tiene entre 4 y 6 páginas según `11_reporte.py` (condición 11 de PRD §13).
2. `grep -c '```' reporte/reporte.md` devuelve 0; no hay fragmentos de código en línea.
3. `uv run python scripts/lint_estilo.py reporte/reporte.md` sin hallazgos (si el script existe).
4. Las ocho secciones están presentes en el orden de la tabla y cada una respeta su extensión ±0.25 páginas.
5. Las ocho fórmulas del anexo A aparecen y se ven completas en el PDF.
6. Toda cifra del texto coincide con su archivo en `salida/`; se hace una lectura cruzada tabla por tabla.
7. Cada categoría de error del enunciado tiene un caso real o la declaración "no apareció".
8. Las diez tablas de respuesta llevan la valoración escrita por el alumno en `anotaciones/valoraciones.yaml`; el asistente no la redacta.
9. La sección "Uso de IA" declara la autoría de la prosa y qué se generó automáticamente.
10. Los tres cortes `[VALIDAR]` quedaron aprobados por el alumno y la prosa aprobada está en git.
11. La sección 8 del README entre los marcadores coincide con `salida/resultados_ir.csv` y `salida/resultados_ie.csv`.
12. Se revisaron visualmente todas las páginas: sin tablas partidas en lugares ilegibles, sin figuras fuera de margen.

## Skills relacionadas

- `integridad-congelacion`: qué hacer si una cifra del reporte cambia después de un congelamiento y cómo conservar las cifras previas.
- `pool-juicios-ir`: origen de `resultados_ir.csv`, la vista con ventana y `data/mejor_modelo.json` que alimentan la sección 4.
- `evaluacion-ie`: origen de `resultados_ie.csv`, la evaluación de 20 IDs y las categorías de error de la sección 6.
- `tablas-respuesta`: origen de `salida/respuestas.csv`, las diez tablas y `valoraciones.yaml` de la sección 7.
- `entrega-reproducible`: `make entrega`, manifiesto de ejecución y README que resume la sección 8.
