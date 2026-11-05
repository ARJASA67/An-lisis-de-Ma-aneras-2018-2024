# PRD unificado · Sistema de recuperación y extracción de información sobre discursos presidenciales

**Examen 1 · Minería de Textos · Licenciatura en Ciencia de Datos**
**Versión:** 3.0 unificada · 4 de noviembre de 2026
**Fuentes:** enunciado del examen (PDF de 4 páginas), PRD 1.0 (26 de octubre), PRD 1.1 (2 de noviembre), PRD 1.2, PRD 2.0 (31 de octubre) y la plantilla reutilizable de decisiones congeladas.
**Destinatarios:** el alumno responsable y el asistente de programación (Claude Code, Cursor, Copilot Workspace o similar) que trabaja con él en su laptop.
**Producto:** repositorio GitHub reproducible, seis CSV de entrega, reporte PDF de 4 a 6 páginas y presentación de 8 minutos con demo en vivo (máximo 5 láminas).

---

## 0. Cómo usar este documento

### 0.1 Procedencia de cada regla

| Marca | Significado |
| --- | --- |
| EX | Requisito explícito del enunciado. No se negocia. |
| DP | Decisión de este proyecto. Se puede revisar antes de su momento de congelación (sección 4); después, cualquier cambio crea una versión experimental nueva y se documenta. |
| OP | Experimento o comodidad opcional. Prescindible para la entrega mínima. |
| PV | Dato pendiente de verificar contra el kit real o con el profesor. No se presenta como confirmado. |

El enunciado y las aclaraciones documentadas del profesor gobiernan la evaluación. El kit real gobierna sus interfaces. Este PRD fija las decisiones propias y no atribuye al profesor acuerdos que no estén registrados en `docs/decisiones.md`.

### 0.2 Reglas de operación para el asistente

1. **Leer completo antes de programar.** El asistente lee este PRD y los archivos reales del kit antes de escribir código, y sigue el orden de hitos de la sección 12.
2. **Fase 0 breve.** El asistente pregunta al alumno solo lo que no puede inspeccionar por sí mismo (sección 1.3). El entorno, las versiones y los archivos existentes se comprueban directamente; no se convierte todo en una entrevista bloqueante.
3. **Trabajo que el asistente tiene prohibido hacer.** Los juicios de relevancia, la anotación gold, el conjunto de selección del NER (si existe), la revisión de siglas del gazetteer y las valoraciones de las tablas los produce el alumno leyendo pasajes. El asistente construye la herramienta, valida formatos y jamás rellena, completa, sugiere ni "corrige" esos valores. Es condición del examen (EX, p. 4) y regla de integridad académica.
4. **Puntos de validación.** Donde el PRD marque `[VALIDAR]`, el asistente muestra el resultado y espera aprobación antes de continuar: criterios de relevancia y anotación, Q9 y Q10, gazetteer extendido, prosa del reporte, láminas y guion.
5. **Contratos fijos.** El kit (`kit/`) no se modifica. `evaluar.py` se usa tal cual. Las adaptaciones viven en `src/mtx/`.
6. **No inventar resultados.** Toda cifra y todo ejemplo del reporte proviene de archivos generados en `salida/`. Lo que falte se declara pendiente.
7. **Congelar antes de medir.** Segmentación y fechas antes del pooling; reglas, gazetteers, modelo NER y convenciones de anotación antes de abrir el gold. Cambiar algo después obliga a documentarlo y a conservar las cifras previas.
8. **Todo en español.** Identificadores sin acentos (`fecha`, `titulo`, `puntaje`), docstrings, mensajes, README y reporte en español.
9. **Prioridades.** Cada módulo tiene prioridad P0, P1 o P2 (sección 12.1). No se empieza un P1 mientras falte un P0. Si el plazo peligra, se aplica la lista de recortes de la sección 12.4 avisando al alumno.
10. **Commits** con Conventional Commits (sección 11.5), uno por unidad probada.

### 0.3 Conflictos entre versiones y cómo se resolvieron

Las cinco versiones previas difieren en los puntos siguientes. La columna "Resolución" es la que rige en este documento; cada una se puede revertir editando la decisión correspondiente de la sección 4.

| # | Tema | Versiones en conflicto | Resolución (y por qué) |
| --- | --- | --- | --- |
| U1 | Pool de relevancia | 1.0 y plantilla: solo top-10 con filtro (≈20 por consulta). 1.1, 1.2, 2.0: unión de las cuatro variantes (≤40) | **Cuatro variantes** (D06). El enunciado pide comparar con y sin filtro; con el pool reducido las variantes sin filtro se castigan por pasajes no juzgados. Si falta tiempo, recorte 5 de 12.4 |
| U2 | Criterio de relevancia | 1.1 y 1.2: temático, la ventana se analiza aparte. 2.0: la ventana forma parte de la relevancia | **Temático** (D07). Permite un único juicio por pasaje válido para las cuatro variantes; el efecto de la ventana se mide con una vista complementaria (6.6) |
| U3 | Porcentajes | 1.0 y 1.1: se anotan MONTO. 1.2 y 2.0: salida auxiliar | **Auxiliar** (D11). El enunciado define MONTO como "cantidades en pesos o dólares, con su unidad"; los porcentajes de Q8 se responden desde `cantidades_auxiliares.csv`. PV con el profesor |
| U4 | Marca de interlocutor en el índice | 1.0: se indexa. 1.1, 1.2: se excluye con `inicio_cuerpo`. 2.0: ambiguo | **Se excluye del índice** y se conserva en `texto` para la extracción (D03). Repetida en cada ventana inflaría el tf de "secretario", "salud", "presidente" |
| U5 | Selección del modelo NER | 1.0: dos modelos comparados sobre el gold. 1.1: sobre 6 pasajes de selección. 1.2 y 2.0: un NER fijado por criterios técnicos, comparación opcional | **Un NER fijado antes del gold (P0)**; comparación con conjunto de selección disjunto como P1 (D09). El gold de 20 nunca elige ni ajusta nada |
| U6 | Span de FECHA con modificador relativo | 1.0 y 1.1: solo el núcleo (`15 de enero`). 2.0 y plantilla: con el modificador (`próximo 15 de enero`) | **Con modificador** (D13). El modificador cambia el significado y el enunciado cita "el próximo 15 de enero" como fecha relativa resoluble. Se excluyen "el", "en", "del" |
| U7 | Año aislado | 1.0 y 1.1: nunca es FECHA. 2.0: `en 2019` es FECHA con precisión de año | **`en 2019`, `el año 2019`, `desde 2019` son FECHA** con precisión de año; un número de cuatro cifras sin contexto temporal no lo es (D13) |
| U8 | Desempate del ganador IR | 1.2: BM25. 2.0: TF-IDF | **BM25** (D08). Es la línea base del curso; el empate exacto es improbable y se comenta en el reporte |
| U9 | Desempate dentro de un ranking | 1.x: `passage_id` ascendente (orden lexicográfico). Plantilla: `(-puntaje, doc_id, posicion)` numérico | **Tupla numérica `(-puntaje, doc_id, posicion)`** (6.4). El orden lexicográfico pone `10_2` antes que `9_1` |
| U10 | Menos de 10 pasajes dentro de la ventana | 1.0: `-inf` antes del argsort. Plantilla: rellenar con puntaje 0.0. 1.2 y 2.0: devolver los que haya | **Devolver `min(10, elegibles)`** y registrar el motivo (6.4). No se rellena con pasajes excluidos ni con ceros |
| U11 | Vacunas y farmacéuticas (Q2) | 1.1: ORG solo si refiere a la farmacéutica. 2.0: un producto no es ORG. Plantilla: siempre ORG | **Siempre ORG** (D14). En transcripción oral la distinción fabricante/producto no es anotable con consistencia, y Q2 pregunta "qué farmacéuticas" |
| U12 | Casi duplicados | 1.1: se excluyen automáticamente. 1.2: solo se señalan | **Exactos se excluyen; casi duplicados (misma fecha y Jaccard ≥ 0.9) se excluyen con el umbral declarado y se listan** para auditoría (6.1.2). El alumno puede revertir uno por uno en `config/limpieza.yaml` |
| U13 | Sustitución de pasajes gold | 1.0: a juicio del alumno. 1.1: criterio objetivo. 1.2 y 2.0: nunca por falta de entidades | **Solo por criterio objetivo** (menos de 25 palabras de contenido o más de la mitad de fórmulas de protocolo), nunca por falta de entidades, y siempre antes de ver predicciones (6.11) |
| U14 | Exclusión del presidente en las tablas | 1.1: se excluye. 1.2: sin lista negra | **Se excluyen las entidades dentro de la marca** y se aplica una lista configurable `config/excluir_tablas.yaml` cuyo valor por defecto son las variantes del nombre del presidente en la columna de funcionarios; se reporta cuántas se excluyeron (6.13) |
| U15 | Unión de subtokens del NER | 1.0 y 1.1: unir adyacentes del mismo tipo separados por un espacio. 2.0: no unir arbitrariamente | **Unión intrapalabra siempre; unión interpalabra como posproceso documentado**, guardando la versión cruda y la unida para medir el efecto (6.8) |
| U16 | `ranking.csv` | 1.x: 8 columnas. 2.0: añade `posicion` | **9 columnas con `posicion`** (3.5). El enunciado pide devolver "doc id, fecha, posición y puntaje"; el evaluador solo lee cuatro columnas, así que no se rompe. PV contra el kit |
| U17 | Calendario | 1.0 y 1.1: lunes 26 a miércoles 28 de octubre. 1.2 y 2.0: hitos con dependencias | **Hitos con dependencias** (sección 12) y las fechas del enunciado como hechos. El plazo real vigente se registra en `docs/decisiones.md` |
| U18 | Duración de la presentación | 1.x: 90 s por lámina más 2 min de demo (suma 9.5 min). 2.0: 5 + 2 + 1 | **≈5 min de exposición, 2 de demo y 1 de margen** (6.15) |
| U19 | Metas numéricas | Plantilla: MAP > 0.40 y F1 > 0.65 como definición de terminado | **No son criterios de aceptación.** Se conservan como umbrales de alerta: un MAP < 0.15 o un F1 combinado < 0.30 obligan a buscar un bug antes de reportar (sección 13) |
| U20 | Carpeta de los archivos humanos | 1.x: `data/`. 2.0: `anotaciones/` | **`anotaciones/`** versionada y protegida; la raíz recibe copias validadas (sección 9) |
| U21 | `make all` | 1.2: no debe fingir una corrida ininterrumpida. 2.0: alias de `make entrega` | **Alias de `make entrega`** que se detiene con un mensaje claro cuando falta un insumo humano (sección 10) |
| U22 | Modelo NER por defecto | 1.x: `PlanTL-GOB-ES/roberta-base-bne-capitel-ner`. 2.0: `mrm8488/bert-spanish-cased-finetuned-ner` | **`mrm8488/bert-spanish-cased-finetuned-ner`** como principal (ficha verificada en 2.0); PlanTL como candidato 2 para la comparación opcional (6.8) |

---

## 1. Contexto, objetivo y alcance

### 1.1 Problema (EX, pp. 1 a 3)

Construir en Python, sobre el corpus `carevies/discursos_AMLO` (2,294 versiones estenográficas de conferencias matutinas y discursos de 2018 a 2024, según el enunciado; se registra el tamaño realmente descargado), un sistema con dos tareas:

- **Tarea A, recuperación de información (IR), 35 puntos.** Dada una consulta en lenguaje natural y una ventana opcional `[desde, hasta]`, devolver los 10 pasajes más relevantes con `doc_id`, `fecha`, `posicion` y `puntaje`, usando dos modelos comparados (TF-IDF con coseno y BM25), y evaluarlos con una colección de prueba propia (pool y juicios manuales) con P@5, P@10 y MAP.
- **Tarea B, extracción de información (IE), 35 puntos.** Sobre los 10 pasajes del mejor modelo para cada consulta, extraer entidades PER, ORG, LOC, FECHA y MONTO con dos enfoques combinados (reglas más gazetteer, y un modelo NER preentrenado para español), evaluarlos contra un gold de 20 pasajes anotado a mano con P/R/F1 por tipo y método, analizar errores con ejemplos reales y responder la pregunta de extracción de cada consulta con una tabla corta y una valoración de credibilidad.

La unidad de recuperación es el pasaje, no el discurso (EX, p. 1). Cada pasaje conserva `doc_id`, `fecha` y `posicion`. Decidir qué limpiar, qué conservar y cómo segmentar forma parte del examen y se califica.

Más el reporte PDF de 4 a 6 páginas, README reproducible desde cero, `requirements.txt`, sección "Uso de IA" y presentación de 8 minutos con demo en vivo.

### 1.2 Matriz de trazabilidad de la rúbrica (EX, pp. 3 y 4)

| ID | Rubro | Puntos | Evidencia que produce este proyecto |
| --- | --- | ---: | --- |
| R01 | Preprocesamiento y segmentación: pipeline justificado, manejo del ruido, pasajes con `doc_id`, fecha y posición | 8 | Limpieza auditada, segmentación propia, estadísticas, descartes cortos, sensibilidad (OP) |
| R02 | Índice invertido: estructura correcta, postings con frecuencias, tres ejemplos en el reporte | 5 | Índice término → {pasaje: tf}, verificación contra scikit-learn, postings de 4 términos |
| R03 | Ranking TF-IDF y BM25: ambos funcionan, top-10 por consulta, filtro por fecha operativo | 10 | `ranking.csv` con cuatro variantes, pruebas de fórmula, solapes y exclusiones por filtro |
| R04 | Evaluación de IR: `juicios_relevancia.csv` completo, `resultados_ir.csv` con P@5, P@10, MAP, comparación argumentada | 7 | Pool de cuatro variantes, app de juicios, evaluador del kit, vista con ventana, análisis por consulta |
| R05 | Reglas y gazetteer: regex de FECHA y MONTO robustas, gazetteer extendido, casos cubiertos y no cubiertos | 7 | Suite `pytest` con positivos y negativos, gazetteers ORG y LOC, minería de siglas revisada |
| R06 | NER con modelo: integrado, salida alineada con spans, fusión con reglas | 7 | Pipeline HF con offsets, chunking, caché versionada, fusión por span exacto |
| R07 | Evaluación de IE y análisis de errores: `gold_entidades.csv` con 20 pasajes, `resultados_ie.csv` por tipo y método, errores con ejemplos reales | 9 | Muestra ciega de 20, app de gold, evaluador del kit, análisis automático de errores |
| R08 | Tablas de respuesta: las ocho preguntas contestadas con entidades y valoración de credibilidad | 5 | `respuestas.csv` con evidencia, tablas Q1 a Q10, `valoraciones.yaml` del alumno |
| R09 | Reporte PDF de 4 a 6 páginas y reproducibilidad: README desde cero, `requirements.txt`, decisiones defendidas, sin código | 6 | `reporte.pdf`, README de 10 secciones, `uv.lock`, `make entrega` desde clon limpio |
| R10 | Presentación de 8 minutos con demo en vivo, máximo 5 láminas | 6 | Láminas, guion medido, `make demo Q=...` |
| R11 | Individual; juicios y gold propios; sección "Uso de IA" | Transversal | `anotaciones/` con procedencia, README 11.3 |
| R12 | Q1 a Q8 sin reformular; Q9 y Q10 propias evaluadas con el mismo protocolo | Transversal | `data/consultas.csv`, pool, juicios y gold incluyen Q9 y Q10 |

Los diez rubros suman 70 puntos. Un sistema con un solo modelo de ranking o un solo enfoque de extracción pierde todos los puntos del rubro (EX, p. 4): por eso los criterios de aceptación de 6.4 y 6.9 son bloqueantes. Un README que no permita reproducir pierde la mitad de R09.

Fuera del alcance: la parte teórica en Kahoot (30 % del examen), interfaces públicas, embeddings densos (solo se discuten), ajuste fino de modelos, motores de búsqueda externos.

### 1.3 Fase 0 · Datos que el asistente necesita del alumno

Se pregunta solo lo que no se puede inspeccionar; las respuestas van a `docs/decisiones.md`.

1. **Entorno:** sistema operativo y arquitectura, versión de Python (se requiere 3.11 o 3.12; si no, `uv python install 3.11`), presencia de `uv`, `git`, `pandoc` y una distribución TeX. El asistente ejecuta las comprobaciones. Si falta TeX el proyecto avanza: solo `make reporte` lo necesita.
2. **Acceso a Hugging Face:** descarga de prueba pequeña. Sin corpus no hay examen; si la red bloquea, se detiene y lo reporta.
3. **Identidad:** nombre completo del alumno (portada y láminas), usuario de GitHub, nombre del repo (sugerido `examen1-mineria-textos`), público o privado con acceso al profesor.
4. **Ruta del kit:** `corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`. Se copian a `kit/` sin modificar y se registran sus hashes SHA-256.
5. **Q9 y Q10:** se eligen después de explorar el corpus (sección 5). Los valores por defecto (Guardia Nacional y Tren Interoceánico) solo se usan si el alumno pide que el asistente decida, con la advertencia de que otros compañeros pueden elegir lo mismo.
6. **Plazo vigente y horas disponibles:** fecha y hora reales de entrega y de presentación (el enunciado fija 28 de octubre a las 20:00 y 4 de noviembre; se registra lo que aplique) y horas por día, para calibrar la sección 12.
7. **Confirmación de utilerías con el profesor (PV):** el asistente redacta un mensaje corto con las bibliotecas de la sección 2.2 que no aparecen en el enunciado y su papel; el alumno lo envía y registra la respuesta. Mientras no haya respuesta se trabaja con ellas, pero cada una tiene alternativa.
8. **Estado actual:** qué artefactos ya existen y si hay un commit entregado. Si lo hay, se conserva su identificación; las mejoras posteriores se registran aparte y no se reescribe qué versión fue entregada.

---

## 2. Restricciones duras y herramientas

### 2.1 Del enunciado (EX, p. 4)

