---
name: kit-contratos
description: "Usa esta skill cuando arranque el proyecto (hito H0): hay que correr la Fase 0 con el alumno, copiar el kit del profesor a kit/ con hashes, escribir las pruebas de contrato de corpus.py y evaluar.py, o resolver una duda sobre qué puede y qué no puede tocarse del kit."
---
# Kit de inicio: Fase 0, copia íntegra y pruebas de contrato (H0)

## Cuándo usarla

- Primera sesión del proyecto o repo sin `kit/`, sin `docs/decisiones.md` o sin `docs/contratos_kit.md`.
- Antes de integrar `kit/evaluar.py` en cualquier script (`05_evaluar_ir.py`, `09_evaluar_ie.py`).
- Cuando una función del kit se comporta distinto a lo que describe el PRD §3 (pendientes P01 y P04).
- Cuando alguien proponga "arreglar" un archivo de `kit/`: la respuesta siempre es un adaptador, nunca una edición.
- Condición para cerrar H0 (PRD §12.2): `docs/contratos_kit.md` escrito, `make setup` y `make contratos` verdes, primer commit.

## Fase 0 del proyecto (qué preguntar y qué comprobar)

Regla: se pregunta solo lo que no se puede inspeccionar (PRD §1.3). Todo lo demás se comprueba con comandos y se reporta con evidencia.

### Comprobar directamente (sin preguntar)

1. `uname -sm` y `python3 --version`: se requiere Python 3.11 o 3.12; si no, `uv python install 3.11`.
2. `uv --version`, `git --version`, `pandoc --version`, `xelatex --version`. Si falta TeX el proyecto avanza: solo `make reporte` lo necesita.
3. Acceso a Hugging Face con una descarga de prueba pequeña (`huggingface_hub`). Si la red bloquea, se detiene y se reporta; mitigación: descargar desde otra red y copiar `kit/data/discursos.parquet` y la caché `HF_HOME` (PRD §14).
4. Estado del repo: `git log --oneline`, `git tag`, archivos ya existentes en `salida/`, `anotaciones/`, raíz.

### Preguntar al alumno (una sola tanda, respuestas cortas)

1. Identidad: nombre completo (portada y láminas), usuario de GitHub, nombre del repo (sugerido `examen1-mineria-textos`), público o privado con acceso al profesor.
2. Ruta de los cuatro archivos del kit: `corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`.
3. Plazo vigente: fecha y hora reales de entrega y de presentación (el enunciado fija 28 de octubre 20:00 y 4 de noviembre; se registra lo que aplique, sin inventar prórrogas, P05) y horas disponibles por día.
4. Estado previo: si ya existe un commit entregado. Si lo hay, se conserva su identificación y las mejoras posteriores se registran aparte; nunca se reescribe qué versión fue entregada.
5. Q9 y Q10 NO se preguntan aquí: se eligen después de explorar el corpus (PRD §5.2). Los valores por defecto (Guardia Nacional, Tren Interoceánico) solo se usan si el alumno pide que el asistente decida, con la advertencia de que otros compañeros pueden elegir lo mismo.

### Mensaje al profesor sobre utilerías (P07)

1. El asistente redacta un mensaje corto con las utilerías de la tabla del PRD §2.2 que no aparecen en el enunciado (`torch`, `pyarrow`, `streamlit`, `plotly`, `pypdf`, `python-pptx`, `pytest`, `pyyaml`, `rich`, `uv`) y el papel de cada una.
2. El alumno lo envía y registra la respuesta en `docs/decisiones.md`.
3. Mientras no haya respuesta se trabaja con ellas; cada una tiene su alternativa en la misma tabla.

### Registro

Escribir `docs/decisiones.md` con la plantilla del PRD anexo D, sección `## Fase 0 (fecha)`: SO, Python, uv, pandoc, TeX; repo, alumno, plazo vigente; Q9 y Q10 (pendientes hasta §5.2); horas disponibles; utilerías (fecha de envío y respuesta); estado previo. Dejar la línea `## Contratos del kit (fecha)` apuntando a `docs/contratos_kit.md` con las diferencias respecto al PRD.

## Copia del kit y hashes

