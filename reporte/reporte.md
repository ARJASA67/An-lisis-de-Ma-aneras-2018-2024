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

<!-- tabla:corpus -->

: Corpus, limpieza e índice (`salida/01_*.json`, `data/indice_meta.json`).

# Preprocesamiento e índice invertido

El texto se normaliza a NFC y minúsculas; un token es una secuencia de letras y dígitos con a lo sumo un guion interno, lo que conserva formas como covid-19. Se descartan los tokens de dos caracteres o menos que no son números y las palabras de una stoplist de 313 palabras funcionales del español más 24 propias de la estenográfica (336 distintas), como presidente, pregunta, interlocutora, gracias, bueno y pues (`config/stoplist_extra.txt`). Después se aplica el stemmer Snowball para español: refinería y refinerías comparten el stem refin. Se eligió stemming sobre lematización por costo (127,739 pasajes) y porque las consultas son cortas. Al indexar solo se tokeniza el cuerpo del pasaje, sin la marca del interlocutor, para que el nombre del presidente no pese en todos los pasajes. El índice invertido resultante tiene 35,891 stems y una longitud media de 72.2 tokens por pasaje. Los stems más frecuentes después de la stoplist siguen siendo verbos y sustantivos generales (hac, mexic, pued, trabaj; `salida/02_vocabulario_top.csv`), que reciben un idf bajo y casi no discriminan.

<!-- tabla:postings -->

: Postings de cuatro términos de las consultas (`salida/02_postings.md`).

# Ranking y evaluación de recuperación

Ambos modelos se implementan sobre el mismo índice. BM25 usa $k_1 = 1.5$ y $b = 0.75$ y suma sobre los términos únicos de la consulta:

$$\mathrm{idf}(t) = \ln\left(1 + \frac{N - df_t + 0.5}{df_t + 0.5}\right), \qquad \mathrm{score}(q, p) = \sum_{t \in q} \mathrm{idf}(t) \cdot \frac{tf_{t,p}\,(k_1 + 1)}{tf_{t,p} + k_1\left(1 - b + b \cdot \frac{|p|}{\mathrm{avgdl}}\right)}$$

La librería rank_bm25 (BM25Okapi) usa $\ln\frac{N - df_t + 0.5}{df_t + 0.5}$ con un piso $\varepsilon$ para los términos con $df_t > N/2$; el 1 sumado dentro del logaritmo mantiene el idf positivo para todo término sin recurrir a ese piso. TF-IDF usa tf sublineal e idf suavizado, normaliza en L2 y ordena por similitud del coseno con la consulta, equivalente a scikit-learn con sublinear_tf y smooth_idf:

$$w_{t,p} = \left(1 + \ln tf_{t,p}\right) \cdot \left(\ln\frac{1 + N}{1 + df_t} + 1\right)$$

El filtro de fecha restringe los candidatos a la ventana de cada consulta antes de ordenar. Las cuatro variantes se evalúan con el kit sobre 176 juicios de un pool formado por la unión de sus top-10. $P@k$ es el número de relevantes en los primeros $k$ dividido entre $k$; $AP = \sum_{r=1}^{10} P@r \cdot rel(r) / R$, con $R$ el total de relevantes del pool de la consulta, y MAP es el promedio de AP sobre las diez consultas. Como el horizonte es 10, una consulta con más de 10 relevantes no puede llegar a AP = 1: Q9 tiene 21 y su techo es 10/21 = 0.476, que ambos modelos alcanzan.

BM25 con filtro obtiene el mayor MAP oficial (0.575 frente a 0.385 de TF-IDF con filtro, tabla 3) y queda como modelo de la extracción. Por consulta gana en 8 de 10; TF-IDF gana en Q3 (0.447 frente a 0.249) y Q9 empata (tabla 4). Las diferencias más amplias están en Q10 (0.866 frente a 0.284) y Q4 (0.693 frente a 0.180), consultas con nombres propios de varias palabras; una explicación posible, no probada, es que la saturación de tf de BM25 impide que un pasaje que repite un solo término común (tren, aeropuerto) supere a otro que contiene todos los términos. En Q3 la consulta incluye dos, un término de df alto que en este corpus funciona casi siempre como número; también es una hipótesis sin probar para la caída de BM25. La longitud de la consulta no separa a los ganadores: BM25 gana en 4 de 5 consultas cortas y en 4 de 5 largas. La vista con ventana, que solo cuenta como relevante un pasaje dentro del periodo, conserva el orden de las variantes (0.625 de BM25 con filtro); el filtro pesa más en Q6, cuya ventana de seis meses deja 11,120 pasajes elegibles y lleva el AP de BM25 de 0.189 sin filtro a 0.449 con filtro. Ninguno de los dos modelos resuelve sinónimos (huachicol frente a robo de combustible, AIFA frente a Felipe Ángeles); un modelo de embeddings densos podría acercarlos, a cambio de perder la explicación término por término y de exigir otro índice.