- Todo en Python. Trabajo individual: código, juicios de relevancia, anotación gold y reporte son propios. Dos entregas con juicios o anotaciones idénticas se califican con cero en esos rubros.
- Bibliotecas válidas: `pandas`, `numpy`, `scikit-learn`, `nltk`, `spacy`, `regex`, `rank_bm25`, `datasets`, `transformers`.
- Prohibidas: LangChain, LlamaIndex, Haystack, Elasticsearch, Whoosh, Vespa y cualquier herramienta que construya el índice o el ranking por el estudiante.
- El índice invertido se escribe a mano o con scikit-learn; BM25 puede ser propio o de `rank_bm25`.
- Asistentes de IA generativa permitidos para programar y redactar, con la sección "Uso de IA" en el README. El juicio no se delega: juicios y gold se hacen leyendo los pasajes. En la demo se pregunta sobre cualquier parte del código.
- Entrega en GitHub (público o con acceso al profesor). El commit final es el que se califica.

### 2.2 Decisiones del proyecto sobre herramientas (DP)

- Índice invertido construido a mano (dict de Python) y contrastado con la matriz de scikit-learn. BM25 implementado a mano; `rank_bm25` solo como dependencia de desarrollo para una prueba de consistencia. TF-IDF con scikit-learn. Elección pedagógica, no una prohibición adicional del examen.
- NER con un modelo tipo BERT de Hugging Face (spaCy es alternativa válida por el enunciado si el modelo principal falla).
- Hardware: laptop personal, solo CPU. El NER corre únicamente sobre los pasajes recuperados (≤100), nunca sobre el corpus completo; toda inferencia se cachea y la caché se versiona.
- Utilerías auxiliares, con su alternativa si el profesor no las acepta (PV):

| Utilería | Papel | Alternativa |
| --- | --- | --- |
| `torch` | Requisito de `transformers` | Ninguna: sin ella no hay NER con modelo |
| `pyarrow` | Parquet | CSV comprimido con pandas |
| `streamlit` | App local de juicios, gold y gazetteer | Formularios por terminal con `input()` |
| `plotly` (+ `kaleido`) | Figuras del reporte (el profesor descartó matplotlib; ver `docs/decisiones.md`) | Tablas en lugar de figuras |
| `pypdf` | Contar páginas del PDF | `pdfinfo` de poppler |
| `python-pptx` | Generar láminas (P2) | Láminas a mano |
| `pytest` | Pruebas | `assert` en scripts |
| `pyyaml` | Configuración | JSON |
| `rich` | Demo en terminal | `print` con formato |
| `uv` | Entorno y lock | `pip` + `requirements.txt` |

- Reproducibilidad: desde un clon limpio, `make entrega` reconstruye todo con los insumos humanos versionados; `make resultados` reproduce todas las cifras sin pandoc ni TeX.

---

## 3. Kit de inicio, contratos y formatos de entrega

El kit vive en `kit/` sin cambios, con sus hashes SHA-256 en `docs/contratos_kit.md`. Las interfaces siguientes provienen de los PRD anteriores y son **PV hasta inspeccionar los archivos reales**; el hito H0 las verifica con pruebas de contrato sobre fixtures sintéticos (nunca con juicios o gold reales) y anota en `docs/contratos_kit.md` firmas, cabeceras, argumentos de CLI y comportamiento ante archivos vacíos. Una incompatibilidad bloquea solo la etapa afectada hasta tener un adaptador transparente; nunca se edita el evaluador.

### 3.1 `kit/corpus.py` (PV)

```python
cargar_corpus(forzar: bool = False) -> pd.DataFrame
# columnas: doc_id (int, 0..N-1), url, titulo, fecha (datetime64, puede ser NaT), texto
# cachea en kit/data/discursos.parquet

limpiar_basico(texto: str) -> str                                # normaliza espacios y saltos
partir_por_interlocutor(texto: str) -> list[tuple[str, str]]     # [(interlocutor, texto), ...]
ventanas(tokens: list[str], tam: int, paso: int) -> list[str]
segmentar_pasajes(df, tam=200, paso=150, min_tokens=40) -> pd.DataFrame
# columnas: passage_id (f"{doc_id}_{posicion}"), doc_id, fecha, titulo, posicion, interlocutor, texto
```

`RE_INTERLOCUTOR = r"^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ ,.\-\(\)]{2,80}):\s*"` con `re.MULTILINE`. Se reutilizan `limpiar_basico`, `partir_por_interlocutor` y `ventanas`; `segmentar_pasajes` se sustituye por una función propia (6.1) que conserva el esquema de columnas y de `passage_id`. Verificar en H0: asignación de `doc_id`, tipos de fecha, caché, y que `limpiar_basico` conserva los saltos que necesita el reconocimiento de interlocutores.

### 3.2 `kit/consultas.csv` (EX)

```
query_id,consulta,desde,hasta,pregunta_extraccion
```

Q1 a Q8 son intocables y se usan tal cual, sin reformular (EX, p. 2). El kit no se modifica: Q9 y Q10 se agregan en `data/consultas.csv` (copia del kit más dos filas) y todos los scripts leen de esa copia. Verificar en H0 que el contenido literal coincide con la tabla de la sección 5.1.

### 3.3 `kit/gazetteer_dependencias.csv` (EX)

```
nombre,siglas,tipo
```

Según el PRD 1.0 tiene 76 entradas con tipos `dependencia`, `organismo`, `organismo autónomo`, `empresa`, `empresa productiva del Estado`, `obra`, `organización empresarial`, `partido`, `organismo internacional`, `poder judicial` (PV: contar en H0). Convención: `tipo == "obra"` → etiqueta LOC; el resto → ORG. Las ampliaciones viven en `config/gazetteer_extendido.csv`.

### 3.4 `kit/evaluar.py` (EX, no se edita)

**IR:** `python kit/evaluar.py ir juicios_relevancia.csv ranking.csv` → `resultados_ir.csv`.

- Lee de `ranking.csv` solo `query_id, modelo, rango, passage_id`; ignora las demás columnas. Agrupa por `(query_id, modelo)` ordenando por `rango`.
- Lee de `juicios_relevancia.csv`: `query_id, doc_id, passage_id, relevante` (0/1).
- Pasaje no juzgado cuenta como no relevante. AP divide entre el total de relevantes del pool de esa consulta. Produce filas por consulta y modelo más una fila `PROMEDIO (MAP = AP)` por modelo.
- Verificar en H0: denominador de AP, listas con menos de k resultados, consultas sin relevantes, columnas reales de salida (`relevantes_recuperados`, `relevantes_en_pool`, `no_juzgados` según 1.0).

**IE:** `python kit/evaluar.py ie gold_entidades.csv entidades.csv` → `resultados_ie.csv`.

- Solo evalúa pasajes presentes en el gold. Coincidencia exacta de `(passage_id, tipo, inicio, fin)`.
- Métodos reconocidos: `regla`, `modelo`, `ambos`. `regla` se evalúa con filas `regla` + `ambos`; `modelo` con `modelo` + `ambos`; `combinado` con todas. Otro valor en `metodo` se descarta en silencio: el extractor solo emite esos tres.
- Verificar en H0: si deduplica entre consultas cuando un pasaje aparece en varias, cómo trata un pasaje gold sin entidades (no tendría filas, luego no se evaluaría: ver 6.11) y qué filas emite para tipos sin soporte.
- Como solo evalúa los pasajes del archivo gold recibido, el mismo evaluador sirve para el conjunto de selección del NER sin modificarlo.

### 3.5 Formatos de entrega (exactos)

Los seis archivos viven en la raíz del repo como exportaciones validadas de `salida/` y `anotaciones/`.

```csv
# ranking.csv (un solo archivo; modelo codifica modelo y variante; posicion se añade por EX p. 1)
query_id,modelo,variante,rango,passage_id,doc_id,fecha,posicion,puntaje
Q1,bm25_con_filtro,con_filtro,1,1532_7,1532,2021-06-14,7,18.4213

# juicios_relevancia.csv
query_id,doc_id,passage_id,relevante
Q1,1532,1532_7,1

# entidades.csv (exactamente estas 8 columnas, en este orden)
query_id,doc_id,passage_id,tipo,texto,inicio,fin,metodo
Q1,1532,1532_7,ORG,Fonatur,88,95,ambos

# gold_entidades.csv (y gold_seleccion.csv, mismo formato)
passage_id,tipo,texto,inicio,fin
1532_7,ORG,Fonatur,88,95

# resultados_ir.csv y resultados_ie.csv: salida íntegra del evaluador, sin renombrar columnas
```

- Valores de `modelo`: `tfidf_con_filtro`, `bm25_con_filtro`, `tfidf_sin_filtro`, `bm25_sin_filtro`; `variante` repite el sufijo. Una sola corrida del evaluador produce los cuatro promedios.
- Claves únicas: `(query_id, modelo, rango)` y `(query_id, modelo, passage_id)` en `ranking.csv`; `(query_id, passage_id)` en juicios; `(query_id, passage_id, tipo, inicio, fin)` en entidades; `(passage_id, tipo, inicio, fin)` en gold.
- `tipo` ∈ {PER, ORG, LOC, FECHA, MONTO}; `metodo` ∈ {regla, modelo, ambos}; `relevante` ∈ {0, 1}.
- CSV en UTF-8 sin BOM, separador coma, comillas dobles cuando el texto las requiera. Fechas ISO `AAAA-MM-DD`; ausencia como campo vacío.

### 3.6 Convenciones de offsets y de anotación

Los offsets son índices de carácter Python sobre el `texto` completo e inmutable del pasaje (incluida la marca de interlocutor reinyectada), `inicio` inclusivo y `fin` exclusivo. Para toda entidad: `0 <= inicio < fin <= len(texto)` y `texto[inicio:fin] == texto_entidad`. No son bytes ni unidades UTF-16: si la app usa JavaScript para seleccionar, convierte posiciones y prueba caracteres fuera del BMP. El preprocesamiento de IR nunca altera estos offsets.

Convenciones de anotación (aplican al gold, al conjunto de selección y al extractor; se fijan en `config/criterios_anotacion.md` antes de anotar y no cambian después):

| Tipo | Qué se anota | Convenciones |
| --- | --- | --- |
| PER | Nombres de funcionarios, empresarios, periodistas | Nombre completo presente en el texto como una sola entidad; se excluye el cargo adyacente: "secretario de Salud, Jorge Alcocer Varela" → `Jorge Alcocer Varela` |
| ORG | Dependencias, empresas, partidos, organismos internacionales, organizaciones empresariales | Nombre o sigla tal como aparece. Farmacéuticas y marcas de vacuna son ORG (D14). Entidad completa cuando contiene un lugar: ORG `Secretaría de Salud de Tabasco` sin LOC interno |
| LOC | Estados, municipios, países y obras con nombre propio | Tren Maya, AIFA, Dos Bocas, refinería Olmeca son LOC (EX, p. 3) |
| FECHA | Absolutas y relativas resolubles | Núcleo completo con modificador relativo cuando lo hay: `próximo 15 de enero`, `diciembre de 2021`, `15 de diciembre de 2023`; sin preposiciones ni artículos introductorios. `en 2019` → `2019` con precisión de año; un número de cuatro cifras sin contexto temporal no es FECHA. Un intervalo explícito (`del 1 al 15 de enero`) es una sola entidad; una enumeración produce entidades separadas |
| MONTO | Cantidades en pesos o dólares con su unidad | Incluye cifra, escala y moneda o símbolo: `20 mil millones de pesos`, `$1,200 millones`. No se recorta el `$`. Porcentajes, dosis, litros y elementos **no** son MONTO: van a cantidades auxiliares (D11) |

Entidades dentro de la marca de interlocutor: se anotan igual que en el cuerpo (`SECRETARIO DE SALUD, JORGE ALCOCER VARELA:` → PER `JORGE ALCOCER VARELA`). `PREGUNTA`, `INTERLOCUTOR`, `INTERLOCUTORA` y otras marcas genéricas no contienen entidades. Así el gold mide el efecto de las mayúsculas, una de las categorías de error que pide el enunciado. Spans que no se contienen pueden coexistir; cualquier excepción se escribe en la guía antes de cerrar el gold.

---

## 4. Decisiones de diseño y momentos de congelación

Cada decisión es DP salvo que se indique EX. Antes de su congelación se puede revisar con motivo documentado; después, un cambio crea una versión experimental nueva, declara qué invalida y protege las anotaciones anteriores. Nunca se cambian parámetros repetidamente para mejorar la cifra final.

| ID | Decisión | Justificación corta | Se congela |
| --- | --- | --- | --- |
| D01 | Python 3.11 como referencia, dependencias fijadas en `uv.lock`, `requirements.txt` exportado | Reproducibilidad; la rúbrica nombra `requirements.txt` | Antes de resultados oficiales |
| D02 | Unidad de recuperación: pasaje por intervención más ventanas de 200 palabras, paso 150, mínimo 40 (base del kit) | Discursos de 1 a 2 horas; la base equilibra cobertura y precisión. Sensibilidad descriptiva (OP) antes del pooling | Antes de rankings y juicios |
| D03 | La marca de interlocutor se reinyecta al inicio de `texto` **para la extracción** y se excluye de los tokens del índice mediante `inicio_cuerpo` | Es fuente de PER y ORG; repetida en cada ventana inflaría el tf de "secretario", "salud", "presidente" | Con D02 |
| D04 | Intervenciones de reporteros se conservan e indexan igual que las del presidente | La pregunta suele nombrar el tema; se mide su proporción en el corpus y en los top-10 | Con D02 |
| D05 | Limpieza de ruido antes de segmentar: acotaciones, separadores, encabezados repetidos, duplicados y reparación de fechas desde título y URL, todo contado y auditado | R01 califica el manejo del ruido; hacerlo antes de segmentar no rompe offsets | Antes de segmentar |
| D06 | Pool de relevancia = unión sin duplicados de los top-10 de las cuatro variantes (≤40 por consulta) | Ninguna variante se castiga por pasajes no juzgados | Antes del primer juicio |
| D07 | Relevancia temática: un pasaje es relevante por su contenido, sin importar su fecha. La ventana se aplica en una vista complementaria del análisis | Un criterio único para las cuatro variantes; separa el ruido temático del efecto temporal | Antes del primer juicio |
| D08 | "Mejor modelo" para la Tarea B = mayor MAP oficial entre `tfidf_con_filtro` y `bm25_con_filtro`, único para todas las consultas; empate exacto a BM25 | Objetivo y reproducible; no se elige por consulta a conveniencia | Antes de evaluar IR |
| D09 | Un NER principal fijado por criterios técnicos antes de abrir el gold. Comparación con un segundo NER solo con un conjunto de selección de 6 pasajes disjunto del gold (P1) | Elegir y reportar con los mismos datos da una cifra optimista | Antes de anotar el gold |
| D10 | Gold de 20 pasajes distintos, 2 por consulta, sorteados con semilla 42 del top-10 con filtro del ganador, anotados en modo ciego y desde cero | El enunciado pide 20 pasajes, al menos 2 por consulta; el modo ciego evita gold copiado del sistema | Antes de mostrar predicciones |
| D11 | MONTO representa dinero. Porcentajes, dosis, litros, elementos y beneficiarios van en `salida/cantidades_auxiliares.csv` con tipos PORCENTAJE y CANTIDAD, fuera de los cinco tipos evaluados | Coherente con la definición EX de MONTO; Q2, Q6 y Q8 se responden desde las auxiliares. PV con el profesor | Antes de anotar el gold |
| D12 | Fusión por coincidencia exacta de `(tipo, inicio, fin)` → `ambos`; solapes parciales y discrepancias de tipo se conservan como filas independientes y se cuantifican | Compatible con el evaluador sin esconder errores | Antes de evaluar IE |
| D13 | Span de FECHA incluye el modificador relativo (`próximo`, `pasado`, `este`) y excluye preposiciones; `en 2019` es FECHA de precisión año | El modificador cambia el significado; el enunciado cita "el próximo 15 de enero" | Antes de anotar el gold |
| D14 | Toda farmacéutica, marca de vacuna o mecanismo multilateral (Pfizer, BioNTech, AstraZeneca, CanSino, Sputnik V, Gamaleya, Sinovac, Moderna, Janssen, Johnson & Johnson, Abdala, Patria, COVAX) se anota ORG; el sustantivo genérico "vacuna" queda fuera del span | Regla determinista para Q2; la distinción producto/fabricante no es anotable con consistencia en habla transcrita | Antes de anotar el gold |
| D15 | Reglas, gazetteers y `criterios_anotacion.md` se congelan con la etiqueta git `reglas-congeladas` antes de abrir el gold. Todo cambio posterior conserva el F1 anterior y marca el nuevo como exploratorio | Evita sobreajustar las reglas al gold sin darse cuenta | Antes de anotar el gold |
| D16 | `entidades.csv` conserva las 8 columnas exactas; normalización y procedencia viven en `salida/entidades_enriquecidas.csv` | No romper el evaluador; las tablas necesitan valores comparables | Al implementar fusión |
| D17 | Tablas de respuesta con evidencia: cada valor respaldado cita pasaje y offsets; estados `respaldado_en_texto`, `ambiguo`, `contradictorio`, `no_encontrado` | Una coocurrencia no demuestra una relación; el enunciado pide valorar credibilidad | Antes de generar tablas finales |
| D18 | Reproducibilidad: hash del parquet del corpus, `revision` fija de modelos, caché NER versionada, `uv.lock`, manifiesto de ejecución | Sin esto "coinciden byte a byte" no está garantizado | Antes de resultados oficiales |
| D19 | Juicios, gold, selección y revisión de gazetteer en una app Streamlit local (CLI como alternativa); persistencia en CSV bajo `anotaciones/` | Offsets correctos, modo ciego, insumos humanos protegidos | Al implementar la app |
| D20 | Prioridades P0, P1, P2 por módulo; el núcleo (seis CSV y reporte mínimo) se entrega primero | El PRD completo excede el tiempo disponible; el núcleo no puede quedar en riesgo | Permanente |
| D21 | Reporte Markdown → PDF con pandoc y XeLaTeX; prosa redactada por el asistente desde resultados reales, validada sección por sección por el alumno y declarada en "Uso de IA" | 4 a 6 páginas sin código; transparencia sobre quién escribió qué | Al preparar entrega |
| D22 | Todo en español; Conventional Commits; scripts numerados en `scripts/`; `Makefile` con equivalentes Python en el README | Legible para humanos, agentes y el profesor | Permanente |