1. `mkdir -p kit && cp <ruta_kit>/{corpus.py,consultas.csv,gazetteer_dependencias.csv,evaluar.py} kit/` (sustituir la ruta por la que dio el alumno; no renombrar nada).
2. `sha256sum kit/corpus.py kit/consultas.csv kit/gazetteer_dependencias.csv kit/evaluar.py` y pegar la salida íntegra en `docs/contratos_kit.md`, sección "Hashes SHA-256 de los originales".
3. Confirmar que `kit/data/` existe o será creado por `cargar_corpus()` (caché `kit/data/discursos.parquet`); el parquet no entra en los hashes del kit, su hash va a `data/corpus_meta.json` (PRD §6.1.1).
4. Verificar con `git diff --stat kit/` en cada sesión posterior que el directorio sigue intacto; cualquier diferencia es un error que se revierte, no una decisión.

## Pruebas de contrato (H0)

Archivo: `tests/test_contratos_kit.py`. Objetivo `make contratos` (PRD §10). Prueba T01 del PRD §13.1. Usan solo fixtures sintéticos construidos en el propio test; nunca juicios ni gold reales.

### `kit/corpus.py` (PRD §3.1, PV)

1. `cargar_corpus(forzar: bool = False) -> pd.DataFrame` con columnas `doc_id` (int, 0..N-1 consecutivo), `url`, `titulo`, `fecha` (`datetime64`, admite NaT), `texto`; cachea en `kit/data/discursos.parquet`. Si la descarga es cara, marcar la prueba como `test-lento` y verificar la firma por `inspect.signature`.
2. `limpiar_basico(texto: str) -> str`: normaliza espacios y saltos, pero debe conservar los saltos que necesita el reconocimiento de interlocutores. Fixture: dos marcas `NOMBRE:` en líneas distintas; tras limpiar, `RE_INTERLOCUTOR` con `re.MULTILINE` sigue encontrando ambas.
3. `partir_por_interlocutor(texto: str) -> list[tuple[str, str]]`: devuelve pares `(interlocutor, texto)`; comprobar con texto sin marcas (una sola tupla o la convención real, anotarla).
4. `ventanas(tokens: list[str], tam: int, paso: int) -> list[str]`: tamaño y traslape correctos; caso con menos tokens que `tam`.
5. `segmentar_pasajes(df, tam=200, paso=150, min_tokens=40) -> pd.DataFrame` con columnas `passage_id` (`f"{doc_id}_{posicion}"`), `doc_id`, `fecha`, `titulo`, `posicion`, `interlocutor`, `texto`. Se sustituye por la función propia del PRD §6.1 pero su esquema real es el contrato que esa función debe conservar.

### `kit/evaluar.py` modo IR (PRD §3.4)

1. CLI: `python kit/evaluar.py ir juicios_relevancia.csv ranking.csv` produce `resultados_ir.csv`. Verificar nombre y ubicación reales del archivo de salida.
2. Columnas leídas de `ranking.csv`: solo `query_id, modelo, rango, passage_id`; las demás (`variante`, `doc_id`, `fecha`, `posicion`, `puntaje`) deben ignorarse. Fixture con columnas extra.
3. Denominador de AP: fixture con 4 relevantes en el pool y una lista que recupera 2; AP debe dividir entre 4 (total de relevantes del pool), no entre los recuperados.
4. Lista con menos de k resultados: fixture con 3 filas para una consulta; no debe fallar ni rellenar.
5. Pasaje no juzgado cuenta como no relevante; consulta sin relevantes: anotar qué AP devuelve (0, NaN o se omite).
6. Columnas reales de salida: comprobar presencia de `relevantes_recuperados`, `relevantes_en_pool`, `no_juzgados` y de la fila `PROMEDIO (MAP = AP)` por modelo; anotar los nombres exactos aunque difieran del PRD.

### `kit/evaluar.py` modo IE (PRD §3.4)

1. CLI: `python kit/evaluar.py ie gold_entidades.csv entidades.csv` produce `resultados_ie.csv`.
2. Solo evalúa pasajes presentes en el gold; coincidencia exacta de `(passage_id, tipo, inicio, fin)`. Fixture con una entidad desplazada un carácter: cuenta como error.
3. Métodos: `regla` se evalúa con filas `regla` + `ambos`; `modelo` con `modelo` + `ambos`; `combinado` con todas. Fila con `metodo` distinto se descarta en silencio: comprobar que no revienta.
4. Deduplicación entre consultas (P04): el mismo `passage_id` bajo Q1 y Q3 con la misma entidad; anotar si cuenta una o dos veces.
5. Pasaje gold sin entidades (P04): un `passage_id` presente en `entidades.csv` pero ausente del gold y viceversa; anotar si se evalúa o se omite (impacta PRD §6.11).
6. Tipos sin soporte: anotar qué filas emite para un `tipo` fuera de {PER, ORG, LOC, FECHA, MONTO}.
7. Archivos vacíos (solo cabecera) en ambos modos: anotar el comportamiento.