<!-- tabla:ir -->

: P@5, P@10 y MAP por variante; vista oficial y vista con ventana (`salida/resultados_ir.csv`, `salida/05_resultados_ir_ventana.csv`).

<!-- tabla:ir_consulta -->

: AP por consulta de las variantes con filtro y etiquetas calculadas (`salida/05_ir_ganador_por_consulta.csv`).


# Extracción con reglas y con modelo

La extracción se aplica a los 99 pasajes únicos del top-10 de BM25 con filtro. El primer enfoque son reglas: expresiones regulares para FECHA (día, mes y año en sus combinaciones, con mes en palabras) y para MONTO, restringido a dinero con moneda explícita (pesos, dólares, con escalas como millones o mil millones). Las cantidades que no son dinero (dosis, litros, sucursales, porcentajes) se guardan aparte como auxiliares, 78 en los top-10, y no entran a la evaluación. Quedan sin cubrir las fechas escritas por completo en palabras y los rangos de años, que se reconocen como dos fechas sueltas; ambos casos están documentados como pruebas que fallan a propósito. ORG y LOC salen de gazetteers: 109 organizaciones (76 del kit, 17 añadidas a mano y 16 siglas minadas del corpus y aceptadas una por una) con 190 formas de búsqueda, y 59 lugares con 67 formas, incluidos los 32 estados. PER sale de la marca del interlocutor, separando el nombre del cargo.

El segundo enfoque es el modelo mrm8488/bert-spanish-cased-finetuned-ner, fijado en la revisión b11721d. Predice PER, ORG, LOC y MISC; MISC se descarta, así que el modelo no cubre FECHA ni MONTO. Los pasajes se parten en ventanas de 494 subtokens con solape de 64 y los spans se proyectan a desplazamientos de caracteres del pasaje. El modelo se eligió por criterio técnico y antes de abrir el gold: el segundo candidato del enunciado ya no está disponible en Hugging Face, de modo que no hubo conjunto de selección. Las dos fuentes se fusionan por coincidencia exacta de tipo, inicio y fin: una entidad que ambas producen queda como ambos, y un solape parcial no se resuelve, se registra. El resultado son 903 entidades únicas y 911 filas en entidades.csv, con 146 discrepancias registradas (140 solapes parciales y 6 de tipo distinto, `salida/08_resumen.json`). La normalización convierte fechas a ISO con la fecha del discurso como ancla y montos a valor numérico con moneda; el nombre canónico de una ORG o LOC solo se asigna cuando el gazetteer registra la equivalencia.

# Evaluación de extracción y análisis de errores

El gold son 20 pasajes sorteados con semilla 42 del top-10 de BM25 con filtro, dos por consulta (uno de rango 1 a 5 y otro de 6 a 10), anotados a mano en la app sin ver predicciones y cerrados con 183 entidades. Una predicción es TP solo si coincide en pasaje, tipo, inicio y fin; con eso $P = TP/(TP+FP)$, $R = TP/(TP+FN)$ y $F1 = 2PR/(P+R)$. El kit evalúa solo los pasajes con entidades gold; como ninguno de los 20 quedó vacío, la evaluación complementaria sobre los 20 IDs del sorteo da las mismas cifras.

La combinación obtiene F1 = 0.774 (tabla 5) frente a 0.587 de las reglas y 0.708 del modelo. Las reglas son precisas y cubren poco (P = 0.82, R = 0.46); el modelo encuentra más ORG y LOC, y la unión sube el recall a 0.81 a costa de bajar la precisión a 0.74. En PER la unión llega a R = 0.92 porque la regla de marca aporta los nombres de quien habla y el modelo los del cuerpo. FECHA y MONTO solo tienen reglas y 6 entidades gold cada uno, así que sus cifras se mueven con un solo acierto.

