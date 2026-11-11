# Recuperación y extracción de información en discursos presidenciales (2018 a 2024)

Examen 1 de Minería de Textos, UNAM FES Acatlán. Alumno: Arturo Jaramillo Salmerón (continúa
individualmente, por indicación del profesor, el repositorio que el profesor inició hasta H5).

## 1. Qué hace el sistema

Sobre 2,294 versiones estenográficas de conferencias presidenciales (snapshot
`carevies/discursos_AMLO`), el sistema limpia el texto, lo parte en 127,739 pasajes y recupera los
10 más relevantes por consulta con TF-IDF y BM25, con y sin filtro de fecha, para 10 consultas.
Sobre el top-10 del mejor modelo (BM25 con filtro) extrae entidades PER, ORG, LOC, FECHA y MONTO
combinando reglas con gazetteers y un NER preentrenado, las evalúa contra un gold anotado a mano y
arma tablas de respuesta con evidencia textual. Reporte: [`reporte/reporte.pdf`](reporte/reporte.pdf).

## 2. Requisitos

Python 3.11 y [`uv`](https://docs.astral.sh/uv/) para todas las cifras; `pandoc` y una
distribución TeX con `xelatex` solo para compilar el PDF.

- **Windows**: `winget install astral-sh.uv`, `winget install JohnMacFarlane.Pandoc`,
  `winget install MiKTeX.MiKTeX`. Windows no trae `make`: usar la tabla de la sección 4.
- **macOS**: `brew install uv pandoc`, `brew install --cask basictex`,
  `sudo tlmgr install collection-fontsrecommended booktabs`.
- **Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`,
  `sudo apt install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-extra`.

En Windows conviene fijar `PYTHONUTF8=1` y conservar `core.autocrlf=false`: el repo usa fin de
línea LF (`.gitattributes`) y con CRLF no coinciden los hashes de `kit/`.

## 3. Instalación desde cero

```bash
git clone https://github.com/ARJASA67/An-lisis-de-Ma-aneras-2018-2024.git
cd An-lisis-de-Ma-aneras-2018-2024
uv sync                                   # make setup: entorno con torch CPU
uv run python -m pytest -q tests/test_contratos_kit.py   # make contratos
uv run python scripts/01_corpus_y_pasajes.py             # make corpus
```

`01_corpus_y_pasajes.py` descarga el snapshot de Hugging Face y comprueba su hash contra
`data/corpus_meta.json` (sha256 `e42531f2…`, commit del dataset `2c463bb`). Si el hash no
coincide, el dataset cambió en origen: las cifras ya no son comparables y hay que recuperar el
commit registrado (ver `docs/decisiones.md`). Tamaño y tiempo de la descarga: pendientes de medir.

## 4. Reproducir resultados

Los insumos humanos (`juicios_relevancia.csv`, `anotaciones/`) y la caché del NER
(`data/cache_ner/`) están versionados, así que las cifras se reproducen sin anotar ni descargar el
modelo. `make resultados` no necesita TeX; `make entrega` añade el PDF.

| Objetivo de make | Equivalente sin make (Windows: `.venv/Scripts/python.exe` en lugar de `uv run python`) |
| --- | --- |
| `make corpus` | `uv run python scripts/01_corpus_y_pasajes.py` |
| `make indice` | `uv run python scripts/02_indice.py` (42 s medidos) |
| `make ranking` | `uv run python scripts/03_ranking.py` |
| `make pool` | `uv run python scripts/04_pool.py` |
| `make evaluar-ir` | `uv run python scripts/05_evaluar_ir.py` |
| `make reglas` | `uv run python scripts/06_reglas.py` (unos 3 min) |
| `make ner` | `uv run python scripts/07_ner.py` (41.8 s sin caché, 3.4 s con caché) |
| `make extraer` | `uv run python scripts/08_extraer.py` |
| `make evaluar-ie` | `uv run python scripts/09_evaluar_ie.py` (5.7 s) |
| `make tablas` | `uv run python scripts/10_tablas.py` |
| `make reporte` | `uv run python scripts/11_reporte.py` (requiere pandoc y xelatex) |
| `make demo Q=Q3` | `uv run python scripts/13_demo.py --q Q3` (0.5 s) |
| `make demo CONSULTA="..."` | `uv run python scripts/13_demo.py --consulta "..." --desde AAAA-MM-DD --hasta AAAA-MM-DD` |
| `make test` | `uv run python -m pytest -q` (sin red) |
| `make validar` | `uv run python scripts/99_validar.py` |

El PDF se compila con la plantilla por defecto de pandoc más `reporte/encabezado.tex`
(equivale al comando del PRD con `--template=plantilla.tex`).

## 5. Flujo completo con pasos humanos

`make explorar` → elegir Q9 y Q10 → `make corpus indice ranking pool` → `make app` (juicios de
relevancia) → `make validar evaluar-ir` → `make reglas` → revisar siglas y gazetteer → `make
congelar` → `make ner muestra-gold` → `make app` (gold, modo ciego) → `make extraer evaluar-ie
tablas` → escribir `anotaciones/valoraciones.yaml` → `make reporte`.

Las valoraciones las escribe el alumno: una entrada por consulta (`Q1` a `Q10`) con `texto` y
`tabla_sha256`, el hash de la tabla valorada que imprime `10_tablas.py` en
`salida/10_tablas_hash.json`. Si la tabla cambia, la valoración se marca como invalidada.

## 6. Mapa del repo

```text
kit/                 archivos del profesor, sin modificar (hashes en docs/contratos_kit.md)
src/mtx/             lógica: corpus, preproceso, indice, ranking, pool, evaluacion, reglas,
                     ner_modelo, fusion, normalizacion, muestreo, gold, respuestas, reporte, app/
scripts/NN_*.py      orquestación numerada del pipeline (00 a 13 y 99)
tests/               pruebas rápidas sin red y lentas (marcador lento)
config/              consultas Q9 y Q10, limpieza, stoplist, gazetteers, NER, tablas de respuesta
data/                consultas, metadatos del corpus e índice, modelo elegido, caché NER
anotaciones/         insumos humanos: juicios, muestra y gold, cierre del gold, valoraciones
salida/              todas las cifras, tablas y auditorías que cita el reporte
reporte/             reporte.md (prosa aprobada), tablas, figuras y reporte.pdf
laminas/             guion y salida de contingencia de la demo
docs/                decisiones con fecha, contratos del kit, guía de la app
```

Entregables en la raíz: `ranking.csv`, `juicios_relevancia.csv`, `resultados_ir.csv`,
`entidades.csv`, `gold_entidades.csv` y `resultados_ie.csv`.

## 7. Decisiones de diseño y limitaciones

El detalle con fecha está en [`docs/decisiones.md`](docs/decisiones.md). Las principales: pasajes
de 200 palabras con paso de 150 y mínimo de 40, con la marca del interlocutor fuera del índice;
limpieza por lista cerrada de acotaciones; BM25 propio ($k_1 = 1.5$, $b = 0.75$) y TF-IDF de
scikit-learn; pool como unión de los top-10 de las cuatro variantes y relevancia temática; ganador
por MAP entre las variantes con filtro; reglas y gazetteers congelados (etiqueta
`reglas-congeladas`) antes de abrir el gold; un NER elegido por criterio técnico; fusión por span
exacto.

Limitaciones: gold de 20 pasajes (6 FECHA y 6 MONTO); un solo NER, sin conjunto de selección;
el 64.9 % de las intervenciones de reporteros queda bajo el mínimo de 40 palabras; juicios de
varias personas sin acuerdo medido; AP depende del pool de las cuatro variantes.

## 8. Resultados principales

<!-- resultados:inicio -->
Cifras autogeneradas por `scripts/11_reporte.py` desde `salida/`; no se editan a mano.

Recuperación (`salida/resultados_ir.csv`, oficial, y `salida/05_resultados_ir_ventana.csv`):

| Variante | P@5 | P@10 | MAP oficial | MAP con ventana |
| :----------------- | -----: | -----: | -----------: | ---------------: |
| TF-IDF con filtro | 0.680 | 0.630 | 0.385 | 0.432 |
| BM25 con filtro | 0.760 | 0.780 | 0.575 | 0.625 |
| TF-IDF sin filtro | 0.620 | 0.600 | 0.360 | 0.328 |
| BM25 sin filtro | 0.720 | 0.750 | 0.548 | 0.499 |

Extracción (`salida/09_ie_detalle.csv`; s/c = el NER no cubre el tipo):

| Tipo | Gold | Reglas P / R / F1 | Modelo P / R / F1 | Combinado P / R / F1 |
| :----- | ----: | ------------------: | ------------------: | --------------------: |
| PER | 36 | 0.88 / 0.42 / 0.57 | 0.53 / 0.53 / 0.53 | 0.63 / 0.92 / 0.75 |
| ORG | 33 | 0.76 / 0.39 / 0.52 | 0.79 / 0.67 / 0.72 | 0.70 / 0.70 / 0.70 |
| LOC | 102 | 0.81 / 0.50 / 0.62 | 0.86 / 0.77 / 0.81 | 0.79 / 0.86 / 0.83 |
| FECHA | 6 | 0.67 / 0.33 / 0.44 | s/c | 0.67 / 0.33 / 0.44 |
| MONTO | 6 | 1.00 / 0.50 / 0.67 | s/c | 1.00 / 0.50 / 0.67 |
| TODOS | 183 | 0.82 / 0.46 / 0.59 | 0.77 / 0.66 / 0.71 | 0.74 / 0.81 / 0.77 |
<!-- resultados:fin -->

## 9. Uso de IA

Se usó un asistente de IA (Claude, en Claude Code) en todo el proyecto, antes y después del relevo.

- **Código escrito por el asistente**: todo `src/mtx/` (incluida la app), todos los
  `scripts/NN_*.py`, todos los `tests/`, el `Makefile`, `pyproject.toml` y las configuraciones de
  `config/` que no son criterios humanos. En esta etapa (Arturo): `src/mtx/evaluacion.py` (parte
  IE), `src/mtx/respuestas.py`, `src/mtx/reporte.py`, `scripts/09_evaluar_ie.py`,
  `10_tablas.py`, `11_reporte.py`, `13_demo.py`, `tests/test_evaluacion_ie.py`,
  `tests/test_respuestas.py`, `config/tablas_respuesta.yaml`, `config/excluir_tablas.yaml`. El
  historial completo está en `git log` (commits con la línea Co-Authored-By del asistente).
- **Prosa**: el reporte y este README los redactó el asistente a partir de las cifras de `salida/`;
  el alumno revisó y aprobó el reporte en tres cortes, sección por sección (registro en
  `docs/decisiones.md`).
- **Decisiones humanas antes del relevo** (etapa iniciada por el profesor, registradas en
  `docs/decisiones.md`): aprobación de Q9 y Q10, criterios de relevancia y de anotación, revisión
  de siglas del gazetteer.
- **Lo que decidió o hizo Arturo**: aprobación del NER, anotación y cierre del gold en la app sin
  ver predicciones (modo ciego, 1.5 horas), valoraciones de las tablas y aprobación de cada corte del reporte.
- **Juicios de relevancia**: se hicieron a mano antes del relevo, Q1 a Q4 en la app y Q5 a Q10 en
  una hoja compartida entre compañeros con autorización del profesor. El asistente no juzgó, no
  sugirió valores ni redactó prompts para que otro modelo juzgara.
- **Verificación**: 396 pruebas rápidas sin red, pruebas lentas sobre el corpus real, validadores
  de formato de juicios, gold, entidades y respuestas, y comparación del detalle propio de IE contra
  la salida del kit. Los validadores comprueban formato, no la corrección de las decisiones humanas.

## 10. Dependencias y por qué

| Biblioteca | Papel | En el enunciado |
| --- | --- | --- |
| pandas, numpy | tablas y arreglos | sí |
| scikit-learn | TF-IDF (vectorizador) | sí |
| nltk | stemmer Snowball | sí |
| regex | expresiones regulares | sí |
| datasets | descarga del corpus | sí |
| transformers, torch (CPU) | NER preentrenado | sí (torch lo requiere transformers) |
| rank_bm25 (desarrollo) | solo para probar el BM25 propio | sí |
| pyarrow | pasajes en Parquet | utilería |
| streamlit | app de anotación | utilería |
| plotly, kaleido | figuras (en lugar de matplotlib, por indicación del profesor) | utilería |
| pypdf | contar páginas del PDF | utilería |
| python-pptx | láminas (opcional) | utilería |
| pyyaml, rich, openpyxl | configuración, demo en terminal, hoja de juicios | utilería |
| pytest, ruff (desarrollo) | pruebas y estilo | utilería |

El índice invertido y BM25 están escritos a mano. La consulta al profesor sobre las utilerías
está en `docs/mensaje_profesor_utilerias.md`; al 11 de noviembre de 2026 el profesor no respondió.
`requirements.txt` se exporta de `uv.lock` con `uv export --no-dev --format requirements-txt`.