### 4.1 Pendientes de verificación (PV)

| ID | Pendiente | Comportamiento mientras se resuelve |
| --- | --- | --- |
| P01 | Interfaces, opciones y esquemas reales del kit | Inspeccionar en H0 con pruebas de contrato antes de integrar la evaluación |
| P02 | Q9, Q10, nombre, repo y estado de la entrega | Obtener del alumno; avanzar módulos independientes |
| P03 | Convención del curso para porcentajes | Aplicar D11 salvo aclaración antes del gold |
| P04 | Cómo trata el evaluador los pasajes gold sin entidades y los duplicados entre consultas | Caracterizar en H0; mantener métricas oficiales y diagnósticos separados |
| P05 | Plazo y zona horaria vigentes | Registrar la información del curso sin inventar prórrogas |
| P06 | Descarga, revisión y offsets del NER principal | Verificación técnica temprana en H5, sin usar el gold |
| P07 | Aceptación de las utilerías de 2.2 | Mensaje al profesor en fase 0; alternativa lista para cada una |

---

## 5. Consultas

### 5.1 Consultas obligatorias (EX, p. 2)

Se toman literalmente del archivo del kit y se cotejan con esta tabla; los saltos tipográficos del PDF no forman parte de las consultas.

| ID | Consulta | Desde | Hasta | Lo que debe responder la extracción |
| --- | --- | --- | --- | --- |
| Q1 | avances en la construcción del Tren Maya | 2020-01-01 | 2023-12-31 | Qué dependencias y empresas participan, en qué estados y con qué montos |
| Q2 | llegada y aplicación de vacunas contra el COVID-19 | 2020-12-01 | 2021-12-31 | Qué farmacéuticas, qué funcionarios y qué fechas y cantidades de dosis |
| Q3 | refinería de Dos Bocas en Tabasco | 2019-01-01 | 2022-12-31 | Qué organizaciones, qué personas responsables y qué montos de inversión |
| Q4 | aeropuerto Felipe Ángeles en Santa Lucía | 2019-01-01 | 2022-06-30 | Qué dependencia construye, qué lugares se mencionan y qué costos |
| Q5 | programa Sembrando Vida y apoyo a campesinos | 2019-01-01 | 2024-12-31 | Qué secretaría lo opera, en qué estados y con qué monto por beneficiario |
| Q6 | combate al huachicol y robo de combustible | 2018-12-01 | 2019-06-30 | Qué lugares, qué organizaciones y qué cifras de pérdidas o litros |
| Q7 | pensión universal para adultos mayores | 2018-12-01 | 2024-12-31 | Qué montos bimestrales, qué institución paga y qué fechas de aumento |
| Q8 | aumento al salario mínimo y acuerdo con empresarios | 2018-12-01 | 2024-01-31 | Qué organizaciones empresariales, qué porcentajes y qué montos diarios |

### 5.2 Q9 y Q10 · Descubrimiento guiado (script `00_descubrir_consultas.py`) · P0

Objetivo: ayudar al alumno a elegir dos temas con señal suficiente en el corpus, distintos entre sí y de Q1 a Q8, con ventana válida y pregunta que se pueda responder con entidades y cantidades auxiliares. Candidatos iniciales (editables en `config/candidatos_q9q10.yaml`; son sugerencias, no consultas elegidas):

| Tema | Términos semilla | Ventana sugerida | Pregunta de extracción sugerida |
| --- | --- | --- | --- |
| Guardia Nacional | guardia nacional, despliegue, elementos | 2019-01-01 a 2020-12-31 | Qué dependencias la integran, en qué estados se despliega, cuántos elementos y qué fechas |
| Insabi y sistema de salud | insabi, seguro popular, medicamentos | 2019-06-01 a 2021-12-31 | Qué instituciones participan, qué funcionarios, qué montos y qué fechas de arranque |
| Tren Interoceánico del Istmo | interoceánico, istmo, salina cruz, coatzacoalcos | 2020-01-01 a 2024-06-30 | Qué dependencias y empresas, qué lugares conecta, qué montos y fechas de inauguración |
| Reforma eléctrica y litio | reforma eléctrica, litio, cfe, generación | 2021-09-01 a 2022-12-31 | Qué organizaciones, qué funcionarios, qué porcentajes y montos |
| Aranceles y acuerdo migratorio con EUA | aranceles, trump, guardia, migrantes | 2019-05-01 a 2019-07-31 | Qué países y funcionarios, qué porcentajes, qué fechas y cifras de migrantes |
| Banco del Bienestar | banco del bienestar, sucursales | 2019-01-01 a 2023-12-31 | Qué institución, cuántas sucursales, en qué estados, con qué montos |
| Mexicana de Aviación | mexicana de aviación, aerolínea, marca | 2023-01-01 a 2024-06-30 | Qué dependencias, qué montos de compra, qué fechas y rutas |
| Caso Ayotzinapa | ayotzinapa, normalistas, comisión de la verdad | 2018-12-01 a 2023-12-31 | Qué organismos y funcionarios, qué fechas y qué lugares |

Para cada candidato el script calcula sobre pasajes: número de pasajes con al menos un término semilla, número de discursos distintos, distribución por año y tres pasajes de ejemplo de 300 caracteres. Salida: `salida/00_candidatos_q9q10.md`. No usa métricas del gold ni reformula Q1 a Q8.

El alumno elige dos y redacta `consulta`, `desde`, `hasta` y `pregunta_extraccion`. El asistente crea `data/consultas.csv` = kit + Q9 + Q10. Si la elección deja menos de dos pasajes disponibles para el gold, se resuelve antes de congelar consultas. `[VALIDAR]` la redacción final.

Regla (EX, p. 2): Q9 y Q10 participan en todo el protocolo: ranking, pool, juicios, selección del mejor modelo, muestra gold, tablas y valoraciones. Se califican dentro de los puntos de evaluación de IR e IE.

---

## 6. Especificación funcional por módulo

Paquete `src/mtx/` (minería de textos). Scripts de orquestación numerados en `scripts/`; cada script importa del paquete y la lógica no vive en los scripts. Cada módulo documenta entradas, salidas e invariantes.

```
src/mtx/
  __init__.py
  config.py            # rutas, constantes, semillas, carga de config/*.yaml, telemetría
  contratos.py         # esquemas de los CSV y validadores de columnas y claves
  adaptadores_kit.py   # envoltorios del kit; único punto de contacto con kit/
  corpus.py            # carga, limpieza de ruido, segmentación propia
  preproceso.py        # tokenizador, stoplist, stemmer
  indice.py            # índice invertido, postings, persistencia
  ranking.py           # TF-IDF, BM25, filtro de fecha, top-k, búsqueda libre
  pool.py              # pool de relevancia y validación de juicios
  muestreo.py          # muestra gold y conjunto de selección con emparejamiento global
  reglas.py            # regex FECHA y MONTO, cantidades auxiliares, gazetteers, regla de marca
  ner_modelo.py        # pipeline HF, chunking, caché, posproceso de spans
  fusion.py            # fusión reglas + modelo
  normalizacion.py     # fecha_iso, valor_num, moneda, canónicos
  evaluacion.py        # envoltorio de kit/evaluar.py, vista con ventana, análisis de errores
  respuestas.py        # tablas de respuesta con evidencia
  artefactos.py        # manifiesto, hashes, invalidación
  reporte.py           # tablas y figuras para el reporte
  laminas.py           # generación del pptx (P2)
  demo.py              # demo en terminal con rich
  app/                 # Streamlit: estado, juicios, gold, gazetteer, demo (P2)
    app.py
    vista_estado.py
    vista_juicios.py
    vista_gold.py
    vista_gazetteer.py
    vista_demo.py
    componentes.py     # resaltado desde offsets, búsqueda de spans, selección por tokens
```

### 6.1 Corpus, limpieza y segmentación (`corpus.py`, script `01_corpus_y_pasajes.py`) · P0

**6.1.1 Carga y huella.** `cargar_corpus()` del kit a través de `adaptadores_kit`. Como el kit no acepta una revisión del dataset, se registra en `data/corpus_meta.json`: SHA-256 de `kit/data/discursos.parquet`, número de filas, fecha de descarga y, si `huggingface_hub` la expone, el commit del dataset. Se conserva la asignación de `doc_id` del snapshot; nunca se reordena el corpus. `make validar` compara el hash y avisa si el corpus cambió. `salida/01_estadisticas_corpus.json`: número de discursos, textos vacíos, rango de fechas, discursos con `fecha` NaT o inválida, distribución de longitud en palabras (mínimo, mediana, media, máximo, percentiles 10 y 90), discursos sin marcas de interlocutor.

**6.1.2 Limpieza de ruido (D05).** `limpiar_ruido(df) -> tuple[pd.DataFrame, dict]`, antes de segmentar. Se conserva el texto de origen y se produce un texto canónico separado. Los patrones viven en `config/limpieza.yaml` para que el reporte los cite. Cada operación se cuenta por `doc_id` en `salida/01_auditoria_corpus.csv`.

1. **Normalización previa:** saltos CRLF a LF, Unicode NFC, espacios dentro de cada línea; se preservan los saltos que necesita `partir_por_interlocutor`.
2. **Acotaciones:** se eliminan las que no son habla: `(APLAUSOS)`, `(INAUDIBLE)`, `(RISAS)`, `(PROYECCIÓN DE VIDEO)` y similares, patrón `\((?:[A-ZÁÉÍÓÚÑÜ ]{3,40})\)`. Se cuentan por tipo.
3. **Separadores y encabezados repetidos:** líneas compuestas solo por guiones, asteriscos o `+`, y los encabezados fijos que se repiten al inicio (`VERSIÓN ESTENOGRÁFICA...`, `CONFERENCIA DE PRENSA DEL PRESIDENTE...`). El encabezado queda en `titulo`.
4. **Duplicados:** hash del texto normalizado (minúsculas, sin acentos, espacios colapsados). Entre duplicados exactos se conserva el menor `doc_id` y el resto se excluye de la segmentación. Casi duplicados: misma `fecha` y Jaccard ≥ 0.9 sobre shingles de 5 palabras; se excluyen con la misma regla, se listan en `salida/01_duplicados.csv` con su similitud y el alumno puede revertir cualquiera en `config/limpieza.yaml` (U12). Los `doc_id` no se renumeran.
5. **Reparación de fechas:** el enunciado advierte que `fecha` puede tener errores. Se extrae una candidata del `titulo` (regex de fecha en español) y de la `url` (`AAAA/MM/DD` o `AAAA-MM-DD`). Si `fecha` es NaT y hay candidata, se usa; si `fecha` cae fuera de [2018-12-01, 2024-09-30] y hay candidata dentro, se usa; si `fecha` y candidata difieren más de 3 días, se usa la del título y se marca. Si título y URL se contradicen, no se corrige y se señala. Columnas: `fecha_original`, `fecha_fuente` ∈ {`original`, `titulo`, `url`, `ninguna`}. Salida: `salida/01_fechas_reparadas.csv`. Nunca se inventa una fecha.
6. **Resumen:** `salida/01_limpieza.json` con los conteos de cada operación y el porcentaje de caracteres descartados, para la sección 2 del reporte.

**6.1.3 Segmentación propia** `segmentar(df, tam=200, paso=150, min_tokens=40, reinyectar_marca=True) -> pd.DataFrame` (D02, D03, D04).

1. `texto = limpiar_basico(texto_canonico)`.
2. `intervenciones = partir_por_interlocutor(texto)`. Un texto sin marcas es una intervención sin interlocutor.
3. Para cada `(quien, que)`: `toks = que.split()`; para cada `trozo` de `ventanas(toks, tam, paso)`: si tiene menos de `min_tokens` palabras se descarta y se cuenta con su interlocutor; si no, el texto del pasaje es `f"{quien}: {trozo}"` cuando `quien != ""` y `reinyectar_marca`, o `trozo` en otro caso.
4. `inicio_cuerpo = len(quien) + 2` si se reinyectó la marca, 0 si no. Invariante: `texto[inicio_cuerpo:] == trozo` y `texto[:inicio_cuerpo] == f"{quien}: "`.
5. `posicion` es un contador por discurso que solo avanza con pasajes conservados. `passage_id = f"{doc_id}_{posicion}"`.
6. `es_reportero = interlocutor in {"PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA"} or interlocutor.startswith("PREGUNTA")`; una marca desconocida no se etiqueta reportero.
7. Columnas: `passage_id, doc_id, fecha, fecha_original, fecha_fuente, titulo, url, posicion, interlocutor, texto, inicio_cuerpo, n_palabras, es_reportero, marca_reinyectada, texto_sha256, intervencion_id, token_inicio, token_fin`. `n_palabras` mide el texto completo visible y puede superar 200 por el prefijo. `intervencion_id`, `token_inicio` y `token_fin` ubican la ventana en su intervención para reconocer evidencia repetida entre ventanas solapadas.

Persistencia: `data/pasajes.parquet`. Determinista: dos corridas producen el mismo contenido (se verifica por hash de filas ordenadas en `tests/test_corpus.py`). Después de iniciar juicios, una nueva segmentación crea una versión experimental nueva; las anotaciones previas no se reasignan por posición.

**6.1.4 Intervenciones cortas.** `salida/01_descartes_cortos.csv`: intervenciones y ventanas descartadas por `min_tokens`, desglosadas por reportero o funcionario, con 20 ejemplos. Si las preguntas de reporteros descartadas superan el 10 % de sus intervenciones, el reporte lo discute como costo de D02.

**6.1.5 Experimento de sensibilidad (OP, P1, antes del pooling).** Configuraciones `(120, 90, 40)`, `(200, 150, 40)`, `(300, 225, 40)` y `(200, 150, 15)`: número de pasajes, longitud media, proporción de pasajes de reporteros, intervenciones descartadas, solape TF-IDF/BM25 en el top-10 con filtro y número de discursos distintos en el top-10. Sin juicios: describe el efecto, no demuestra qué segmentación es más relevante. Salida: `salida/01_sensibilidad_segmentacion.csv`. La configuración base se mantiene (D02).

**6.1.6 Criterios de aceptación.** `data/pasajes.parquet` sin `passage_id` duplicados y cada uno reconstruye `doc_id` y `posicion`; todo pasaje tiene `fecha` (puede ser NaT), `fecha_fuente` e `inicio_cuerpo` válido; ningún pasaje proviene de un discurso excluido; `corpus_meta.json`, `01_limpieza.json`, estadísticas y descartes generados; `uv run pytest tests/test_corpus.py` en verde, incluidos textos con varias marcas, sin marcas, acentos y saltos (T02).

### 6.2 Preprocesamiento (`preproceso.py`) · P0

```python
tokenizar(texto: str) -> list[str]
tokenizar_pasaje(texto: str, inicio_cuerpo: int) -> list[str]   # tokeniza solo texto[inicio_cuerpo:]
tokenizar_sin_stem(texto: str) -> list[str]                     # para mostrar el efecto del stemmer
```

1. Normalización Unicode NFC y minúsculas. `RE_TOKEN = re.compile(r"[a-záéíóúñü0-9]+(?:-[a-záéíóúñü0-9]+)?", re.IGNORECASE)`: conserva números y formas como `covid-19` mediante una política explícita de tokens alfanuméricos; la política se documenta y se prueba.
2. Stoplist = `nltk.corpus.stopwords.words("spanish")` ∪ lista mínima de respaldo versionada en `config/stopwords_es.txt` (si falta `nltk_data` se usa esa misma lista, nunca una distinta) ∪ stoplist de estenográfica en `config/stoplist_extra.txt`: `presidente, pregunta, interlocutor, interlocutora, gracias, bueno, entonces, vamos, pues, ustedes, nosotros, aquí, ahora, decir, digo, va, ir, andrés, manuel, lópez, obrador, mañanera, conferencia, prensa`. Se guarda el contenido efectivo y su hash. No se retiran siglas cortas ni nombres propios de forma indiscriminada.
3. Se descartan tokens de longitud ≤ 2 salvo que sean numéricos.
4. Stemming con `SnowballStemmer("spanish")`. Se documenta por qué stemming y no lematización (velocidad, sin dependencia de spaCy, suficiente para consultas cortas).
5. Los pasajes se indexan con `tokenizar_pasaje` (D03); las consultas con `tokenizar`. Ambos modelos usan los mismos tokens. No se aplica expansión por sinónimos a las consultas oficiales.

Se guarda `data/tokens.parquet` (`passage_id, tokens`) con la configuración congelada y su hash.

**Prueba de tokens de consulta.** `tests/test_preproceso.py` verifica los tokens de las diez consultas tras el preprocesamiento y `02_indice.py` los escribe en `salida/02_tokens_consultas.md` (originales y finales). La prueba falla si se pierde un término clave: "dos" y "bocas" (Q3), "santa" y "lucía" (Q4), "sembrando" y "vida" (Q5), "huachicol" (Q6), "mínimo" (Q8). Si un término clave cae en la stoplist, se quita de la stoplist y se documenta. Una consulta que quede sin tokens produce un aviso explícito, no un ranking engañoso. Se prueba además que `tokenizar_pasaje(texto, inicio_cuerpo) == tokenizar(texto[inicio_cuerpo:])` y que ningún token proviene solo de la marca.

### 6.3 Índice invertido (`indice.py`, script `02_indice.py`) · P0