Los errores se clasificaron sobre la salida combinada (tabla 6; una fila puede caer en varias categorías). El más común es de frontera, 38 casos: el modelo marca Felipe Ángeles donde el gold tiene aeropuerto Felipe Ángeles (1606_0) y de México donde el gold tiene Estado de México (343_2). La entidad partida apareció 2 veces: Centro y Sudamérica (354_38) sale como dos entidades, Centro y Sudamérica. El efecto de las mayúsculas se concentra en la marca de interlocutor, con 20 errores ahí, 17 del modelo, que corta los nombres en mayúsculas en fragmentos como MAN o MANUEL LÓPEZ (420_10, 343_2). La única sigla no reconocida es UMAS (1216_44). La confusión de obra entre LOC y ORG aparece una vez: Tren Maya en «empresa de participación estatal mayoritaria Tren Maya» es ORG para el modelo y LOC en el gold (396_23). El monto sin unidad, entendido como una predicción que corta la moneda, no apareció; sí hay montos gold sin moneda junto a la cifra (500 en 1415_16; Sesenta y cinco mil y 65 mil millones en 2115_5) que la regla omite porque exige la moneda. Entre las 17 omisiones destacan programas que ningún gazetteer registra, como Sembrando Vida (420_10, 776_72). No hubo cambios a reglas ni gazetteers después de ver estos resultados.

<!-- tabla:ie -->

: Precisión, recall y F1 por tipo y método (`salida/09_ie_detalle.csv`; s/c: el NER no predice ese tipo).

<!-- tabla:errores -->

: Errores de la extracción combinada por categoría, no excluyentes (`salida/09_resumen_errores.csv`).


# Tablas de respuesta

Para cada consulta, cada campo de la pregunta (dependencias, estados, montos, fechas, dosis) se llena con las entidades del top-10 del tipo correspondiente, quitando las que caen en la marca del interlocutor y las variantes del nombre del presidente en los campos de personas. Un valor cuenta como respaldado en texto solo si un patrón de la relación pedida (por ejemplo bimestr para la pensión o diario para el salario) aparece a 60 caracteres o en la oración del valor o en sus contiguas; si no, queda ambiguo con su cita. Lo que dice un reportero queda como ambiguo con su interlocutor. Respaldado significa que el corpus lo afirma, sin implicar que sea verdad. Las diez tablas completas, con valor, pasaje, fecha y cita, están en `salida/tablas_respuesta/`; aquí se resumen por estado (tabla 7) con la valoración de cada una (tabla 8). Tres campos no tienen evidencia en el top-10: montos del Tren Maya en Q1, fechas de aumento de la pensión en Q7 y organizaciones empresariales en Q8.

<!-- tabla:respuestas -->

: Estado de la evidencia por consulta (`salida/respuestas.csv`).

<!-- tabla:valoraciones -->

: Valoración de credibilidad de cada tabla, escrita por el alumno (`anotaciones/valoraciones.yaml`).

# Uso de IA, limitaciones y reproducibilidad

El código, las pruebas y los borradores de este reporte los escribió un asistente de IA (Claude, en Claude Code), a partir de las cifras de `salida/`; el alumno revisó y aprobó cada sección y la lista de archivos generados está en el README. Las decisiones humanas no se delegaron al asistente: los juicios de relevancia se hicieron a mano, en la app y en una hoja compartida autorizada por el profesor, durante la etapa del repositorio anterior al relevo; el gold y las valoraciones son del alumno. No se midió el acuerdo entre anotadores de los juicios.

Las limitaciones principales son el tamaño del gold (20 pasajes, 6 FECHA y 6 MONTO), un solo modelo NER sin comparación, la pérdida de preguntas cortas de reporteros por la segmentación y que AP depende del pool de las cuatro variantes. Todo se reproduce sin TeX desde el repositorio con los scripts numerados (`scripts/01` a `scripts/10`, que usan los juicios, el gold y la caché del NER versionados) y el PDF con `scripts/11_reporte.py`; los hashes del kit, del gold y de las entidades están en `salida/manifiesto_ejecucion.json`.
