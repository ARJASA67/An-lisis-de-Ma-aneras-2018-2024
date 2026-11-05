# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- 2026-11-04: arnés de desarrollo generado con `/harnesser` (CLAUDE.md, AGENTS.md, 17 skills en .claude/skills/ con symlinks en .agents/skills/, docs/harness/).
- 2026-11-04: `README.md` mínimo (descripción, estado H0, documentos de referencia) en lugar de la plantilla de GitLab; el README de 10 secciones sigue siendo entregable de H9.

## Pendiente

- H0 · Preparación: Fase 0 con el alumno (skill `kit-contratos`), `pyproject.toml`, `Makefile`, copia del kit a `kit/` con hashes, pruebas de contrato, `docs/contratos_kit.md`, `docs/decisiones.md`.
- H1 · Datos y consultas → H2 · Recuperación → H3 · Juicios (humano) → H4 · Evaluación IR → H5 · Preparación IE → H6 · Gold (humano) → H7 · IE final → H8 · Respuestas → H9 · Entrega (PRD §12.2).

## Decisiones

- El remote actual es GitLab (`text-mining-ir-er`) aunque el PRD habla de GitHub y del nombre `examen1-mineria-textos`; se registra en `docs/decisiones.md` durante la Fase 0.
- `README.md` actual es la plantilla de GitLab; se reemplaza en H9 por el README de 10 secciones (PRD §11.2).

## Bloqueos

- Ninguno. El kit del profesor (`corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`) aún no está en el repo; se pide en la Fase 0.
