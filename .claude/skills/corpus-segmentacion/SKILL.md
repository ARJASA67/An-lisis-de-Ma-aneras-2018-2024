---
name: corpus-segmentacion
description: "Usa esta skill cuando vayas a cargar el corpus de discursos, limpiar ruido (D05), segmentar pasajes con marca de interlocutor reinyectada, generar data/pasajes.parquet, o descubrir y registrar las consultas Q9 y Q10 (src/mtx/corpus.py, scripts 00 y 01)."
---
# Corpus, limpieza auditada y segmentación propia

## Cuándo usarla
- Al implementar o modificar `src/mtx/corpus.py` (carga, `limpiar_ruido`, `segmentar`).
- Al escribir o ejecutar `scripts/00_descubrir_consultas.py` (`make explorar`) o `scripts/01_corpus_y_pasajes.py` (`make corpus`).
- Al tocar `config/limpieza.yaml`, `config/candidatos_q9q10.yaml`, `data/consultas.csv` o `data/corpus_meta.json`.
- Al escribir `tests/test_corpus.py` o cuando falle `uv run pytest tests/test_corpus.py`.
- Al revisar por qué cambió `data/pasajes.parquet` o un `passage_id` ya anotado.

## Prerrequisitos y congelaciones que aplican
1. H0 terminado: `make contratos` verde y `docs/contratos_kit.md` con las firmas reales de `cargar_corpus`, `limpiar_basico`, `partir_por_interlocutor` y `ventanas` (PRD §3.1). Las interfaces del PRD son PV hasta inspeccionar el kit.
2. Toda llamada al kit pasa por `src/mtx/adaptadores_kit.py`; nunca se edita `kit/`.
3. Decisiones que gobiernan este módulo (PRD §4): D02 (200/150/40), D03 (marca reinyectada e `inicio_cuerpo`), D04 (reporteros se conservan e indexan), D05 (limpieza antes de segmentar). Se pueden revisar con motivo documentado solo antes de rankings y juicios.
4. Congelación: una vez iniciados los juicios, cualquier cambio en limpieza o segmentación crea una versión experimental nueva, declara qué invalida y nunca reasigna anotaciones por `posicion` (PRD §6.1.3, §4). Antes de cambiar parámetros, consulta `integridad-congelacion`.
5. Q1 a Q8 son intocables (EX): no se reformulan ni se reordenan; Q9 y Q10 solo se agregan en `data/consultas.csv` (PRD §3.2).

## Carga y huella del corpus
1. Llama a `cargar_corpus()` vía `adaptadores_kit`. Columnas esperadas: `doc_id` (int, 0..N-1), `url`, `titulo`, `fecha` (datetime64, puede ser NaT), `texto`; caché en `kit/data/discursos.parquet`.
2. Conserva la asignación de `doc_id` del snapshot. Nunca reordenes, renumeres ni filtres el DataFrame antes de registrar la huella.
3. Escribe `data/corpus_meta.json` con: SHA-256 de `kit/data/discursos.parquet`, número de filas, fecha de descarga y, si `huggingface_hub` la expone, el commit del dataset (PRD §6.1.1). Este archivo sí se versiona; el parquet no.
4. `make validar` compara el hash guardado contra el parquet actual y avisa si el corpus cambió. Un hash distinto invalida pasajes, rankings y pool.
5. Escribe `salida/01_estadisticas_corpus.json`: número de discursos, textos vacíos, rango de fechas, discursos con `fecha` NaT o inválida, longitud en palabras (mínimo, mediana, media, máximo, percentiles 10 y 90) y discursos sin marcas de interlocutor.

## Limpieza de ruido auditada
`limpiar_ruido(df) -> tuple[pd.DataFrame, dict]` corre antes de segmentar (D05). Conserva el texto de origen y produce `texto_canonico` como columna separada. Los patrones viven en `config/limpieza.yaml` para que el reporte los cite; cada operación se cuenta por `doc_id` en `salida/01_auditoria_corpus.csv` (PRD §6.1.2).

