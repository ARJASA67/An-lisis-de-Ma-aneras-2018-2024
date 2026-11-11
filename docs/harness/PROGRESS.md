# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- Arnés (`/harnesser`): CLAUDE.md, AGENTS.md, 17 skills, `docs/harness/`.
- H0 cerrado (2026-11-04): entorno `uv` (Python 3.11, torch CPU, plotly y kaleido), `Makefile`, kit copiado a `kit/` con hashes, `src/mtx/adaptadores_kit.py`, 42 pruebas de contrato, `docs/contratos_kit.md`, `docs/decisiones.md`. Alumno: Daniel Gonzalez. Plazo: entrega y presentación el 11 de noviembre de 2026, presentación a las 20:00 (CDMX). Repo de entrega: este GitLab.
- H1 (2026-11-04): `src/mtx/corpus.py` (limpieza, canonización de marcas, fechas, duplicados, segmentación), `config/limpieza.yaml`, `scripts/01_corpus_y_pasajes.py`, `make corpus` verde: 127,739 pasajes, 5 discursos excluidos, 10 fechas reparadas. Descubrimiento de Q9 y Q10 (`make explorar`, `salida/00_candidatos_q9q10.md`). `data/consultas.csv` con Q9 y Q10 en borrador (`make consultas`). 79 pruebas rápidas verdes.

- H2 en curso (2026-11-08): `preproceso.py`, `indice.py` y `ranking.py` probados. `tests/test_indice.py` (T03, 10 pruebas, contra `CountVectorizer`) y `tests/test_ranking.py` (T04 a T06, 29 pruebas: fórmulas a mano, subclase de `rank_bm25` con 1e-6, ventana de fechas, 0/3/10 candidatos, desempate numérico, marca sin efecto). `scripts/02_indice.py` corrió (`make indice`, 42 s): N = 127,739, vocabulario 35,891, avgdl 72.2, 7.24 M postings, df idéntico al de `CountVectorizer`. Memoria medida: pico de 1.3 GB (el índice como dict no necesita varios GB aquí); `indice.pkl` 43.5 MB. Salidas: `data/{tokens.parquet,indice.pkl,indice_meta.json,tfidf.pkl,tfidf_X.npz}` (las pesadas, ignoradas por git) y `salida/02_{postings.md,vocabulario_top.csv,tokens_consultas.md,memoria.json}`. 133 pruebas rápidas verdes, ruff limpio.

- H2 cerrado salvo juicios (2026-11-08): Q9 y Q10 aprobadas por Daniel (registrado en `docs/decisiones.md`); también confirmó acceso del profesor al repo de GitLab. `scripts/03_ranking.py` (`make ranking`) genera `ranking.csv` (400 filas, copia idéntica en la raíz) y `salida/03_{ranking_detalle,solape_modelos,excluidos_por_filtro}.csv`. `tests/test_ranking_real.py` (lento, 7 pruebas) cubre los criterios bloqueantes: 400 filas y claves únicas, top-10 con filtro dentro de la ventana, Q3 con refinería o Pemex, Q1 con Tren Maya, Q6 con huachicol, TF-IDF distinto de BM25 y `kit/evaluar.py ir` con juicios sintéticos. 140 pruebas verdes (con las lentas). Ningún ranking idéntico entre TF-IDF y BM25; ninguna fila sin señal léxica. Observación para el reporte: la ventana de Q6 (2018-12 a 2019-06) deja solo 11,120 pasajes elegibles y el top-10 sin filtro casi no coincide con el filtrado (1 de 10 en TF-IDF, 0 en BM25).

- Pool (2026-11-08): `src/mtx/pool.py` (construcción, orden con semilla 42, comparación de hashes, `validar_juicios()` de solo lectura), `scripts/04_pool.py` (`make pool`, idempotente, se detiene si el pool cambió y hay juicios) y `tests/test_pool.py` (21 pruebas, T07 y T08). `salida/04_pool.csv`: 176 pares; Q5, Q7 y Q8 bajo 15 pasajes (alto solape entre variantes, sin error), Q6 con 28 y 12 fuera de ventana. Sin juicios.

- App de anotación (2026-11-08): `src/mtx/app/` con Estado y Juicios (`make app`) y alternativa `make app-cli`; `componentes.py` sin Streamlit (escritura atómica con respaldo y revisión, resaltado desde offsets, modo ciego, almacén de juicios, estado de artefactos); `tests/test_app.py` (T15, 22 pruebas con rutas temporales); `docs/pruebas_app.md`. No registra juicios sin `config/criterios_relevancia.md`. `anotaciones/` sigue vacía. Gold, Gazetteer y Demo quedan para H5 y H6.

- H3 cerrado (2026-11-08): criterios aprobados (`config/criterios_relevancia.md`, PRD §6.5 sin cambios), 176 de 176 juicios (Q1 a Q4 en la app, Q5 a Q10 por hoja e importador `04c`), `make validar` sin errores y `juicios_relevancia.csv` en la raíz. Hoja colaborativa: `src/mtx/hoja_juicios.py`, `make hoja-juicios`. 186 pruebas rápidas verdes.