Estructura: `dict[str, dict[int, int]]`, término → {índice interno de pasaje → tf}. Además `df[termino]`, `N`, `longitud[pasaje]` en tokens del cuerpo, `avgdl` y el mapa estable `idx ↔ passage_id`.

Persistencia: `data/indice.pkl` (pickle protocolo 5) y `data/indice_meta.json` (N, tamaño del vocabulario, avgdl, fecha de construcción, hash de `tokens.parquet` para invalidar la caché).

Verificación cruzada obligatoria: `CountVectorizer` con un analizador identidad definido a nivel de módulo (no un lambda, para poder persistir) sobre los mismos tokens; `tests/test_indice.py` comprueba para 50 términos aleatorios y para conteos conocidos de un fixture sintético que df y suma de tf coinciden (T03), incluidos nombres que aparecen solo en marcas.

El índice se ajusta una vez sobre todos los pasajes congelados. Filtrar por fecha no recalcula N, df, idf ni avgdl: la comparación temporal cambia el conjunto elegible, no la definición de los modelos.

Postings para el reporte (EX pide al menos tres): `salida/02_postings.md` con `tren`, `vacuna`, `refinería` y `huachicol` en su forma stemmed indicando el stem: df, idf (fórmula BM25), top-15 pasajes por tf con `passage_id`, `fecha` y 80 caracteres de contexto, señalando que es una muestra y que la lista completa está en el índice. También `salida/02_vocabulario_top.csv` (200 términos más frecuentes por df) para la discusión de la stoplist.

### 6.4 Ranking (`ranking.py`, script `03_ranking.py`) · P0

**TF-IDF con coseno.** `TfidfVectorizer(analyzer=identidad, sublinear_tf=True, smooth_idf=True, min_df=1, norm="l2")` sobre los tokens del cuerpo; `cosine_similarity(vec.transform([q_tokens]), X)`. `min_df=1` para que TF-IDF y BM25 vean el mismo vocabulario: con `min_df=2`, un término de consulta con df = 1 desaparecería de TF-IDF y seguiría puntuando en BM25. Fórmula para `tf > 0`:

- `tf_sublineal = 1 + ln(tf)`; `idf = ln((1 + N) / (1 + df)) + 1`; `w = tf_sublineal · idf`; normalización L2 y coseno. Un vector nulo produce similitud cero, nunca NaN.

Se persisten vectorizador y matriz (`data/tfidf.pkl`, `data/tfidf_X.npz`) y se prueba cargarlos en un proceso nuevo.

**BM25 propio.** Clase `BM25(k1=1.5, b=0.75)` sobre el índice invertido, variante con idf positivo:

- `idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5))`
- `score(q, p) = Σ_{t ∈ términos únicos de q} idf(t) · tf·(k1 + 1) / (tf + k1·(1 - b + b·dl/avgdl))`

Los términos repetidos de la consulta cuentan una vez; los ausentes aportan cero.

**Validación de BM25.** (a) Corpus sintético pequeño con puntajes calculados a mano (T04). (b) Consistencia con `rank_bm25`: `BM25Okapi` usa `ln((N - df + 0.5)/(df + 0.5))` con un piso epsilon para términos muy frecuentes, así que comparar rankings directos puede fallar sin bug. `tests/test_ranking.py` define una subclase de `BM25Okapi` que sobrescribe `_calc_idf` con la fórmula propia y compara, sobre 200 pasajes y 5 consultas, los puntajes con tolerancia absoluta 1e-6; además documenta que, sin la subclase, la diferencia se concentra en términos con df > N/2. `rank_bm25` queda solo como dependencia de desarrollo.

**Filtro de fecha.** Ventanas como días inclusivos: `desde <= fecha <= hasta`. Ambos límites ausentes equivalen a sin filtro; uno ausente deja ese lado abierto; `desde > hasta` o un límite inválido es error de entrada. `fecha` NaT queda fuera con filtro y dentro sin filtro, identificada como tal. Se seleccionan primero los pasajes elegibles y después se ordena: no se rellena con pasajes excluidos ni con `-inf` ni con ceros (U10). Se reporta cuántos pasajes excluye el filtro por consulta.

**Top-k y desempates.** `k = 10`. Orden por la tupla `(-puntaje, doc_id, posicion)` con `doc_id` y `posicion` enteros (U9). No se redondea antes de ordenar; el CSV guarda 6 decimales. Para consultas oficiales se devuelve `min(10, n_elegibles)`; las excepciones a 400 filas llevan conteo y motivo. Puntajes cero se marcan `sin_senal_lexica` en el detalle y no se presentan como evidencia de relevancia. Una consulta libre vacía devuelve estado explicativo y ninguna fila.

**Salidas.**

- `salida/ranking.csv` → copia en la raíz `ranking.csv` (sección 3.5, 9 columnas).
- `salida/03_ranking_detalle.csv`: lo mismo más `interlocutor`, `es_reportero`, `titulo`, `sin_senal_lexica` y `texto` recortado a 400 caracteres.
- `salida/03_solape_modelos.csv`: por consulta, intersección de top-10 entre TF-IDF y BM25 con filtro, y entre con y sin filtro por modelo; discursos distintos por top-10.
- `salida/03_excluidos_por_filtro.csv`: por consulta, cuántos pasajes del top-10 sin filtro caen fuera de la ventana o tienen fecha desconocida, con sus fechas.

**Búsqueda libre.** `buscar(consulta, desde=None, hasta=None, modelo="bm25", k=10) -> tuple[pd.DataFrame, dict]` para la demo y la app; devuelve resultados y estado.

**Criterios de aceptación (bloqueantes).**

- Las cuatro variantes producen 10 filas por consulta para las 10 consultas (400 filas) o la excepción está justificada.
- Para Q3 el top-10 de BM25 con filtro contiene al menos un pasaje con "refinería" o "Pemex"; para Q1 al menos uno con "Tren Maya"; para Q6 al menos uno con "huachicol" (prueba lenta en `tests/test_ranking.py`).
- TF-IDF y BM25 no producen rankings idénticos en todas las consultas. Un ranking igual es un resultado a investigar, no una prueba automática de error.
- Modificar solo la marca de un pasaje no altera puntajes ni orden para un cuerpo fijo (D03).
- Pruebas de fecha en límites exactos, ausente, ventana abierta e invertida (T05); cero, tres y diez candidatos y términos desconocidos (T06).
- `python kit/evaluar.py ir` corre contra `ranking.csv` con un `juicios_relevancia.csv` sintético sin lanzar excepción.

### 6.5 Pool y juicios de relevancia (`pool.py`, app `vista_juicios.py`, script `04_pool.py`) · P0

**Pool (D06).** Por consulta: unión sin duplicados de los `passage_id` de las cuatro variantes. Tamaño esperado de 15 a 40 por consulta; un pasaje compartido entre consultas recibe un juicio independiente para cada una. `salida/04_pool.csv`: `query_id, passage_id, doc_id, fecha, en_ventana, variantes (separadas por "|"), mejor_rango_tfidf, mejor_rango_bm25, texto, texto_sha256`. La procedencia se guarda para auditoría pero se oculta al anotador. Orden de presentación aleatorio con semilla 42 por consulta sobre la lista de IDs ordenada.

Se congelan corpus, consultas, configuración IR, rankings, pool y criterio antes del primer juicio. Cualquier cambio del pool invalida su cierre.

**Criterio de relevancia (D07).** Fijado por el alumno en `config/criterios_relevancia.md` antes de empezar `[VALIDAR]`. Propuesta: "un pasaje es relevante si trata directamente del tema de la consulta y aporta al menos un dato sustantivo que ayudaría a responder su pregunta de extracción. El juicio es temático: la fecha del pasaje y el modelo que lo recuperó no cuentan. Un saludo o una coincidencia aislada de términos no basta". La ventana se aplica después, en el análisis (6.6).

**App de juicios (pestaña "Juicios").**

- Barra lateral: selector de consulta, progreso por consulta y global, botón "Guardar".
- Cuerpo: consulta en grande; `pregunta_extraccion` como ayuda; pasaje completo con resaltado de los términos de la consulta (match por stem sobre el token original); metadatos `doc_id`, `titulo`, `interlocutor`. La fecha se muestra, pero el criterio en pantalla recuerda que no cuenta.
- Botones: **Relevante (1)**, **No relevante (0)**, **Omitir por ahora**, **Anterior**. "Sin juzgar" es distinto de 0.
- No muestra puntajes, rangos ni variante (ciego al modelo).
- Autoguardado atómico en `anotaciones/juicios_relevancia.csv` tras cada clic, con historial de revisión; reanudable; detecta edición desde dos pestañas.

**Validador** `validar_juicios()` (también `make validar`): todos los pasajes del pool tienen exactamente un juicio en {0, 1}; ningún pasaje fuera del pool; hashes de texto coinciden; cada consulta tiene al menos un relevante (si no, aviso: AP indefinido para esa consulta, se discute en el reporte, no se altera ningún juicio); columnas exactas. Exporta a la raíz `juicios_relevancia.csv`.

**Tiempo estimado para el alumno:** 150 a 400 pasajes × 40 segundos ≈ 2 a 4.5 horas. Se mide un lote inicial para ajustar. Si no alcanza, recorte 5 de 12.4 declarado antes de interpretar resultados.

### 6.6 Evaluación de IR (`evaluacion.py`, script `05_evaluar_ir.py`) · P0

1. Ejecuta `python kit/evaluar.py ir juicios_relevancia.csv ranking.csv` vía `subprocess` con los argumentos verificados en H0 y guarda `resultados_ir.csv` en la raíz y en `salida/`, junto con entrada, salida, hashes y registro de ejecución. Esta es la cifra oficial (relevancia temática).
2. **Vista con ventana (complementaria).** `salida/05_juicios_con_ventana.csv` con `relevante_ventana = relevante AND en_ventana` (fecha desconocida no cumple la ventana) y el mismo evaluador sobre él: `salida/05_resultados_ir_ventana.csv`. Las dos vistas separan cuánto ruido temático quita el filtro y cuántos pasajes fuera de ventana deja pasar la variante sin filtro. Se rotula como complementaria: cambian el criterio y el denominador de AP; nunca sustituye a `resultados_ir.csv`. Se cuentan por consulta los relevantes temáticos dentro y fuera de la ventana y los de fecha desconocida.
3. `salida/05_ir_por_consulta.csv` en formato ancho (consulta × variante para P@5, P@10, AP, soporte, juzgados y no juzgados) y `salida/05_ir_ganador_por_consulta.csv`: ganador por AP con filtro, diferencia, y etiquetas **calculadas por el script**: longitud en tokens tras preprocesar (larga o corta respecto a la mediana de las diez), número de términos con df alto, presencia de siglas o nombre propio, sinónimos conocidos (`config/sinonimos_consultas.yaml`: huachicol ↔ robo de combustible; adultos mayores ↔ pensión del Bienestar; AIFA ↔ Santa Lucía ↔ Felipe Ángeles; Dos Bocas ↔ refinería Olmeca). El texto del análisis se escribe después de ver estas etiquetas.
4. `mejor_modelo` = argmax MAP oficial entre `tfidf_con_filtro` y `bm25_con_filtro`; empate exacto a BM25 (D08). Se escribe `data/mejor_modelo.json` con modelo, MAP, alternativa, su MAP, versión de rankings y juicios. Si la diferencia es menor a 0.01, se marca y se comenta en el reporte sin cambiar la regla.
5. Figuras (plotly con exportación PNG por kaleido, estilo sobrio, una paleta, títulos en mayúscula inicial): `reporte/figuras/ir_map_por_modelo.png`, `ir_ap_por_consulta.png`, `ir_con_vs_sin_filtro.png`.
6. Texto base para el análisis (EX, p. 2): en qué consultas gana cada modelo, consultas largas frente a cortas según las etiquetas, sinónimos, con y sin filtro en las dos vistas, y en qué consultas ayudarían embeddings densos (sin implementarlos). Las cifras describen esta colección y no se presentan como generalización.

**Criterios de aceptación.** `resultados_ir.csv` con 10 consultas × 4 variantes más 4 filas de promedio; `no_juzgados == 0` en las cuatro variantes; ninguna consulta con cero relevantes sin nota en el reporte; horizonte de evaluación (AP sobre top-10) documentado.

### 6.7 Reglas y gazetteers (`reglas.py`, script `06_reglas.py`, `tests/test_reglas.py`) · P0

Las reglas trabajan sobre el `texto` canónico completo, con mayúsculas y acentos, nunca sobre los tokens de IR. Al terminar este módulo y antes de abrir el gold se crea la etiqueta git `reglas-congeladas` (D15).

**6.7.1 Regex FECHA.** Con `fin` exclusivo y sin espacios colgantes.

Positivos (span esperado):

- `15 de diciembre de 2023`, `primero de enero de 2020`, `1 de septiembre del 2021`
- `enero de 2021`, `diciembre del 2019`
- `15/12/2023`, `1/1/19` (año de dos dígitos: se detecta y se normaliza solo con regla de siglo documentada; si es ambiguo, `fecha_iso` queda vacía)
- `el próximo 15 de enero` → `próximo 15 de enero`; `el pasado 20 de noviembre` → `pasado 20 de noviembre`; `este 1 de julio` → `este 1 de julio` (D13)
- `en diciembre de 2021` → `diciembre de 2021`
- `en 2019`, `el año 2019`, `desde 2019` → `2019` con precisión de año (D13)
- `del 1 al 15 de enero de 2021` → una sola entidad de intervalo

Negativos: `15 personas`, `página 15`, `2 horas`, `15 de los 32 estados`, `15 de cada 100`, `2019` sin contexto temporal, `31 de febrero` (día imposible: se rechaza en normalización, se registra como detección no resoluble).

No cubiertos (se documentan): rangos de años como `de 2019 a 2024` (se emiten dos FECHA de año, no un intervalo), fechas completamente en palabras (`quince de enero`).

**6.7.2 Regex MONTO.** Positivos:

- `20 mil millones de pesos`, `2 mil 500 millones de pesos`, `1,200 millones de pesos`, `$1,200 millones`, `$ 5 mil`, `5 mil pesos`, `500 pesos`, `2 mil millones de dólares`, `100 millones de dólares`, `1.5 billones de pesos`
- `6 mil 300 pesos`, `mil 200 pesos`, `un millón de pesos`, `dos mil millones de pesos`

Negativos: `20 mil personas`, `15 millones de dosis`, `3 millones de árboles`, `20 por ciento` y `20%` (son PORCENTAJE auxiliar, D11), `página 20`, y ninguna coincidencia que empiece a mitad de una cifra (`1500 pesos` produce un solo span, nunca `500 pesos`).

No cubiertos (se documentan): separador de miles con punto (`1.200 pesos`, ambiguo con decimales; queda sin valor numérico) y cifras completamente en palabras más allá de las escalas (`trescientos cincuenta pesos`).

Patrón semilla (se extiende hasta pasar la suite; no se entrega sin probar):

```python
NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
PALABRA_NUM = r"un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|cien"
# "20 mil", "2 mil 500", "dos mil", "mil 200", "mil"
CIFRA = rf"(?:(?:{NUM}|{PALABRA_NUM})(?:\s+mil(?!\w)(?:\s+(?:{NUM}))?)?|mil(?!\w)(?:\s+(?:{NUM}))?)"
ESCALA = r"(?:\s+(?:millones|millón|billones|billón))?"
MONEDA = r"\s+(?:de\s+)?(?:pesos|dólares|dolares)"
LIMITE_IZQ = r"(?<![\w$.,])"
RE_MONTO = rf"{LIMITE_IZQ}(?:\$\s?{CIFRA}{ESCALA}(?:{MONEDA})?|{CIFRA}{ESCALA}{MONEDA})"
RE_PORCENTAJE = rf"{LIMITE_IZQ}(?:{NUM})\s*(?:por\s+ciento|%)"
# compilar con re.IGNORECASE
```

**6.7.3 Cantidades auxiliares (D11, no son entidad del examen).** `RE_PORCENTAJE` y `RE_CANTIDAD` para `N millones de dosis`, `N mil elementos`, `N litros`, `N sucursales`, `N hectáreas`, `N beneficiarios`, `N sembradores`, `N kilómetros`. Van a `salida/cantidades_auxiliares.csv` (`query_id, passage_id, texto, inicio, fin, tipo_aux, valor_num, unidad, estado_normalizacion, regla_id`) y **nunca** a `entidades.csv`. Alimentan Q2 (dosis), Q6 (litros), Q8 (porcentajes), Q5 y Q9.

**6.7.4 Gazetteer ORG extendido.**

- Base: `kit/gazetteer_dependencias.csv`.
- Minería (`minar_siglas(pasajes)`): patrón `Nombre Largo (SIGLAS)` con nombre de 2 a 8 palabras con inicial mayúscula o preposiciones y siglas de 2 a 8 mayúsculas; más frecuencia de tokens todo en mayúsculas de 3 a 7 letras **del cuerpo** (desde `inicio_cuerpo`) que no estén en la stoplist. Salida: `salida/06_siglas_candidatas.csv` (`sigla, nombre_propuesto, frecuencia, ejemplo`).
- Revisión del alumno en la pestaña "Gazetteer" (o editando el CSV validado): aceptar, corregir tipo (ORG, LOC, descartar) y nombre. Resultado: `config/gazetteer_extendido.csv` con `nombre, variantes, siglas, tipo, etiqueta (ORG|LOC), origen (kit|minado|manual), evidencia`. La extensión se justifica por cobertura útil, sin cuota; se mide entradas base, nuevas, rechazadas y cobertura en los resultados. `[VALIDAR]`.
- Entradas que deben existir (se verifican en test): IMSS, ISSSTE, Pemex, CFE, Sedena, Semar, Conagua, Fonatur, Insabi, Cofepris, Birmex, Pfizer, AstraZeneca, CanSino, Sputnik V, COVAX, Coparmex, CCE, Concanaco, Conasami, Morena, PAN, PRI, PRD, ONU, OMS, OPS, FMI, Banco Mundial, Banxico, SAT, Guardia Nacional, Secretaría del Bienestar, STPS, SICT, Sener, Sedatu, Fonatur, Grupo Carso, ICA.