Orden obligatorio de operaciones:
1. **Normalización previa:** CRLF a LF, Unicode NFC, espacios dentro de cada línea. Preserva los saltos de línea que `partir_por_interlocutor` necesita (`RE_INTERLOCUTOR` usa `^` con `re.MULTILINE`).
2. **Acotaciones:** elimina las que no son habla con el patrón `\((?:[A-ZÁÉÍÓÚÑÜ ]{3,40})\)` (`(APLAUSOS)`, `(INAUDIBLE)`, `(RISAS)`, `(PROYECCIÓN DE VIDEO)`). Cuenta por tipo.
3. **Separadores y encabezados repetidos:** líneas compuestas solo por guiones, asteriscos o `+`; encabezados fijos que se repiten al inicio (`VERSIÓN ESTENOGRÁFICA...`, `CONFERENCIA DE PRENSA DEL PRESIDENTE...`). El encabezado se queda en `titulo`, no en el cuerpo.
4. **Duplicados exactos:** hash del texto normalizado (minúsculas, sin acentos, espacios colapsados). Se conserva el menor `doc_id`; el resto se marca como excluido de la segmentación.
5. **Casi duplicados:** misma `fecha` y Jaccard ≥ 0.9 sobre shingles de 5 palabras. Misma regla de exclusión; se listan en `salida/01_duplicados.csv` con su similitud. Cada exclusión es reversible desde `config/limpieza.yaml` (U12). Los `doc_id` nunca se renumeran.
6. **Reparación de fechas:** candidata desde `titulo` (regex de fecha en español) y desde `url` (`AAAA/MM/DD` o `AAAA-MM-DD`). Reglas en orden:
   - `fecha` NaT y hay candidata: se usa la candidata.
   - `fecha` fuera de [2018-12-01, 2024-09-30] y candidata dentro: se usa la candidata.
   - `fecha` y candidata difieren más de 3 días: se usa la del título y se marca.
   - Título y URL se contradicen: no se corrige, se señala.
   - Nunca se inventa una fecha. Columnas resultantes: `fecha_original`, `fecha_fuente` ∈ {`original`, `titulo`, `url`, `ninguna`}. Salida: `salida/01_fechas_reparadas.csv`.
7. **Resumen:** `salida/01_limpieza.json` con el conteo de cada operación y el porcentaje de caracteres descartados (alimenta la sección 2 del reporte).

## Segmentación propia e invariantes
`segmentar(df, tam=200, paso=150, min_tokens=40, reinyectar_marca=True) -> pd.DataFrame` sustituye a `segmentar_pasajes` del kit conservando esquema de columnas y `passage_id` (PRD §3.1, §6.1.3). Reutiliza `limpiar_basico`, `partir_por_interlocutor` y `ventanas` del kit; no los reimplementes.

Algoritmo:
1. `texto = limpiar_basico(texto_canonico)`; solo discursos no excluidos.
2. `intervenciones = partir_por_interlocutor(texto)`. Un texto sin marcas es una sola intervención con `quien == ""`.
3. Por cada `(quien, que)`: `toks = que.split()`; por cada `trozo` de `ventanas(toks, tam, paso)`:
   - menos de `min_tokens` palabras: se descarta y se cuenta con su interlocutor;
   - si no, `texto = f"{quien}: {trozo}"` cuando `quien != ""` y `reinyectar_marca`; `trozo` en otro caso.
4. `inicio_cuerpo = len(quien) + 2` si se reinyectó la marca; `0` si no.
5. `posicion` es un contador por discurso que avanza **solo** con pasajes conservados (los descartes no consumen posición). `passage_id = f"{doc_id}_{posicion}"`.
6. `es_reportero = interlocutor in {"PREGUNTA", "INTERLOCUTOR", "INTERLOCUTORA"} or interlocutor.startswith("PREGUNTA")`. Una marca desconocida no se etiqueta reportero.

Invariantes que `tests/test_corpus.py` debe comprobar:
- `texto[inicio_cuerpo:] == trozo` y `texto[:inicio_cuerpo] == f"{quien}: "` en el 100 % de los pasajes con marca.
- Offsets en índices de carácter Python sobre el `texto` completo e inmutable, `inicio` inclusivo y `fin` exclusivo (PRD §3.6). El preprocesamiento de IR nunca altera `texto`.
- Columnas exactas y en este orden: `passage_id, doc_id, fecha, fecha_original, fecha_fuente, titulo, url, posicion, interlocutor, texto, inicio_cuerpo, n_palabras, es_reportero, marca_reinyectada, texto_sha256, intervencion_id, token_inicio, token_fin`.
- `n_palabras` mide el texto completo visible y puede superar 200 por el prefijo.
- `intervencion_id`, `token_inicio`, `token_fin` ubican la ventana dentro de su intervención (sirven para detectar evidencia repetida en ventanas solapadas).
- Determinismo: dos corridas producen el mismo `data/pasajes.parquet` (verificar con hash de filas ordenadas). Sin fuentes de aleatoriedad ni dependencia del orden de iteración de conjuntos.

Salidas complementarias:
- `salida/01_descartes_cortos.csv` (PRD §6.1.4): intervenciones y ventanas descartadas por `min_tokens`, desglosadas por reportero o funcionario, con 20 ejemplos. Si las preguntas de reporteros descartadas superan el 10 % de sus intervenciones, el reporte lo discute como costo de D02.
- `salida/01_sensibilidad_segmentacion.csv` (PRD §6.1.5, OP, P1, antes del pooling): configuraciones `(120, 90, 40)`, `(200, 150, 40)`, `(300, 225, 40)`, `(200, 150, 15)`; reporta número de pasajes, longitud media, proporción de pasajes de reporteros, intervenciones descartadas, solape TF-IDF/BM25 en el top-10 con filtro y discursos distintos en el top-10. Es descriptivo: no elige segmentación ni cambia la base D02.