### Cierre

Escribir en `docs/contratos_kit.md`: firmas reales, cabeceras, argumentos de CLI, columnas de salida, comportamiento ante vacíos y duplicados, y una tabla "PRD dice / kit hace" por cada diferencia. Copiar el resumen a `docs/decisiones.md`.

## Qué verificar de cada archivo del kit

| Archivo | Verificación | Dónde se anota |
| --- | --- | --- |
| `kit/corpus.py` | Firmas de las 5 funciones, asignación de `doc_id`, tipo de `fecha`, caché, saltos conservados por `limpiar_basico` | `docs/contratos_kit.md` |
| `kit/consultas.csv` | Cabecera `query_id,consulta,desde,hasta,pregunta_extraccion`; Q1 a Q8 coinciden literalmente (texto, `desde`, `hasta`) con la tabla del PRD §5.1; sin saltos tipográficos del PDF | Prueba en `test_contratos_kit.py` + `docs/contratos_kit.md` |
| `kit/gazetteer_dependencias.csv` | Cabecera `nombre,siglas,tipo`; contar entradas (PRD 1.0 dice 76, PV) y listar los valores distintos de `tipo`; confirmar que `obra` existe (→ LOC) | `docs/contratos_kit.md` |
| `kit/evaluar.py` | CLI `ir` e `ie`, columnas leídas e ignoradas, AP, duplicados, gold sin entidades, salida | `docs/contratos_kit.md` |

Q9 y Q10 nunca se agregan a `kit/consultas.csv`: van en `data/consultas.csv` (copia del kit más dos filas) y todos los scripts leen de esa copia (PRD §3.2). Las ampliaciones del gazetteer van en `config/gazetteer_extendido.csv` (PRD §3.3).

## Reglas inviolables

1. `kit/` nunca se edita, ni para corregir un error evidente; los cuatro hashes de `docs/contratos_kit.md` deben seguir coincidiendo hasta la entrega.
2. `kit/evaluar.py` se usa tal cual y produce las métricas oficiales; `resultados_ir.csv` y `resultados_ie.csv` son su salida íntegra sin renombrar columnas (PRD §3.5). Diagnósticos propios van en archivos aparte.
3. Toda adaptación vive en `src/mtx/adaptadores_kit.py`, único punto de contacto con `kit/` (PRD §9). Ningún otro módulo importa de `kit/` directamente.
4. Una incompatibilidad bloquea solo la etapa afectada hasta tener un adaptador transparente; los módulos independientes siguen avanzando (P01, P02).
5. Las pruebas de contrato usan fixtures sintéticos; jamás `anotaciones/juicios_relevancia.csv` ni ningún gold real.
6. Q1 a Q8 se usan sin reformular; el gazetteer original no se toca.
7. Si hay un commit ya entregado, se conserva su identificación y no se reescribe la versión entregada (PRD §1.3 punto 8, §11.5).

## Salidas de este hito

- `kit/corpus.py`, `kit/consultas.csv`, `kit/gazetteer_dependencias.csv`, `kit/evaluar.py` idénticos a los originales.
- `docs/contratos_kit.md`: hashes SHA-256, firmas, cabeceras, CLI, columnas de salida, comportamiento ante vacíos y duplicados, tabla de diferencias con el PRD.
- `docs/decisiones.md` con la sección "Fase 0" completa (plantilla PRD anexo D) y la línea de contratos del kit.
- `tests/test_contratos_kit.py` verde vía `make contratos`; `make setup` verde.
- Mensaje al profesor sobre utilerías redactado y entregado al alumno para su envío (P07).
- Primer commit, por ejemplo `chore: kit original, hashes y pruebas de contrato` (PRD §11.5).

## Skills relacionadas

- `system-onboarding`: arranque del repo, `pyproject`, `Makefile` y `make setup`, que H0 exige junto con esta skill.
- `session-resume`: en sesiones posteriores, releer `docs/decisiones.md` y `docs/contratos_kit.md` antes de tocar nada.
- `integridad-congelacion`: verificación periódica de hashes de `kit/` y de los artefactos congelados.
- `corpus-segmentacion`: consume las firmas verificadas de `corpus.py` y el esquema de `segmentar_pasajes`.
- `evaluacion-ie`: depende de lo caracterizado aquí sobre duplicados y pasajes gold sin entidades (P04).
