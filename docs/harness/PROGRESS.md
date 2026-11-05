# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- 2026-11-04: arnés de desarrollo generado con `/harnesser` (CLAUDE.md, AGENTS.md, 17 skills en .claude/skills/ con symlinks en .agents/skills/, docs/harness/).
- 2026-11-04: `README.md` mínimo (descripción, estado H0, documentos de referencia) en lugar de la plantilla de GitLab; el README de 10 secciones sigue siendo entregable de H9.

- 2026-11-04: H0 parcial. Entorno (`pyproject.toml`, `uv.lock`, `.python-version` 3.11, `Makefile`, `.gitignore`, carpetas), `make setup` verde, `docs/decisiones.md` con la Fase 0 (datos de entorno), `docs/mensaje_profesor_utilerias.md`.

- 2026-11-04: H0 cerrado. Kit copiado con hashes, `src/mtx/adaptadores_kit.py`, 42 pruebas de contrato, `docs/contratos_kit.md`. Fase 0: alumno Daniel Gonzalez, plazo 11 de noviembre, plotly en lugar de matplotlib.
- 2026-11-04: H1 parcial. `src/mtx/corpus.py`, `config/limpieza.yaml`, `scripts/01_corpus_y_pasajes.py`, `tests/test_corpus.py` (35 pruebas) y `make corpus` verde: 127,739 pasajes en `data/pasajes.parquet`. Falta `00_descubrir_consultas.py`, Q9 y Q10 `[VALIDAR]` y `data/consultas.csv`.

## Pendiente

- (H0 hecho salvo:) el alumno entrega la ruta del kit, nombre, repo de entrega y plazo vigente; copiar el kit a `kit/` con hashes SHA-256 (quitar `kit/.gitkeep`), `tests/test_contratos_kit.py` (`make contratos`), `docs/contratos_kit.md`; el alumno envía el mensaje a profesor.
- Siguiente: `scripts/00_descubrir_consultas.py` y `config/candidatos_q9q10.yaml`; mostrar candidatos a Daniel y esperar su elección de Q9 y Q10. Luego H2. Orden completo: H1 → H2 · Recuperación → H3 · Juicios (humano) → H4 · Evaluación IR → H5 · Preparación IE → H6 · Gold (humano) → H7 · IE final → H8 · Respuestas → H9 · Entrega (PRD §12.2).

## Decisiones

- El remote actual es GitLab (`text-mining-ir-er`) aunque el PRD habla de GitHub y del nombre `examen1-mineria-textos`; se registra en `docs/decisiones.md` durante la Fase 0.
- `README.md` actual es la plantilla de GitLab; se reemplaza en H9 por el README de 10 secciones (PRD §11.2).

## Bloqueos

- El kit del profesor (`corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`) no está en el equipo; solo el alumno puede dar la ruta. Bloquea contratos, `corpus.py` de H1 y la evaluación de H4/H7.
- El plazo del enunciado (entrega 28 de octubre, presentación 4 de noviembre) coincide o ya pasó respecto a hoy (2026-11-04); el alumno debe confirmar el plazo vigente.
- NLTK no puede descargar stopwords en esta máquina (validación de rutas); se usará `config/stopwords_es.txt`.