**6.7.5 Gazetteer LOC.** `config/gazetteer_loc.csv`: las 32 entidades federativas con variantes (Ciudad de México, CDMX; Estado de México, Edomex; Michoacán, Michoacán de Ocampo; Veracruz, Veracruz de Ignacio de la Llave; Coahuila, Coahuila de Zaragoza; y las demás), municipios y lugares de las consultas (Palenque, Cancún, Tulum, Mérida, Chetumal, Escárcega, Tula, Salamanca, Minatitlán, Salina Cruz, Coatzacoalcos, Santa Lucía, Istmo de Tehuantepec), obras (Tren Maya, Dos Bocas, refinería Olmeca, AIFA, Aeropuerto Internacional Felipe Ángeles, Tren Interoceánico, Corredor Interoceánico) y países (Estados Unidos, Washington, China, Rusia, India, Argentina, Cuba). Las obras se etiquetan LOC (EX).

**6.7.6 Regla de marca de interlocutor (PER y ORG por regla, OP recomendada).** Se analiza `texto[:inicio_cuerpo]`: si contiene coma, lo que sigue a la última coma y tiene 2 a 5 palabras es PER (`JORGE ALCOCER VARELA`); `PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR` → PER `ANDRÉS MANUEL LÓPEZ OBRADOR` mediante una lista de cargos conocidos, no suponiendo que cualquier secuencia tras la coma es una persona; si no contiene coma y coincide con el gazetteer, es ORG. `PREGUNTA`, `INTERLOCUTOR(A)` no generan entidad. Coherente con la convención de 3.6. La procedencia `marca` se conserva para medir errores en el prefijo.

**6.7.7 Motor de coincidencia del gazetteer.** Patrones con metacaracteres escapados, ordenados por longitud descendente; límites de palabra que respetan acentos (`(?<![\wáéíóúñü])...(?![\wáéíóúñü])`); siglas de ≤5 caracteres se buscan sensibles a mayúsculas, el resto insensible; dentro del gazetteer gana la coincidencia más larga. Se admite coincidencia con el texto en mayúsculas de la marca.

**6.7.8 Resolución de colisiones entre fuentes de reglas.** Ante solape entre dos fuentes se conserva el span más largo (`fin - inicio`); ante empate, la jerarquía determinista `regex_fecha > regex_monto > gazetteer_loc > gazetteer_org > marca`. Los solapes suprimidos se cuentan en `salida/06_colisiones_reglas.csv`.

**6.7.9 API.** `extraer_reglas(texto: str, inicio_cuerpo: int) -> list[Entidad]` con `Entidad` dataclass `tipo, texto, inicio, fin, metodo="regla", fuente ("regex_fecha"|"regex_monto"|"gazetteer_org"|"gazetteer_loc"|"marca"), en_marca (bool)`. Invariante en tests: `texto_pasaje[inicio:fin] == texto`.

**6.7.10 Suite `pytest` (bloqueante).** Todos los casos de 6.7.1 a 6.7.3 como pruebas parametrizadas (positivos con span exacto, negativos con cero coincidencias, valores normalizados), gazetteer (longest match, siglas sensibles a mayúsculas, acentos, sigla coincidente con palabra común), regla de marca, colisiones, e invariante de offsets sobre 200 pasajes reales incluidas las marcas (T11). Los ejemplos de prueba son sintéticos y no se presentan como anotaciones del corpus. Los casos que fallan se guardan para explicarlos, no se maquillan. El módulo no se da por terminado hasta `uv run pytest tests/test_reglas.py` en verde.

### 6.8 NER con modelo (`ner_modelo.py`, script `07_ner.py`) · P0 (un modelo), P1 (comparación)

**Modelo principal (D09, U22):** `mrm8488/bert-spanish-cased-finetuned-ner` (PER, ORG, LOC, MISC). **Candidato 2 (P1):** `PlanTL-GOB-ES/roberta-base-bne-capitel-ner` (PER, ORG, LOC, OTH). Ambos en `config/ner.yaml` con `revision` fija registrada en la primera descarga. Las métricas publicadas en sus fichas no son resultados de este proyecto.

**Verificación previa al gold (P06).** Pesos de clasificación de tokens, mapa real de etiquetas, tokenizador rápido con offsets, compatibilidad del entorno y funcionamiento sobre ejemplos de desarrollo independientes de la muestra gold. Si el principal falla, se elige y verifica otro NER español (incluido spaCy `es_core_news_lg`, permitido por el enunciado) antes de abrir el gold, se registra el motivo y se vuelve a congelar. Un modelo base sin cabeza NER afinada no es reemplazo válido.

**Inferencia.** `transformers.pipeline("token-classification", model=..., revision=..., aggregation_strategy="simple", device=-1)`. Mapa de etiquetas solo si existen en el modelo: `PER|PERSON → PER`, `ORG → ORG`, `LOC|GPE → LOC`; `MISC|OTH` se descarta pero se cuenta (las obras suelen caer ahí; el gazetteer las recupera; va al análisis de errores). El mapa no se cambia por inspección de errores del gold. Lotes de 8, ajustados según medición.

**Pasajes largos.** Se respeta el límite real del modelo descontando tokens especiales. Ventanas de subtokens con solapamiento explícito y offsets proyectados al texto canónico; partir por oraciones (`[.!?]\s+`) es una optimización, no la única defensa ante una oración muy larga. Se comprueba que todo el texto queda cubierto y que el último fragmento no se pierde. Entidades duplicadas en el traslape se deduplican por span; ante conflicto se prioriza la no cortada por el borde y después la confianza (que es un puntaje, no una probabilidad calibrada). Entidad en el borde de ventana es caso de prueba (T12).

**Posproceso de spans (U15).** Recorte de espacios y puntuación en los extremos sin eliminar caracteres semánticos (`$` se conserva). Unión intrapalabra (`fin_1 == inicio_2`) siempre. Unión interpalabra de spans adyacentes del mismo tipo separados por un solo espacio (`López` + `Obrador`) como posproceso documentado: se guardan la predicción cruda y la unida, se registra cada unión en `salida/07_uniones_spans.csv` y el reporte mide el efecto. El invariante `texto[inicio:fin] == texto_entidad` se verifica en cada fila.

**Caché versionada (D18).** `data/cache_ner/{modelo_slug}@{revision_corta}/{passage_id}.json`, con clave que depende de texto canónico (`texto_sha256`), modelo y revisión, tokenizador, fragmentación y parámetros de inferencia; la capa de posproceso lleva su propia versión para poder cambiarla sin reinferir. Nunca se reinfiere un pasaje cacheado; `--forzar` lo invalida. La caché se versiona en git (≤100 pasajes × 2 modelos, unos cientos de KB), así que `make resultados` desde un clon limpio no descarga modelos.

**Ámbito.** Solo los pasajes únicos del top-10 con filtro del mejor modelo de IR (≤100), que incluyen los del gold y del conjunto de selección. La inferencia puede correr antes del cierre del gold si permanece oculta al anotador. Tiempo esperado en CPU: 1 a 3 minutos por modelo; se mide primera carga y con caché por separado.

**Comparación y selección (P1).** Para cada candidato se produce `salida/entidades_{slug}.csv` (solo método modelo) y se evalúa contra `anotaciones/gold_seleccion.csv` (6 pasajes disjuntos del gold, 6.11) con `kit/evaluar.py ie`; gana el de mayor F1 en `metodo == modelo, tipo == TODOS`; empate al principal. Se fija en `data/modelo_ner.json` (`modelo, revision, f1_seleccion, f1_seleccion_alternativa, criterio`) **antes** de usar `gold_entidades.csv`. Los F1 de ambos sobre el gold de 20 se presentan solo como información: la elección ya está hecha y no cambia. Si no hay conjunto de selección, se usa el principal y el reporte declara que la elección fue técnica.

**Experimento de capitalización (OP, P2).** Correr el modelo sobre una versión del pasaje con la marca en capitalización de título y medir el cambio en PER/ORG dentro de la marca. Exige mapa de offsets o verificación explícita de correspondencia; no se supone que la longitud se conserva. Sin este experimento, el reporte describe dónde ocurren los errores en la marca pero no afirma causalidad de las mayúsculas.

### 6.9 Fusión y consolidación (`fusion.py`, script `08_extraer.py`) · P0

Se extrae una sola vez por pasaje y después se asocian las entidades a todas las consultas que lo recuperaron (la clave pública incluye `query_id`). Regla (D12): misma `(passage_id, tipo, inicio, fin)` en reglas y modelo → una fila con `metodo = ambos`; solo reglas → `regla`; solo modelo → `modelo`. Solapes parciales y discrepancias de tipo se conservan como filas independientes, se cuantifican en `salida/08_solapes_parciales.csv` y alimentan el análisis de errores. No se borran falsos positivos a partir del gold. Se verifica en H0 si el evaluador deduplica por pasaje; si necesita una vista única, se exporta por adaptador documentado conservando el CSV completo (T08, T13).

Salidas:

- `entidades.csv` (raíz y `salida/`), 8 columnas exactas, ordenado por `query_id, passage_id, inicio`, sin filas duplicadas en la clave.
- `salida/entidades_unicas.csv`: entidades por pasaje sin repetir asociaciones a consultas.
- `salida/entidades_enriquecidas.csv`: las 8 columnas más procedencia (`fuentes`, `en_marca`, `modelo_id`, `modelo_revision`, `puntaje_modelo`, `version_extractor`), identidad (`canonico`, `texto_normalizado`, `estado_identidad`), tiempo (`fecha_iso`, `fecha_inicio`, `fecha_fin`, `precision_fecha`, `fecha_relativo`, `fecha_ancla`, `resuelta_desde_ancla`, `estado_fecha`) y dinero (`valor_num`, `valor_min`, `valor_max`, `moneda`, `escala`, `estado_monto`). Los campos no aplicables quedan vacíos; `fuentes` puede contener varias procedencias para `ambos`.

### 6.10 Normalización prudente (`normalizacion.py`) · P0 (MONTO, FECHA absoluta, ORG/LOC), P2 (fechas relativas, vínculo de personas)

Representaciones auxiliares sin modificar los spans originales. El normalizador recibe texto, span, contexto y fecha ancla, no solo la cadena.

- **FECHA:** `fecha_iso` en `AAAA-MM-DD`, `AAAA-MM` o `AAAA` según `precision_fecha` (día, mes, año, intervalo). `diciembre de 2021` no se convierte en un día inventado. Se validan días, bisiestos y orden de intervalos. **Relativas (P2):** `próximo`/`pasado` se resuelven con la `fecha` del discurso como ancla solo cuando es válida (siguiente o anterior ocurrencia estricta del día y mes), con `resuelta_desde_ancla = True`; sin modificador ni año, el año del discurso si hay ancla; sin ancla, queda parcial.
- **MONTO:** `Decimal` para el cálculo y representación decimal estable al exportar. `valor_num` en unidades, `moneda` ∈ {MXN, USD, vacío}, `escala` ∈ {uno, mil, millones, mil_millones, billones}. Parser de cifras habladas (`2 mil 500 millones` → 2500000000). `billón` se interpreta como 10^12 (escala larga) y se marca ambiguo si el contexto lo contradice. `$` sin evidencia no fija moneda. Expresiones ambiguas quedan sin valor numérico (`estado_monto = ambiguo`). No se convierten monedas ni se suman inversiones entre pasajes automáticamente.
- **PORCENTAJE y CANTIDAD:** `20%` guarda 20 con unidad porcentaje, no 0.20; las cantidades conservan unidad y escala.
- **ORG/LOC:** `canonico` por equivalencias verificadas del gazetteer extendido (siglas → nombre); `texto_normalizado` en minúsculas sin acentos para agrupar.
- **PER (P2):** `texto_normalizado`; se vinculan alias solo cuando uno es sufijo del otro y aparecen en el mismo pasaje, con `estado_identidad = vinculado_por_sufijo`; compartir apellido no basta para unir personas.

`tests/test_normalizacion.py` cubre al menos 15 casos de montos, 10 de fechas (incluidas inválidas y de dos dígitos) y la no mezcla entre normalización y evaluación por span exacto.

### 6.11 Gold de evaluación y conjunto de selección (`muestreo.py`, script `08b_muestra_gold.py`, app `vista_gold.py`) · P0

**Muestras.** Ambas se sortean con semilla 42 del top-10 con filtro del mejor modelo, **antes** de mostrar predicciones, y se congelan con los hashes de texto:

- **Gold de evaluación (D10, EX):** 20 pasajes distintos, 2 por consulta. Como un pasaje puede estar en el top-10 de varias consultas, las dos plazas por consulta se asignan con un emparejamiento global reproducible que garantiza 20 IDs únicos (T09); un sorteo independiente por consulta no lo garantiza. Si no existe asignación completa, se muestran las consultas en conflicto y se registra la excepción; no se amplía al top-20 ni se duplican IDs en silencio. Se distribuyen rangos altos y bajos para no medir solo los más evidentes. Manifiesto: `anotaciones/muestra_gold.csv` (`query_id, passage_id, doc_id, texto_sha256, semilla, version_muestra`).
- **Conjunto de selección (P1, solo si se comparan NER):** 6 pasajes adicionales, disjuntos del gold, de 6 consultas distintas sorteadas entre los restantes. `anotaciones/muestra_seleccion.csv`. Se anota primero, sirve solo para elegir el modelo NER y no entra en `resultados_ie.csv`.

**Sustitución de pasajes (U13).** Solo por criterio objetivo: menos de 25 palabras de contenido (tokens del cuerpo sin stoplist), más de la mitad de sus palabras en la lista de fórmulas de protocolo de `config/protocolo.txt` (saludos, agradecimientos, despedidas), o causa técnica (texto corrupto). "No tiene entidades" nunca es motivo. El sustituto es el siguiente sorteado con la misma semilla en la misma consulta y el cambio se registra en `docs/decisiones.md` antes de ver predicciones. Se permite cerrar un pasaje con cero entidades.

**Pestaña "Gold" de la app (D19).**

- Modo ciego: Gold, Demo y paneles de errores no muestran predicciones de la muestra bajo ninguna circunstancia hasta que el alumno cierra el gold con un botón que escribe `anotaciones/cierre_gold.json` (hashes de muestra, textos, protocolo y gold, fecha). No se precargan entidades del sistema como borrador.
- Selector de conjunto: "Selección" (6, se anota primero) o "Evaluación" (20).
- **Modo principal, búsqueda por texto:** el alumno escribe el texto exacto; la app lo busca en el pasaje y, si aparece más de una vez, muestra cada aparición con 40 caracteres de contexto para elegir. No se infiere el offset por la primera coincidencia.
- **Modo secundario, selección por tokens:** texto renderizado token por token (`re.finditer(r"\S+")` con offsets reales); clic en el primer y último token; casilla "recortar puntuación final" activada por defecto que nunca quita `$`. Solo para casos difíciles: con 250 tokens por pasaje un botón por token provoca recargas lentas.
- Selector de tipo (PER, ORG, LOC, FECHA, MONTO), botón "Agregar", tabla de anotaciones con borrar por fila y edición de tipo y límites, botón "Pasaje revisado completo".
- La marca de interlocutor se muestra resaltada en gris para recordar que sus entidades también se anotan.
- Barra lateral: convenciones (3.6 y `config/criterios_anotacion.md`), progreso por conjunto y por consulta, contador por tipo.
- Autoguardado atómico con respaldo y número de revisión en `anotaciones/gold_seleccion.csv`, `anotaciones/gold_entidades.csv` y `anotaciones/estado_gold.csv` (`passage_id, texto_sha256, estado, n_entidades, revision`); validación en vivo del invariante, duplicados y anidamiento; detección de edición desde dos pestañas. HTML escapado y renderizado desde offsets.

**Pasajes sin entidades (P04).** El evaluador solo evalúa pasajes presentes en el CSV gold, así que un pasaje revisado con cero entidades no genera filas y desaparece de la métrica oficial. Se registra cuántos pasajes evalúa realmente, se conserva la cifra oficial sin modificarla y se añade en `salida/09_evaluacion_20_ids.csv` una evaluación complementaria sobre los 20 IDs del manifiesto que cuenta los falsos positivos en pasajes vacíos. No se inventa una entidad centinela ni se sustituyen negativos.

**Validador** `validar_gold()`: 20 IDs distintos con 2 por consulta según el manifiesto (no según los IDs con filas), todos en estado `cerrado`; 6 IDs de selección disjuntos si existen; invariante de offsets en el 100 % de las filas; columnas exactas; ninguna fila con `texto` vacío; hashes de texto vigentes; la etiqueta `reglas-congeladas` precede al primer commit de los archivos gold. Alerta (no bloqueo) si el F1 combinado resulta 1.0 en algún tipo con más de 5 entidades gold. Exporta a la raíz `gold_entidades.csv`.

**Cambios posteriores al cierre.** Corregir un error humano exige revisión explícita del alumno, motivo y nueva versión, declarando si ya había visto predicciones. No se retoca el gold para optimizar métricas.

**Tiempo estimado para el alumno:** 20 a 26 pasajes × 6 a 8 minutos ≈ 2 a 3.5 horas.

### 6.12 Evaluación de IE y análisis de errores (`evaluacion.py`, script `09_evaluar_ie.py`) · P0