## Descubrimiento de Q9 y Q10
Script `scripts/00_descubrir_consultas.py` (`make explorar`, PRD §5.2). El script calcula señal; el alumno elige.
1. Lee los candidatos de `config/candidatos_q9q10.yaml` (ocho sugerencias editables: Guardia Nacional, Insabi, Tren Interoceánico, reforma eléctrica y litio, aranceles y acuerdo migratorio, Banco del Bienestar, Mexicana de Aviación, Ayotzinapa). Son sugerencias, no consultas elegidas.
2. Para cada candidato calcula sobre `data/pasajes.parquet`: pasajes con al menos un término semilla, discursos distintos, distribución por año y tres pasajes de ejemplo de 300 caracteres.
3. Escribe `salida/00_candidatos_q9q10.md`. Prohibido: usar métricas del gold o reformular Q1 a Q8.
4. El alumno elige dos temas distintos entre sí y de Q1 a Q8, y redacta `consulta`, `desde`, `hasta` y `pregunta_extraccion`. La redacción final lleva `[VALIDAR]`: no la des por cerrada sin confirmación humana.
5. Crea `data/consultas.csv` = filas del kit tal cual + Q9 + Q10. Todos los scripts posteriores leen de esta copia, nunca del kit.
6. Si la elección deja menos de dos pasajes disponibles para el gold, se resuelve antes de congelar consultas. Q9 y Q10 participan en todo el protocolo (ranking, pool, juicios, mejor modelo, gold, tablas).

## Salidas y criterios de aceptación
Lista de verificación antes de dar por terminado `make corpus` (PRD §6.1.6, T01, T02):
- [ ] `data/pasajes.parquet` sin `passage_id` duplicados; cada id reconstruye `doc_id` y `posicion`.
- [ ] Todo pasaje tiene `fecha` (NaT permitido), `fecha_fuente` e `inicio_cuerpo` válido; ninguno proviene de un discurso excluido.
- [ ] Generados: `data/corpus_meta.json`, `salida/01_estadisticas_corpus.json`, `salida/01_auditoria_corpus.csv`, `salida/01_duplicados.csv`, `salida/01_fechas_reparadas.csv`, `salida/01_limpieza.json`, `salida/01_descartes_cortos.csv`.
- [ ] `uv run pytest tests/test_corpus.py` en verde, con casos: varias marcas, sin marcas, acentos, saltos CRLF/LF, determinismo por hash, invariante de `inicio_cuerpo`, pérdida de contenido cuantificada (T02).
- [ ] `data/consultas.csv` con las ocho filas del kit literales más Q9 y Q10 validadas.

## Errores frecuentes a evitar
- Segmentar antes de limpiar, o limpiar después: rompe offsets y deja acotaciones dentro de pasajes (D05 exige limpiar primero).
- Reordenar, renumerar o filtrar `doc_id` al excluir duplicados; los excluidos se marcan, no se eliminan del snapshot.
- Avanzar `posicion` con ventanas descartadas: desalinea `passage_id` respecto a lo persistido.
- Calcular `inicio_cuerpo` sobre texto ya tokenizado o normalizado para IR; se calcula sobre el `texto` canónico con mayúsculas y acentos.
- Etiquetar como reportero cualquier marca desconocida; solo el conjunto cerrado y el prefijo `PREGUNTA`.
- Inventar fechas o corregirlas cuando título y URL se contradicen; se señala y se deja `fecha_fuente = "ninguna"` si no hay original válida.
- Usar `segmentar_pasajes` del kit en lugar de `segmentar` propia, o reimplementar `ventanas` y cambiar el solape.
- Volver a segmentar con parámetros nuevos tras iniciar juicios y sobrescribir `data/pasajes.parquet`: debe crearse una versión experimental nueva sin reasignar anotaciones.
- Redactar Q9 y Q10 por cuenta propia o dejar que el script las "elija" por mayor conteo; la decisión es del alumno y lleva `[VALIDAR]`.
- Leer consultas desde `kit/` en lugar de `data/consultas.csv`.

## Skills relacionadas
- `kit-contratos`: firmas reales de `cargar_corpus`, `limpiar_basico`, `partir_por_interlocutor` y `ventanas` verificadas en H0.
- `integridad-congelacion`: hash del corpus, invalidación en cascada y versiones experimentales tras iniciar juicios.
- `indice-ranking`: consume `data/pasajes.parquet` y excluye `texto[:inicio_cuerpo]` de los tokens del índice (D03).
- `pool-juicios-ir`: congela pasajes y consultas antes del primer juicio; cualquier cambio aquí invalida su cierre.
- `session-resume`: estado de H1 (`00_descubrir_consultas.py`, Q9 y Q10, `01_corpus_y_pasajes.py`, `test_corpus` verde).
