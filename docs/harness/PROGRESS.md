# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- 2026-11-04: arnés de desarrollo generado con `/harnesser` (CLAUDE.md, AGENTS.md, 17 skills en .claude/skills/ con symlinks en .agents/skills/, docs/harness/).
- 2026-11-04: `README.md` mínimo (descripción, estado H0, documentos de referencia) en lugar de la plantilla de GitLab; el README de 10 secciones sigue siendo entregable de H9.

- 2026-11-04: H0 parcial. Entorno (`pyproject.toml`, `uv.lock`, `.python-version` 3.11, `Makefile`, `.gitignore`, carpetas), `make setup` verde, `docs/decisiones.md` con la Fase 0 (datos de entorno), `docs/mensaje_profesor_utilerias.md`.

## Pendiente

- H0 · Preparación (falta): el alumno entrega la ruta del kit, nombre, repo de entrega y plazo vigente; copiar el kit a `kit/` con hashes SHA-256 (quitar `kit/.gitkeep`), `tests/test_contratos_kit.py` (`make contratos`), `docs/contratos_kit.md`; el alumno envía el mensaje a profesor.
- H1 · Datos y consultas → H2 · Recuperación → H3 · Juicios (humano) → H4 · Evaluación IR → H5 · Preparación IE → H6 · Gold (humano) → H7 · IE final → H8 · Respuestas → H9 · Entrega (PRD §12.2).

## Decisiones

- El remote actual es GitLab (`text-mining-ir-er`) aunque el PRD habla de GitHub y del nombre `examen1-mineria-textos`; se registra en `docs/decisiones.md` durante la Fase 0.
- `README.md` actual es la plantilla de GitLab; se reemplaza en H9 por el README de 10 secciones (PRD §11.2).

## Bloqueos

- El kit del profesor (`corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`) no está en el equipo; solo el alumno puede dar la ruta. Bloquea contratos, `corpus.py` de H1 y la evaluación de H4/H7.
- El plazo del enunciado (entrega 28 de octubre, presentación 4 de noviembre) coincide o ya pasó respecto a hoy (2026-11-04); el alumno debe confirmar el plazo vigente.
- NLTK no puede descargar stopwords en esta máquina (validación de rutas); se usará `config/stopwords_es.txt`.