1. Si hay conjunto de selección: comparación de candidatos NER (6.8) → `salida/09_comparacion_ner.csv` con F1 por tipo en selección (decide) y en gold (informativo); `data/modelo_ner.json` fijado antes de este paso.
2. Con el extractor congelado (reglas + modelo elegido): `entidades.csv` fusionado → `python kit/evaluar.py ie gold_entidades.csv entidades.csv` → `resultados_ie.csv` (raíz y `salida/`), nunca con una salida provisional de otro modelo. Se registran versiones y hashes.
3. `salida/09_ie_detalle.csv`: por método y tipo, P/R/F1 con TP, FP, FN y soporte; tipos sin soporte como "no aplicable" sin alterar el CSV oficial. Un NER limitado a PER/ORG/LOC no tiene cobertura de FECHA/MONTO: se muestra explícitamente.
4. **Cambios posteriores al congelamiento (D15).** Si después de ver resultados se ajusta una regex o el gazetteer, `salida/09_cambios_post_congelamiento.csv` guarda el F1 antes y después con el commit; el reporte presenta ambas cifras y marca la segunda como exploratoria.
5. **Análisis de errores automático** `analizar_errores(gold, pred, pasajes)` sobre los 20 pasajes gold. Para cada FN y cada FP se asignan una o más categorías (no son partición exclusiva):
   - `frontera`: predicción del mismo tipo que solapa parcialmente (incluye "entidad partida": dos o más predicciones dentro de un gold, y "monto sin unidad": predicción prefijo del gold).
   - `tipo`: mismo span, tipo distinto (incluye `obra_LOC_vs_ORG` cuando el texto está en el gazetteer de obras).
   - `sigla_no_reconocida`: gold en mayúsculas de 2 a 7 letras sin predicción que lo cubra.
   - `en_marca`: el span cae dentro de la marca (`fin <= inicio_cuerpo`); describe dónde ocurre, no demuestra causa.
   - `omision`: sin predicción que solape.
   - `espuria`: FP sin gold que solape, subclasificada por fuente (regex, gazetteer, marca, modelo).
   Salida: `salida/09_analisis_errores.csv` (`passage_id, tipo, texto_gold, texto_pred, inicio, fin, metodo, categoria, fuente, contexto`) y `salida/09_resumen_errores.csv`. Se revisan los ejemplos reales antes de redactar conclusiones. Para cada categoría del enunciado (entidad partida, sigla no reconocida, monto sin unidad, obra LOC u ORG, efecto de mayúsculas) el reporte incluye un caso observado o declara que no apareció; no se inventan errores para llegar a una cuota.
6. Figuras: `reporte/figuras/ie_f1_por_tipo_metodo.png`, `ie_errores_por_categoria.png`.

**Criterios de aceptación.** `resultados_ie.csv` con filas para `regla`, `modelo`, `combinado` × tipos más TODOS; evaluación complementaria de 20 IDs; comparación NER guardada si se hizo; ejemplos de error reales clasificados (meta orientativa: 8).

### 6.13 Tablas de respuesta con evidencia (`respuestas.py`, script `10_tablas.py`) · P0

Para cada consulta, sobre su top-10 con filtro del mejor modelo (D17). Una lista de entidades es un inventario; las respuestas sobre participación, costos, pagos o fechas requieren evidencia de la relación.

1. **Exclusiones (U14).** Antes de agregar se quitan las entidades con `en_marca == True` y las PER cuyo `texto_normalizado` está en `config/excluir_tablas.yaml` (por defecto, variantes del nombre del presidente, solo para la columna de funcionarios). Sin esto, "Andrés Manuel López Obrador" encabezaría la columna de funcionarios en todas las consultas por aparecer en la marca de cada intervención. Se reporta cuántas se excluyeron por consulta; `entidades.csv` no se toca.
2. **Mapa consulta → campos** en `config/tablas_respuesta.yaml`, fijado antes de generar respuestas:

| Consulta | Campos de respuesta | Evidencia mínima de la relación |
| --- | --- | --- |
| Q1 | dependencias y empresas ← ORG; estados ← LOC ∩ entidades federativas; montos ← MONTO | Participación o inversión vinculada al Tren Maya en la cita |
| Q2 | farmacéuticas ← ORG ∩ lista D14; funcionarios ← PER; fechas ← FECHA; dosis ← CANTIDAD (dosis) | Entrega, aplicación o gestión de vacunas; fecha y cantidad vinculadas al evento citado |
| Q3 | organizaciones ← ORG; responsables ← PER; montos de inversión ← MONTO | Responsabilidad o inversión explícita en Dos Bocas o refinería Olmeca |
| Q4 | dependencia constructora ← ORG; lugares ← LOC; costos ← MONTO | Construcción o costo asociado a AIFA o Santa Lucía, no a otro aeropuerto |
| Q5 | secretaría operadora ← ORG; estados ← LOC; monto por beneficiario ← MONTO con contexto "mensual|por sembrador|por beneficiario" | Distinguir del presupuesto total |
| Q6 | lugares ← LOC; organizaciones ← ORG; pérdidas ← MONTO; litros ← CANTIDAD (litros) | Evento de robo, recuperación o pérdida de combustible; conservar sentido y unidad |
| Q7 | montos bimestrales ← MONTO con contexto "bimestr"; institución ← ORG; fechas de aumento ← FECHA con contexto "aument" | Distinguir monto previo y nuevo; no asumir que todo monto es bimestral |
| Q8 | organizaciones empresariales ← ORG ∩ tipo organización empresarial; porcentajes ← PORCENTAJE; montos diarios ← MONTO con contexto "diario|al día" | Aumento o acuerdo salarial; distinguir propuestas de valores anunciados |
| Q9, Q10 | Definidos con su pregunta | Mapa y patrones fijados antes de generar la respuesta |

   El contexto se busca en ±60 caracteres alrededor del span y en la oración contigua.
3. **Contrato `salida/respuestas.csv`:** `query_id, campo_respuesta, valor, unidad, relacion, estado, passage_id, doc_id, fecha_documento, evidencia_inicio, evidencia_fin, cita, entidades_referencia, regla_relacion, grupo_evento, interlocutor`. `estado` ∈ {respaldado_en_texto, ambiguo, contradictorio, no_encontrado}. Un valor respaldado tiene pasaje y cita exacta con offsets; `no_encontrado` deja esos campos vacíos. "Respaldado en texto" significa que el corpus lo afirma, no que sea verdad.
4. **Agregación y credibilidad.** Se agrupan alias verificados por `canonico` o `texto_normalizado` y evidencias repetidas del mismo evento; las ventanas solapadas del mismo discurso (`intervencion_id` y tokens) no cuentan como confirmaciones independientes. Se conservan frecuencia, pasajes y discursos distintos. Contradicciones se muestran sin resolverlas por mayoría. No se atribuye al presidente lo que dijo un reportero: se conserva quién habla y si el fragmento es pregunta, anuncio o respuesta. Hasta 8 valores por campo, ordenados por evidencia directa y después por frecuencia.
5. Salida: `salida/tablas_respuesta/Q1.md` … `Q10.md` y `todas.md`, cada una con la pregunta como encabezado, la tabla compacta (valor, tipo o rol, pasaje de evidencia, fecha del discurso, cita breve) y un bloque `valoracion:` que el alumno rellena en `anotaciones/valoraciones.yaml` (2 a 3 líneas por consulta: ¿es creíble?, ¿qué le falta?, ¿qué está mal?). `[VALIDAR]` que el alumno las escribió antes de generar el reporte; el asistente no las redacta. Un cambio sustancial de las tablas invalida la valoración.

### 6.14 Reporte (`reporte.py`, script `11_reporte.py`, `reporte/`) · P0 (contenido), P2 (lint de estilo)

**Formato.** `reporte/reporte.md` → `reporte/reporte.pdf` con `pandoc reporte.md -o reporte.pdf --pdf-engine=xelatex --template=plantilla.tex` (plantilla sobria en el repo: márgenes 2.2 cm, fuente del sistema, `booktabs`, figuras con ancho máximo). Otra ruta que produzca el mismo PDF es válida si se documenta. Conteo automático de páginas (`pypdf` o `pdfinfo`): entre 4 y 6; si excede, se recorta primero anexos y ejemplos redundantes, nunca la evidencia de un rubro ni la legibilidad de la tipografía. Tablas y figuras se generan con `make resultados`, sin TeX. Se revisan visualmente todas las páginas, cortes de tablas y fórmulas.

**Sin código** (EX): ni bloques ni fragmentos. Pseudocódigo en prosa y fórmulas en LaTeX sí.

**Estructura y extensión objetivo (6 páginas):**

1. Portada compacta: título, nombre, materia, fecha, enlace al repo (0.25).
2. Datos, limpieza y segmentación: estadísticas del corpus, conteos de limpieza (acotaciones, duplicados, fechas reparadas), decisión de segmentación y tabla de sensibilidad si existe, tratamiento de marcas y reporteros, intervenciones cortas descartadas (0.75).
3. Preprocesamiento e índice invertido: tokenización, stoplist con ejemplos de la estenográfica, stemming, exclusión de la marca del índice, postings de 4 términos (0.75).
4. Ranking y evaluación de IR: TF-IDF frente a BM25, con y sin filtro, tabla de P@5, P@10 y MAP en las dos vistas, figura por consulta, discusión por consulta: dónde gana cada uno y por qué, consultas largas y cortas, sinónimos, qué cambiaría con embeddings densos (1.25).
5. Extracción con reglas y con modelo: regex y casos no cubiertos, gazetteers (tamaño, origen), modelo elegido y criterio (o comparación sobre el conjunto de selección), normalización, fusión (0.75).
6. Evaluación de IE y análisis de errores: tabla P/R/F1 por tipo y método, evaluación de 20 IDs, cambios posteriores al congelamiento si los hubo, categorías de error con ejemplos reales (1.0).
7. Tablas de respuesta: las diez en formato compacto con la valoración del alumno; si no cabe, Q1 a Q8 completas y Q9 y Q10 resumidas con el resto en el repo (0.75).
8. Uso de IA, limitaciones y reproducibilidad: resumen del README, incluida la autoría de la prosa (0.5).

**Guía de estilo (obligatoria para el asistente):** español de México, tono directo e impersonal (se habla del "sistema", "el pipeline"); sin rayas ni guiones largos como puntuación; títulos en mayúscula inicial solamente; sin el patrón "no es X, es Y"; sin cierres sentenciosos; discusión en prosa y cifras en tablas, nada de listas con negritas como sustituto de párrafos; sin adjetivos vacíos sin cifra; cada afirmación comparativa cita la cifra y la tabla o figura. `scripts/lint_estilo.py` (P2) detecta rayas, encabezados con más de dos palabras capitalizadas no propias, el patrón `/no es .*?, (es|sino)/i` y la lista de `config/estilo_prohibido.txt`; si se recorta, se verifica leyendo.

**Flujo con el alumno.** `[VALIDAR]` en tres cortes: (1) esqueleto con títulos, tablas y figuras insertadas; (2) borrador completo de prosa sección por sección, donde el alumno corrige tono y conclusiones (el asistente aplica cambios y no discute matices que el alumno quiera); (3) PDF final con conteo de páginas. La prosa aprobada se versiona y no se vuelve a generar en cada compilación.

### 6.15 Láminas y guion (`laminas.py`, script `12_laminas.py`) · P0 (contenido y guion), P2 (generación automática)

Máximo cinco láminas (EX) 16:9 con el patrón "concepto + artefacto": columna izquierda (40 %) con 3 a 5 líneas, columna derecha (60 %) con una figura o tabla real del proyecto. Títulos en mayúscula inicial, paleta de dos colores más gris, pie con nombre y número. La generación con `python-pptx` es P2: a mano con las figuras de `reporte/figuras/` toma menos de una hora.

| Lámina | Concepto | Artefacto |
| --- | --- | --- |
| 1 | Problema, corpus, limpieza, unidad de recuperación, pipeline en una línea | Diagrama del pipeline y cifras del corpus |
| 2 | Segmentación e índice: decisiones y qué cambió | Tabla de sensibilidad (o de descartes) y postings de "huachicol" |
| 3 | IR: TF-IDF frente a BM25, con y sin filtro, consulta difícil | Figura AP por consulta y tabla de MAP |
| 4 | IE: reglas más modelo, fusión, errores típicos | Tabla P/R/F1 por tipo y método y 3 ejemplos reales de error |
| 5 | Demo y limitaciones: qué se muestra en vivo y tabla de respuesta de una consulta | Tabla de respuesta de la consulta elegida y el comando `make demo Q=Q3` |

`laminas/guion.md` (P0): ≈5 minutos de exposición, 2 de demo y 1 de margen (U18), medidos en un ensayo. Incluye las preguntas probables del anexo C con la respuesta preparada. `[VALIDAR]` láminas y guion.

### 6.16 Demo (`demo.py`, script `13_demo.py`, pestaña "Demo" P2) · P0 (terminal)

`make demo Q=Q3` o `uv run python scripts/13_demo.py --consulta "refinería de Dos Bocas en Tabasco" --desde 2019-01-01 --hasta 2022-12-31`. Imprime con `rich`, sin red, sobre artefactos cacheados: consulta y ventana; top-10 de TF-IDF y BM25 lado a lado (rango, `passage_id`, fecha, posición, puntaje, 100 caracteres); pasajes; entidades del top-10 del mejor modelo agrupadas por pasaje con color por tipo y método; tabla de respuesta con evidencia. Se mide latencia de primera carga y con caché (meta: menos de 30 segundos con caché). Si la consulta es libre (no está en `consultas.csv`), ejecuta el NER en caliente sobre los 10 pasajes (20 a 40 segundos en CPU), lo avisa y no le atribuye métricas del experimento. Se conserva una salida guardada para contingencias, identificada como tal, que no se presenta como demo en vivo.

---

## 7. App local (`src/mtx/app/app.py`)

- Arranque: `make app` → `uv run streamlit run src/mtx/app/app.py`. Alternativa sin Streamlit: CLI con `input()` que ofrece las mismas tres funciones esenciales (juicios, gold, demo).
- Pestañas: **Estado**, **Juicios**, **Gold**, **Gazetteer**, **Demo** (P2).
- Estado: por artefacto distingue pendiente humano, pendiente técnico, válido, obsoleto (hash cambió) y error. No muestra "completado" solo porque exista un archivo.
- Persistencia en CSV bajo `anotaciones/` tras cada acción, escritura atómica con respaldo y número de revisión; sin base de datos. Se prueba recuperación tras cerrar y reabrir y edición desde dos pestañas (T15).
- Resaltado: HTML seguro generado desde offsets (escape de `<` y `&`), nunca por reemplazo de texto.
- Anotación: búsqueda por texto con desambiguación como modo principal, selección por tokens como secundario; los offsets provienen del texto real.
- Modo ciego: Gold, Demo y paneles de errores no muestran predicciones de la muestra hasta `cierre_gold.json`.
- Prueba manual en `docs/pruebas_app.md`: lista de 10 pasos que el alumno recorre una vez.

---

## 8. Esquemas de datos internos

| Archivo | Contenido | Productor |
| --- | --- | --- |
| `data/corpus_meta.json` | hash del parquet, filas, revisión, fecha de descarga | 01 |
| `data/pasajes.parquet` | columnas de 6.1.3 | 01 |
| `salida/01_estadisticas_corpus.json`, `01_auditoria_corpus.csv`, `01_limpieza.json`, `01_duplicados.csv`, `01_fechas_reparadas.csv`, `01_descartes_cortos.csv`, `01_sensibilidad_segmentacion.csv` (OP) | ver 6.1 | 01 |
| `data/tokens.parquet` | `passage_id, tokens` (solo cuerpo), hash de configuración | 02 |
| `data/indice.pkl`, `data/indice_meta.json`, `salida/02_postings.md`, `02_tokens_consultas.md`, `02_vocabulario_top.csv` | ver 6.3 | 02 |
| `data/tfidf.pkl`, `data/tfidf_X.npz` | vectorizador y matriz | 03 |
| `data/consultas.csv` | kit + Q9 + Q10 | 00 + alumno |
| `salida/ranking.csv` → `ranking.csv`, `03_ranking_detalle.csv`, `03_solape_modelos.csv`, `03_excluidos_por_filtro.csv` | ver 6.4 | 03 |
| `salida/04_pool.csv` | ver 6.5 | 04 |
| `anotaciones/juicios_relevancia.csv` → `juicios_relevancia.csv` | sección 3.5 | alumno (app) |
| `resultados_ir.csv`, `salida/05_resultados_ir_ventana.csv`, `05_ir_por_consulta.csv`, `05_ir_ganador_por_consulta.csv` | ver 6.6 | 05 |
| `data/mejor_modelo.json` | modelo, MAP, alternativa, versiones | 05 |
| `config/gazetteer_extendido.csv`, `salida/06_siglas_candidatas.csv`, `06_colisiones_reglas.csv` | ver 6.7 | 06 + alumno |
| `data/cache_ner/...`, `salida/07_uniones_spans.csv` | json por pasaje, modelo y revisión | 07 |
| `anotaciones/muestra_gold.csv`, `muestra_seleccion.csv`, `estado_gold.csv`, `gold_seleccion.csv`, `gold_entidades.csv` → `gold_entidades.csv`, `cierre_gold.json` | ver 6.11 | 08b + alumno |
| `data/modelo_ner.json` | modelo, revisión, F1 de selección, criterio | 09 (antes del gold) |
| `entidades.csv`, `salida/entidades_unicas.csv`, `entidades_enriquecidas.csv`, `cantidades_auxiliares.csv`, `08_solapes_parciales.csv` | ver 6.9 | 08 |
| `resultados_ie.csv`, `salida/09_ie_detalle.csv`, `09_evaluacion_20_ids.csv`, `09_comparacion_ner.csv`, `09_cambios_post_congelamiento.csv`, `09_analisis_errores.csv`, `09_resumen_errores.csv` | ver 6.12 | 09 |
| `salida/respuestas.csv`, `salida/tablas_respuesta/*.md`, `anotaciones/valoraciones.yaml` | ver 6.13 | 10 + alumno |
| `salida/manifiesto_ejecucion.json`, `salida/tiempos_ejecucion.json` | versiones, hashes, configuración, duración por script | todos |
| `reporte/reporte.md`, `reporte.pdf`, `figuras/`, `tablas/` | | 11 |
| `laminas/laminas.pptx`, `laminas/guion.md` | | 12 o alumno |