- H4 cerrado (2026-11-08): `src/mtx/evaluacion.py`, `scripts/05_evaluar_ir.py` (`make evaluar-ir`), `resultados_ir.csv` oficial (MAP BM25 con filtro 0.5750 vs TF-IDF con filtro 0.3846), vista con ventana complementaria, tablas por consulta, ganador con etiquetas, tres figuras en `reporte/figuras/`, `config/sinonimos_consultas.yaml` y `data/mejor_modelo.json` = `bm25_con_filtro`. 200 pruebas rápidas y 8 lentas verdes.

- H5, reglas cerradas y congeladas (2026-11-08): `src/mtx/reglas.py`, `scripts/06_reglas.py` (`make reglas`), `tests/test_reglas.py` (108 pruebas y 2 `xfail` documentados), `config/gazetteer_extendido.csv` (109 filas: kit, PRD, 16 siglas minadas), `config/gazetteer_loc.csv`, `config/criterios_anotacion.md` aprobado por Daniel. Etiqueta `reglas-congeladas` creada. Desviación del PRD §6.7.6 en la regla de marca (el corpus trae «NOMBRE, CARGO»), documentada. Cambios posteriores a reglas o gazetteers son exploratorios y conservan el F1 congelado (D15).

- Relevo (2026-11-11): el profesor inició el repo hasta H5 y pidió continuarlo individualmente; el alumno ahora es Arturo Jaramillo Salmerón, en Windows sin `make` (correr `uv run python scripts/NN_*.py`). Datos regenerados con hashes idénticos; `.gitattributes` con `eol=lf`.
- H5, NER (2026-11-11): `ner_modelo.py`, `scripts/07_ner.py`, `config/ner.yaml`, 19 pruebas sin red. Principal verificado (P06, `salida/07_verificacion_ner_bert_mrm8488.md`) y corrido sobre los 99 pasajes del top-10 (`salida/entidades_bert_mrm8488.csv`, caché en `data/cache_ner/`). 327 pruebas rápidas verdes, ruff limpio.
- H5, muestra gold (2026-11-11): `muestreo.py`, `gold.py`, `08b_muestra_gold.py`, pestaña Gold, `config/protocolo.txt`; 20 pasajes sorteados, una sustitución objetiva. 343 pruebas rápidas verdes.
- H7, fusión y normalización (2026-11-11): `fusion.py`, `normalizacion.py`, `08_extraer.py`; `entidades.csv` (911 filas) y derivados en `salida/`. 378 pruebas rápidas verdes.

## Pendiente

1. ~~NER principal~~: aprobado y fijado en `data/modelo_ner.json` (2026-11-11, criterio técnico).
2. ~~Muestra y pestaña Gold~~ hechas (2026-11-11). **Siguiente: Arturo anota el gold (H6)** en la pestaña Gold (`python -m uv run streamlit run src/mtx/app/app.py`), 20 pasajes, unas 2 a 3.5 h; al terminar, «Cerrar gold». Mientras tanto se puede construir la fusión (H7) sin mirar la muestra. Modo ciego: Arturo no abre `salida/entidades_*.csv`, `salida/07_*` ni `data/cache_ner/` hasta `cierre_gold.json`.
3. H7 resto: `09_evaluar_ie.py` (necesita el gold cerrado), análisis de errores y evaluación de 20 IDs. Luego H8 (tablas) y H9 (reporte, láminas, README). P0 primero; recortes según PRD §12.4.
3b. Arturo decide qué hacer con el cambio accidental en `anotaciones/juicios_relevancia.csv` (Q1 578_0 de 1 a vacío); ver `docs/decisiones.md`.
4. Pendientes heredados: revisar `salida/02_vocabulario_top.csv` para la discusión de la stoplist; declarar el tiempo real de anotación de juicios.
5. Subir el repo al GitHub de Arturo cuando él cree el repo vacío y dé el visto bueno.

## Decisiones

Ver `docs/decisiones.md`. Las no obvias: el corpus real tiene otro formato de marcas que el PRD (parser propio); acotaciones por lista y no por mayúsculas (se conservan siglas como `(IMSS)`); candidatas de fecha fuera de rango se descartan; el 65 % de las intervenciones de reporteros queda bajo 40 palabras y el reporte debe discutirlo (costo de D02); plotly en lugar de matplotlib por indicación del profesor.

## Bloqueos

- (Resuelto 2026-11-11) NER principal aprobado y fijado.
- H6 (gold) es trabajo humano de Arturo y bloqueará H7 en adelante.
- Plazo registrado por el repo: entrega y presentación el 11 de noviembre de 2026, 20:00 (CDMX); confirmar con Arturo su plazo real.
- Kaleido necesita el Chrome que instala `plotly_get_chrome` (`make setup` lo hace); los Chromium de snap fallan.