Todas las fechas en ISO `AAAA-MM-DD`, UTF-8 sin BOM. Cada artefacto derivado lleva versión de esquema, productor y hashes de entradas en el manifiesto. No se insertan columnas auxiliares en los seis archivos oficiales.

---

## 9. Estructura del repositorio

```
examen1-mineria-textos/
├── README.md                 # instrucciones desde cero, mapa, resultados, uso de IA
├── AGENTS.md                 # guía breve para agentes: mapa, no tocar, comandos, invalidación
├── pyproject.toml            # dependencias, uv, pytest, ruff
├── uv.lock                   # versionado (D01, D18)
├── requirements.txt          # exportado con uv
├── Makefile
├── .gitignore
├── .python-version           # 3.11
├── ranking.csv               # seis entregables en la raíz: exportaciones validadas
├── juicios_relevancia.csv
├── resultados_ir.csv
├── entidades.csv
├── gold_entidades.csv
├── resultados_ie.csv
├── kit/                      # cuatro originales sin modificar; hashes en docs/contratos_kit.md
├── config/
│   ├── proyecto.yaml             # semillas, parámetros de segmentación, rutas
│   ├── ranking.yaml              # k1, b, k, min_df
│   ├── ner.yaml                  # modelos con revision fija, mapa de etiquetas, lotes
│   ├── limpieza.yaml             # patrones de ruido, umbral de duplicados, reversiones
│   ├── candidatos_q9q10.yaml
│   ├── stopwords_es.txt          # respaldo versionado de NLTK
│   ├── stoplist_extra.txt
│   ├── protocolo.txt             # fórmulas de saludo y despedida (criterio de sustitución)
│   ├── gazetteer_loc.csv
│   ├── gazetteer_extendido.csv   # revisado por el alumno
│   ├── sinonimos_consultas.yaml
│   ├── tablas_respuesta.yaml
│   ├── excluir_tablas.yaml
│   ├── criterios_relevancia.md   # lo escribe el alumno
│   ├── criterios_anotacion.md    # lo escribe el alumno
│   └── estilo_prohibido.txt
├── anotaciones/              # fuentes humanas versionadas y protegidas (U20)
│   ├── juicios_relevancia.csv
│   ├── muestra_gold.csv
│   ├── muestra_seleccion.csv     # solo si se comparan NER
│   ├── estado_gold.csv
│   ├── gold_seleccion.csv        # solo si se comparan NER
│   ├── gold_entidades.csv
│   ├── cierre_gold.json
│   └── valoraciones.yaml
├── src/mtx/                  # paquete (sección 6)
├── scripts/
│   ├── 00_descubrir_consultas.py
│   ├── 01_corpus_y_pasajes.py
│   ├── 02_indice.py
│   ├── 03_ranking.py
│   ├── 04_pool.py
│   ├── 05_evaluar_ir.py
│   ├── 06_reglas.py
│   ├── 07_ner.py
│   ├── 08_extraer.py
│   ├── 08b_muestra_gold.py
│   ├── 09_evaluar_ie.py
│   ├── 10_tablas.py
│   ├── 11_reporte.py
│   ├── 12_laminas.py
│   ├── 13_demo.py
│   ├── 99_validar.py
│   └── lint_estilo.py
├── tests/
│   ├── fixtures/             # corpus sintético, kit de prueba, CSV de contrato
│   ├── test_contratos_kit.py
│   ├── test_corpus.py
│   ├── test_preproceso.py
│   ├── test_indice.py
│   ├── test_ranking.py
│   ├── test_pool.py
│   ├── test_muestreo.py
│   ├── test_reglas.py
│   ├── test_ner_posproceso.py
│   ├── test_normalizacion.py
│   ├── test_fusion.py
│   ├── test_respuestas.py
│   └── test_formatos.py      # columnas y claves exactas de los seis CSV
├── data/                     # generado; ver lista de versionados
├── salida/                   # generado; se versiona completo (es pequeño) para que el profesor lo lea
├── reporte/
│   ├── reporte.md            # prosa aprobada, versionada
│   ├── plantilla.tex
│   ├── figuras/
│   ├── tablas/
│   └── reporte.pdf
├── laminas/
│   ├── laminas.pptx
│   └── guion.md
└── docs/
    ├── decisiones.md         # fase 0 y cada decisión posterior con fecha, motivo y efecto
    ├── contratos_kit.md      # firmas y comportamiento verificados del kit
    ├── guia_defensa.md       # 5 líneas por módulo y fórmulas clave
    ├── pruebas_app.md
    └── reproducibilidad.md   # tiempos medidos, hashes, cómo recuperar recursos
```

`.gitignore` excluye `data/*.parquet`, `data/*.pkl`, `data/*.npz`, `kit/data/`, `.venv/`, `__pycache__/`, pesos de modelos. Se versionan `data/consultas.csv`, `data/corpus_meta.json`, `data/mejor_modelo.json`, `data/modelo_ner.json`, `data/cache_ner/`, todo `anotaciones/`, `config/`, `salida/`, `reporte/reporte.md` y los seis CSV de la raíz. Un recurso que no pueda reconstruirse desde la fuente lleva instrucciones y hash para recuperarlo.

---

## 10. Makefile (objetivos)

```make
setup        # uv sync; stopwords de nltk; comprueba pandoc y xelatex (advierte, no falla)
contratos    # H0: pruebas de contrato del kit sobre fixtures; escribe docs/contratos_kit.md
corpus       # 01: descarga, limpieza auditada, segmentación, estadísticas, descartes (y sensibilidad OP)
explorar     # 00: candidatos para Q9 y Q10
indice       # 02
ranking      # 03
pool         # 04: construye o verifica el pool; nunca sustituye uno anotado sin detectar el cambio
app          # streamlit (estado, juicios, gold, gazetteer, demo)
evaluar-ir   # 05: exige juicios validados; escribe mejor_modelo.json
reglas       # 06: minería de siglas, suite de regex
congelar     # etiqueta git reglas-congeladas (antes de abrir el gold)
ner          # 07: inferencia con caché; no infiere si la caché existe
muestra-gold # 08b: muestra gold y, si aplica, conjunto de selección
extraer      # 08: fusión, entidades.csv, enriquecidas, cantidades auxiliares
evaluar-ie   # 09: exige gold cerrado y compatible; comparación NER si hay selección
tablas       # 10: respuestas con evidencia
resultados   # todas las cifras, tablas y figuras del reporte; NO requiere pandoc ni TeX
reporte      # 11: md -> pdf, conteo de páginas, lint (requiere pandoc y TeX)
laminas      # 12
demo         # 13, variable Q=Q3 o CONSULTA="texto"
test         # uv run pytest -q (rápidas, offline, con fixtures); test-lento incluye corpus y modelos
validar      # 99: formatos, claves, invariantes de offsets, pool, gold, hashes, páginas, láminas
entrega      # contratos + resultados + reporte + laminas + validar + copia de CSV a la raíz
all          # alias exacto de entrega
limpiar      # borra solo artefactos regenerables; muestra alcance; nunca toca anotaciones/ ni cache_ner/
```

Los objetivos tienen dependencias reales. Si faltan juicios, gold o textos humanos, el objetivo informa la tarea pendiente (`make app`) y se detiene sin generar datos ficticios. El reinicio continúa desde los artefactos válidos. Para quien no tenga `make`, el README incluye la tabla objetivo → `uv run python scripts/...`.

---

## 11. Reproducibilidad, README, uso de IA, commits

### 11.1 Entorno

- `pyproject.toml` con `requires-python = ">=3.11,<3.13"`. Dependencias: `pandas, numpy, scikit-learn, nltk, regex, datasets, pyarrow, transformers, torch (CPU), streamlit, python-pptx, pyyaml, rich, plotly, kaleido, pypdf`. Desarrollo: `pytest, rank_bm25, ruff`. Marcador `lento` en pytest.
- `torch` CPU desde `https://download.pytorch.org/whl/cpu` en Linux y Windows (`[[tool.uv.index]]` y `[tool.uv.sources]`); en macOS el wheel por defecto ya es CPU/MPS.
- `uv.lock` versionado; `requirements.txt` con `uv export --no-dev --format requirements-txt > requirements.txt` porque la rúbrica lo nombra.
- `salida/manifiesto_ejecucion.json`: commit del código, hashes del kit, del snapshot y del orden de IDs, consultas, configuración, stopwords, gazetteers, muestras, juicios, gold, versión del protocolo, modelo y tokenizador con revisiones, dependencias, semillas, esquemas y parámetros. Las marcas de tiempo informan, no identifican.
- Tabla de invalidación (qué cambio invalida qué producto) en `AGENTS.md`: snapshot o segmentación → todo; tokenización o ranker → ranking, pool, ganador y selección de pasajes IE; consultas → sus rankings y juicios; juicios → métricas IR y ganador (y, si cambia el ganador, revisión explícita de muestra e IE); modelo, reglas o fusión → extracción, evaluación IE, tablas y documentos; gold o protocolo → evaluación IE y documentos. No se borran anotaciones para resolver una invalidación.
- Reconstrucción: desde un clon limpio sin cachés, `make entrega` reproduce los resultados con los insumos humanos versionados. Igualdad exacta para IDs, textos, etiquetas, spans y conteos; tolerancia absoluta 1e-8 para puntajes; los PDF no requieren igualdad byte a byte. Tiempos medidos en la laptop del alumno, en `docs/reproducibilidad.md`, nunca prometidos sin medir.

### 11.2 README.md (secciones obligatorias, en este orden)

1. Qué hace el sistema (5 líneas) y enlace al PDF del reporte.
2. Requisitos: Python 3.11 y `uv` para reproducir cifras; `pandoc` y TeX solo para el PDF. Instrucciones por SO: macOS (`brew install uv pandoc`, `brew install --cask basictex` y `sudo tlmgr install collection-fontsrecommended booktabs`), Windows (`winget install astral-sh.uv`, `winget install JohnMacFarlane.Pandoc`, `winget install MiKTeX.MiKTeX`, tabla de comandos sin `make`), Linux (`curl -LsSf https://astral.sh/uv/install.sh | sh`, `sudo apt install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-extra`).
3. Instalación desde cero: `git clone`, `make setup`, `make contratos`, `make corpus` (incluye descarga del corpus con tamaño y tiempo medidos, y qué hacer si el hash no coincide con `data/corpus_meta.json`).
4. Reproducir resultados: `make resultados` (sin TeX) o `make entrega` (con TeX), usando los CSV humanos y la caché NER versionados.
5. Flujo completo con pasos humanos: `make explorar` → elegir Q9 y Q10 → `make corpus indice ranking pool` → `make app` (juicios) → `make evaluar-ir` → `make reglas` → `make app` (gazetteer) → `make congelar` → `make ner muestra-gold` → `make app` (selección y gold) → `make evaluar-ie tablas` → editar `anotaciones/valoraciones.yaml` → `make reporte laminas`.
6. Mapa del repo (árbol comentado).
7. Decisiones de diseño (resumen de la sección 4 con enlace a `docs/decisiones.md`) y limitaciones conocidas.
8. Resultados principales: MAP por variante y F1 combinado por tipo, autogenerados por `11_reporte.py` entre `<!-- resultados:inicio -->` y `<!-- resultados:fin -->`.
9. Uso de IA (11.3).
10. Dependencias y por qué: tabla con papel de cada biblioteca, cuáles están en el enunciado, cuáles son utilerías y la respuesta del profesor sobre ellas.

### 11.3 Sección "Uso de IA" (EX, p. 4; la redacta el asistente con trazabilidad real)

- Qué asistente se usó y para qué módulos (lista real de archivos escritos o coescritos).
- Autoría de la prosa: el reporte, el README y el guion los redactó el asistente a partir de resultados reales y el alumno los revisó y corrigió sección por sección, indicando cuáles modificó de forma sustancial.
- Qué revisó, modificó o decidió el alumno: fase 0, criterios de relevancia y anotación, Q9 y Q10, gazetteer, valoraciones, correcciones al reporte.
- Declaración explícita, solo si ocurrió así: los juicios, el conjunto de selección y el gold se hicieron a mano en la app leyendo cada pasaje, en modo ciego para el gold; el asistente no generó ni sugirió ninguno de esos valores. No se añade una declaración de integridad ficticia para cumplir una plantilla.
- Cómo se verificó el código generado (pruebas, validadores, lectura del alumno).
- Lo que el alumno debe poder explicar en la demo: cualquier función del paquete. El asistente genera `docs/guia_defensa.md` con 5 líneas por módulo, un ejemplo y las fórmulas clave (idf de BM25, TF-IDF sublineal, coseno, AP, F1), que el alumno estudia y puede corregir.

### 11.4 AGENTS.md (P2, una página)

Propósito del repo; "no tocar" (`kit/`, `anotaciones/`, `data/cache_ner/`, `config/criterios_*.md`, `reporte/reporte.md` aprobado); mapa paquete → script → salida; cómo correr pruebas; convenciones (español, Conventional Commits, sin rayas en prosa); dónde registrar decisiones; tabla de invalidación de 11.1. Referencia este PRD y no duplica su metodología.

### 11.5 Commits

Conventional Commits con tipo en inglés y descripción en español: `feat(corpus): limpieza de ruido y segmentación con marca reinyectada`, `feat(ranking): tf-idf, bm25 y filtro de fecha`, `feat(app): pestaña de juicios`, `data(juicios): juicios de relevancia Q1-Q10` (tipo `data` para los CSV humanos), `test(reglas): casos de fecha y monto`, `docs(reporte): borrador completo`, `chore: dependencias`. Un commit por unidad probada. Etiquetas: `reglas-congeladas` antes del gold y `v1.0-entrega` en el commit final con la hora registrada. No se publica ni se cambia la versión entregada bajo una autorización destinada solo a revisar este documento.

---

## 12. Plan de ejecución por hitos

### 12.1 Prioridades (D20)

| Prioridad | Qué incluye | Regla |
| --- | --- | --- |
| P0 · núcleo de entrega | Contratos del kit, limpieza y segmentación, preprocesamiento, índice, ambos rankings con filtro, pool y juicios, evaluación IR, regex y gazetteers con su suite, un modelo NER, fusión, gold, evaluación IE con análisis de errores, tablas con evidencia, reporte de 4 a 6 páginas, README, `requirements.txt`, guion y demo en terminal | Completo antes de tocar P1 |
| P1 · mejora de calificación | Segundo NER con conjunto de selección, experimento de sensibilidad, vista con ventana completa, figuras completas | Solo con P0 terminado |
| P2 · pulido | Normalización de fechas relativas, vínculo de personas, lint de estilo, láminas con `python-pptx`, pestaña Demo, `AGENTS.md`, experimento de capitalización | Solo con P1 terminado; lo primero que se recorta |

### 12.2 Hitos y dependencias

Las fechas del enunciado (entrega 28 de octubre a las 20:00, presentación 4 de noviembre) son hechos registrados; el plazo vigente se anota en `docs/decisiones.md` y el plan se adapta al estado real del proyecto (U17). No se crea un calendario retrospectivo que dé por hechas fases pendientes. Las filas **humano** no las puede hacer el asistente; mientras el alumno anota, el asistente avanza en lo que no depende de esa anotación.

| Hito | Trabajo | Condición para avanzar |
| --- | --- | --- |
| H0 · Preparación | Fase 0, repo, `pyproject`, `Makefile`, `kit/` copiado con hashes, pruebas de contrato, `make setup` verde | `docs/contratos_kit.md` y primer commit |
| H1 · Datos y consultas | `00_descubrir_consultas.py`, Q9 y Q10 `[VALIDAR]`, `01_corpus_y_pasajes.py` con limpieza auditada | `data/pasajes.parquet`, consultas congeladas, `test_corpus` verde |
| H2 · Recuperación | Preprocesamiento, índice, postings, tokens de consultas, TF-IDF, BM25, filtro, `ranking.csv`, pool | 400 filas (o excepciones justificadas), pruebas bloqueantes de 6.4 verdes, pool congelado |
| H3 · Juicios (**humano**) | `config/criterios_relevancia.md` `[VALIDAR]`, juicios en la app (2 a 4.5 h) | `make validar` sin errores en juicios; cierre |
| H4 · Evaluación IR | `05_evaluar_ir.py`, vista con ventana, `mejor_modelo.json`, figuras IR | `resultados_ir.csv` |
| H5 · Preparación IE | Regex, gazetteers, minería de siglas, suite verde; revisión de siglas (**humano**, ≈30 min) `[VALIDAR]`; verificación técnica del NER; `config/criterios_anotacion.md` `[VALIDAR]`; `make congelar`; muestras sorteadas | Etiqueta `reglas-congeladas`, `modelo_ner.json` provisional, manifiestos de muestra |
| H6 · Gold (**humano**) | Conjunto de selección (si aplica) y gold de 20 en modo ciego (2 a 3.5 h); cierre | `make validar` sin errores en gold; `cierre_gold.json` |
| H7 · IE final | Selección NER (si aplica), inferencia, fusión, `entidades.csv`, enriquecidas, `resultados_ie.csv`, análisis de errores, figuras IE | Ejemplos de error reales clasificados |
| H8 · Respuestas | Tablas con evidencia; `valoraciones.yaml` (**humano**, ≈40 min) | 10 tablas y 10 valoraciones |
| H9 · Entrega | Reporte en tres cortes `[VALIDAR]`, láminas y guion `[VALIDAR]`, demo ensayada, README con tiempos medidos, sección de IA, `make entrega` desde un clon limpio en otra carpeta, etiqueta `v1.0-entrega` | Push con margen antes del plazo |

Entre la entrega y la presentación: ensayo con `docs/guia_defensa.md`; no se cambia código que afecte cifras del reporte.

### 12.3 Estimaciones de tiempo humano (pendientes de medir)

Hasta 400 juicios a 40 segundos ≈ 4.4 horas; 20 a 26 pasajes gold a 6 a 8 minutos ≈ 2 a 3.5 horas; revisión de siglas ≈ 30 minutos; valoraciones ≈ 40 minutos; revisión de prosa ≈ 1 hora. Se mide un lote inicial para ajustar; estas cifras no son promesas.

### 12.4 Lista de recortes (en este orden, avisando al alumno)

1. Todo lo P2: experimento de capitalización, pestaña Demo, láminas con `python-pptx` (se hacen a mano), lint de estilo (se revisa leyendo), normalización de fechas relativas, vínculo de personas, `AGENTS.md` reducido a cinco líneas en el README.
2. Comparación de dos NER: se usa el principal por criterio técnico y el reporte lo declara.
3. Experimento de sensibilidad de segmentación (se justifica la base con los conteos de 6.1).
4. Figuras del reporte reducidas a dos (MAP por variante y F1 por tipo).
5. Pool reducido a las variantes con filtro: las variantes sin filtro se evalúan con la métrica condensada (ignorando no juzgados) y el reporte declara que su comparación cuantitativa es limitada.
6. Tablas Q9 y Q10 resumidas en el reporte (completas en el repo).

Nunca se recorta: dos modelos de ranking, dos enfoques de extracción, la limpieza de ruido, los seis CSV de entrega, el congelamiento antes del gold, el modo ciego, README reproducible, reporte dentro de 4 a 6 páginas, máximo 5 láminas. Si se reduce un requisito EX, el estado final dice qué falta; una limitación escrita en el reporte no se convierte en cumplimiento.

---

## 13. Validación y criterios de aceptación globales

### 13.1 Pruebas relevantes (`make test`; las de integración en `make test-lento`)

| ID | Caso | Comprobación |
| --- | --- | --- |
| T01 | Kit real y fixtures sintéticos | CLI, esquemas y semántica documentados en `docs/contratos_kit.md`; resultados oficiales preservados |
| T02 | Texto con varias marcas, sin marcas, acentos y saltos | Segmentación y texto canónico estables; `inicio_cuerpo` correcto; pérdida de contenido cuantificada |
| T03 | Conteos conocidos de términos | Postings, tf y df coinciden con `CountVectorizer` |
| T04 | Corpus numérico pequeño | TF-IDF y BM25 coinciden con sus fórmulas dentro de tolerancia; ceros sin NaN; subclase de `rank_bm25` coincide |
| T05 | Fecha en límites exactos, ausente, ventana abierta e invertida | Inclusión y exclusión correctas; error claro ante entradas inválidas |
| T06 | Cero, tres o diez candidatos y términos desconocidos | Nunca se cuelan excluidos; tamaños, rangos y estados consistentes |
| T07 | Cuatro rankings parcialmente solapados | Pool como unión exacta y cobertura completa de juicios |
| T08 | Pasaje compartido entre consultas | Asociaciones conservadas con `query_id`; evaluación por pasaje sin doble conteo inadvertido |
| T09 | Muestreo con colisiones y caso imposible | 20 IDs únicos con 2 por consulta, o explicación de inviabilidad |
| T10 | Pasaje gold sin entidades y tipo sin soporte | Cierre válido; soporte real del kit identificado; evaluación complementaria coherente |
| T11 | Regex, números hablados, fechas inválidas, colisiones y ambigüedades | Spans exactos, valores y estados esperados, prioridad entre fuentes |
| T12 | Texto largo, una oración enorme y entidad en borde de ventana | Sin truncamiento silencioso; offsets correctos; consolidación determinista |
| T13 | Coincidencia exacta, parcial y de distinto tipo | Métodos `regla`, `modelo`, `ambos`; discrepancias conservadas |
| T14 | Respuesta con varias organizaciones y montos y pregunta de reportero | No se atribuyen relaciones sin evidencia; ventanas solapadas deduplicadas; interlocutor conservado |
| T15 | Cambio de texto, modelo o regla; interrupción; dos pestañas | Invalidación correcta, reanudación y protección de datos humanos |
| T16 | Clon limpio y ejecución repetida | Reconstrucción completa con los mismos resultados y cifras publicadas |

Las pruebas rápidas corren sin red ni modelos grandes (fixtures sintéticos y mocks del pipeline HF). Una salida de modelo "parecida" no sustituye la validación de offsets; una diferencia TF-IDF/BM25 no demuestra corrección; las pruebas sintéticas no reemplazan la lectura humana.

### 13.2 Condiciones de entrega (`make validar`, script `99_validar.py`)

1. El kit original permanece sin cambios (hashes); Q1 a Q8 coinciden con el kit; `data/consultas.csv` tiene Q9 y Q10 elegidas por el alumno.
2. Los seis CSV existen en la raíz con las columnas y claves exactas de 3.5 (`tests/test_formatos.py`) y son exportaciones de `salida/` y `anotaciones/` con la misma versión.
3. `ranking.csv`: 10 consultas × 4 variantes × 10 rangos (o excepciones justificadas); rangos consecutivos; puntajes finitos; `passage_id` existen en `pasajes.parquet`; en variantes con filtro toda `fecha` cae en la ventana.
4. `juicios_relevancia.csv`: cubre el 100 % del pool de cuatro variantes; valores en {0, 1}; ningún pasaje fuera del pool; hashes vigentes.
5. `resultados_ir.csv` se regenera con `kit/evaluar.py` y coincide con el versionado; ganador fijado con la regla D08 antes de IE.
6. `entidades.csv`: `metodo` ∈ {regla, modelo, ambos}; invariante de offsets en el 100 % de las filas; sin duplicados en la clave; corresponde al extractor congelado.
7. `gold_entidades.csv`: 20 IDs distintos del manifiesto con 2 por consulta, todos cerrados, invariante en 100 %, todos en el top-10 con filtro del mejor modelo; `gold_seleccion.csv` disjunto si existe; `reglas-congeladas` precede a ambos; `cierre_gold.json` vigente.
8. `resultados_ie.csv` se regenera con `kit/evaluar.py` y coincide; existe `09_evaluacion_20_ids.csv`; ejemplos de error reales.
9. `respuestas.csv` y las diez tablas existen; cada valor respaldado tiene cita con offsets válidos; `valoraciones.yaml` tiene 10 entradas escritas por el alumno.
10. El hash del corpus coincide con `data/corpus_meta.json` (si no, aviso).
11. `reporte.pdf` entre 4 y 6 páginas; sin bloques de código en el Markdown; `lint_estilo.py` sin hallazgos si existe.
12. Entre 1 y 5 láminas; guion con tiempo medido ≤ 8 minutos.
13. `uv run pytest -q` verde; `make resultados` desde un clon limpio reproduce las cifras sin TeX.
14. README con las 10 secciones de 11.2; `requirements.txt` coherente con `uv.lock`; sección de IA exacta.
15. Versión entregada identificada (`v1.0-entrega`), acceso del profesor comprobado y hora real registrada.

**Umbrales de alerta (U19, no son metas):** MAP oficial del ganador < 0.15 o F1 combinado TODOS < 0.30 obligan a buscar un bug (tokens de consulta, offsets, mapa de etiquetas) antes de reportar. Un F1 de 1.0 en un tipo con más de 5 entidades gold dispara la alerta de gold copiado. Los validadores técnicos no certifican que las decisiones humanas sean correctas.

---

## 14. Riesgos y mitigaciones

| Riesgo | Probabilidad | Detección | Mitigación |
| --- | --- | --- | --- |
| El kit real difiere del contrato descrito | Media | H0, T01 | Adaptadores en `adaptadores_kit.py`; nunca editar el kit ni sustituir el evaluador |
| Hugging Face bloqueado en la red del alumno | Baja | Fase 0 | Descargar desde otra red y copiar `kit/data/discursos.parquet` y la caché de modelos (`HF_HOME`) |
| El dataset cambia de versión | Baja | Hash en `corpus_meta.json` | Aviso del validador; registrar la revisión |
| Muchas `fecha` NaT o erróneas que vacíen el filtro | Media | 6.1.2 | Reparación desde título y URL; se cuentan; si una consulta tiene menos de 10 elegibles se documenta |
| Discursos duplicados que llenen el top-10 | Media | 6.1.2 | Deduplicación exacta y casi exacta antes de segmentar, auditada y reversible |
| Marcas repetidas sesgan el índice | Alta sin D03 | Prueba de marca alterada | `inicio_cuerpo`; solo el cuerpo se indexa |
| Términos de consulta perdidos por stoplist o stemming | Media | `02_tokens_consultas.md` | Prueba bloqueante de términos clave |
| Modelos BERT lentos o sin memoria | Baja | Medición temprana | ≤100 pasajes, lotes de 8, caché versionada; alternativa antes del gold |
| Offsets desalineados tras reinyección o chunking | Media | Invariante en tests y validadores | El `texto` del pasaje es la única fuente de verdad |
| Muestra de 20 IDs inviable por colisiones | Baja | T09 | Emparejamiento global; conflicto explícito antes de anotar |
| F1 optimista por elegir el NER o ajustar reglas con el gold | Media | D09, D15 | Conjunto de selección disjunto; congelamiento; cifras antes y después |
| Gold expuesto a predicciones | Baja | Modo ciego y `cierre_gold.json` | Congelar selección; declarar cualquier exposición |
| Juicios o gold incompletos por falta de tiempo | Media | Progreso en la app | Reserva de horas; recortes 2 y 5; el asistente avanza en paralelo; nunca se autocompleta |
| La app de gold va lenta con selección por tokens | Media | Prueba manual | Búsqueda por texto como modo principal |
| Tablas con relaciones falsas | Media | T14 | Estados de evidencia; abstenerse y mostrar ambigüedad |
| Reporte que excede 6 páginas | Alta | Conteo automático | Prioridades de recorte en 6.14 |
| Prosa con marcas de IA | Alta | Guía de estilo, lint | Validación sección por sección; autoría declarada |
| Rankings idénticos TF-IDF/BM25 por bug | Baja | Prueba de 6.4 | Investigar antes de reportar |
| Resultados viejos tras un cambio | Media | Hashes y T15 | Tabla de invalidación; regenerar descendientes; proteger insumos humanos |
| El profesor no acepta una utilería | Baja | Fase 0 | Alternativa de 2.2 para cada una |
| El alumno no sabe explicar el código en la demo | Media | Ensayo | `docs/guia_defensa.md`, anexo C, sección de IA con trazabilidad |

---

## 15. Anexos

### A. Fórmulas que el reporte debe mostrar (en LaTeX, sin código)

idf de BM25:

$$\mathrm{idf}(t) = \ln\left(1 + \frac{N - df_t + 0.5}{df_t + 0.5}\right)$$

BM25, con $k_1 = 1.5$ y $b = 0.75$, sumando sobre los términos únicos de la consulta:

$$\mathrm{score}(q, p) = \sum_{t \in q} \mathrm{idf}(t) \cdot \frac{tf_{t,p}\,(k_1 + 1)}{tf_{t,p} + k_1\left(1 - b + b \cdot \frac{|p|}{\mathrm{avgdl}}\right)}$$

TF-IDF sublineal con idf suavizado (equivale a scikit-learn con `sublinear_tf=True` y `smooth_idf=True`), normalizado L2, con similitud del coseno con la consulta:

$$w_{t,p} = \left(1 + \ln tf_{t,p}\right) \cdot \left(\ln\frac{1 + N}{1 + df_t} + 1\right)$$

Diferencia con `rank_bm25.BM25Okapi`: usa $\ln\frac{N - df_t + 0.5}{df_t + 0.5}$ con un piso $\varepsilon$ para términos con $df_t > N/2$.

P@k = relevantes en los primeros k / k. AP@10 = $\sum_{r=1}^{10} P@r \cdot rel(r) / R$, con R el número de relevantes del pool de esa consulta (denominador confirmado contra el kit en H0). MAP = promedio de AP entre las diez consultas.

Precisión = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R); una predicción es TP cuando coincide exactamente en `(passage_id, tipo, inicio, fin)`.

### B. Casos de prueba mínimos de regex (resumen; la suite completa está en `tests/test_reglas.py`)

| Grupo | Casos |
| --- | --- |
| FECHA positivos | `15 de diciembre de 2023` · `primero de enero de 2020` · `1 de septiembre del 2021` · `enero de 2021` · `diciembre del 2019` · `15/12/2023` · `el próximo 15 de enero` → `próximo 15 de enero` · `el pasado 20 de noviembre` → `pasado 20 de noviembre` · `en diciembre de 2021` → `diciembre de 2021` · `en 2019` → `2019` · `del 1 al 15 de enero de 2021` |
| FECHA negativos | `15 personas` · `página 15` · `2 horas` · `15 de los 32 estados` · `15 de cada 100` · `2019` sin contexto · `31 de febrero` (detectada, no resoluble) |
| MONTO positivos | `20 mil millones de pesos` · `2 mil 500 millones de pesos` · `1,200 millones de pesos` · `$1,200 millones` · `$ 5 mil` · `5 mil pesos` · `500 pesos` · `2 mil millones de dólares` · `1.5 billones de pesos` · `6 mil 300 pesos` · `mil 200 pesos` · `un millón de pesos` · `dos mil millones de pesos` |
| MONTO negativos | `20 mil personas` · `15 millones de dosis` · `3 millones de árboles` · `página 20` · `20 por` · `20%` y `20 por ciento` (son PORCENTAJE) · `500 pesos` dentro de `1500 pesos` |
| PORCENTAJE | `20%` · `20 por ciento` · `3.5 por ciento` → valor 20, 20, 3.5 con unidad porcentaje |
| CANTIDAD | `15 millones de dosis` · `100 mil litros` · `30 mil elementos` · `200 mil sembradores` |
| ORG y LOC | `IMSS`, `Pemex`, `COVAX` sensibles a mayúsculas · `Tren Maya`, `Ciudad de México`, `Dos Bocas` como LOC · sigla coincidente con palabra común no se marca · `Secretaría de Salud de Tabasco` como ORG completa |

### C. Preguntas probables en la demo y dónde está la respuesta

| Pregunta | Dónde |
| --- | --- |
| ¿Por qué pasajes y no discursos? ¿Por qué 200 palabras? ¿Qué pasa si lo duplicas? | D02, `salida/01_sensibilidad_segmentacion.csv` si existe, reporte sección 2 |
| ¿Qué ruido limpiaste y cuánto? | `salida/01_limpieza.json`, reporte sección 2 |
| ¿Por qué la marca no entra al índice si sí está en el texto y se anota? | D03, 3.6, reporte sección 3 |
| Postings de "huachicol", su idf y por qué es alto | `salida/02_postings.md` |
| ¿Cómo se calcula el idf y el puntaje BM25? ¿Por qué no coincide exacto con `rank_bm25`? | 6.4 y anexo A |
| Consulta más difícil y por qué | `salida/05_ir_ganador_por_consulta.csv`, reporte sección 4 |
| ¿Qué cambia con el filtro y por qué la relevancia se juzga temáticamente? | D06, D07, 6.6, reporte sección 4 |
| ¿Cómo evitaste usar el gold para elegir el NER o ajustar reglas? | D09, D15, `salida/09_comparacion_ner.csv` |
| Entidad que más falló; mayúsculas y siglas | `salida/09_resumen_errores.csv`, reporte sección 6 |
| ¿Qué respuestas tienen evidencia textual y cuáles quedan incompletas? | `salida/respuestas.csv`, `anotaciones/valoraciones.yaml` |
| Con embeddings densos, ¿qué consulta mejoraría? | Reporte sección 4 (sinónimos: Q6, Q7, Q4) |
| Cualquier función del código | `docs/guia_defensa.md` |

### D. Plantilla de `docs/decisiones.md`

```
# Decisiones del proyecto
## Fase 0 (fecha)
- SO: ...  Python: ...  uv: ...  pandoc: ...  TeX: ...
- Repo: ...  Alumno: ...  Plazo vigente: ...
- Q9: ... ventana ... pregunta ...
- Q10: ...
- Horas disponibles: ...
- Utilerías: mensaje enviado al profesor (fecha); respuesta: ...
- Estado previo: commit entregado ... / ninguno
## Contratos del kit (fecha): ver docs/contratos_kit.md; diferencias con el PRD: ...
## Decisiones posteriores
- (fecha) Criterio de relevancia fijado: ...
- (fecha) Convenciones de anotación fijadas: ...
- (fecha) NER principal: ... revisión ... criterio ...
- (fecha) Etiqueta reglas-congeladas en el commit ...
- (fecha) Sustitución de pasaje gold Q4 rango 7 por el siguiente sorteado: 18 palabras de contenido (< 25).
- (fecha) Cambio posterior al congelamiento: regex MONTO acepta "1.200"; F1 MONTO combinado 0.71 -> 0.74 (exploratorio).
```

### E. Historial de versiones unificadas

| Versión | Fecha | Aporte principal que conserva este documento |
| --- | --- | --- |
| 1.0 | 26 de octubre de 2026 | Arquitectura modular, contratos del kit, app de anotación, estructura del reporte, guía de estilo, plan de recortes |
| 1.1 | 2 de noviembre de 2026 | `inicio_cuerpo`, limpieza de ruido auditada, pool de cuatro variantes, conjunto de selección NER, congelamiento de reglas, prioridades P0 a P2, `make resultados` sin TeX, regex MONTO corregida |
| 1.2 | sin fecha | Verificación del kit antes de programar, NER único por criterio técnico, cantidades auxiliares, no eliminar casi duplicados sin auditoría, pasajes gold sin entidades, plan por dependencias |
| 2.0 | 31 de octubre de 2026 | Marcas EX/DP/OP/PV, matriz de rúbrica, `posicion` en `ranking.csv`, emparejamiento global de la muestra, `respuestas.csv` con estados de evidencia, manifiesto e invalidación, pruebas T01 a T16, condiciones C01 a C18, duración realista de la presentación |
| Plantilla | sin fecha | Desempate numérico, prioridad de colisiones entre reglas, FECHA con modificador, vacunas como ORG, telemetría de tiempos |
| 3.0 unificada | 4 de noviembre de 2026 | Este documento; conflictos resueltos en 0.3 |

---

*Fin del PRD unificado.*
