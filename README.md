# Sistema de recuperación y extracción de información sobre discursos presidenciales

Examen 1 de Minería de Textos (Licenciatura en Ciencia de Datos). Sistema en
Python que, sobre el corpus `carevies/discursos_AMLO` (versiones estenográficas
de conferencias y discursos de 2018 a 2024), recupera los 10 pasajes más
relevantes por consulta con TF-IDF y BM25 (con y sin filtro de fecha) y extrae
entidades PER, ORG, LOC, FECHA y MONTO combinando reglas con gazetteer y un NER
preentrenado para español.

## Estado

El proyecto está en el hito H0 (preparación): todavía no hay código ni kit del
profesor en el repo. Este README se reemplaza en el hito H9 por el README de
10 secciones que exige el enunciado (instalación desde cero, reproducción de
resultados, flujo completo, uso de IA).

## Documentos de referencia

| Archivo | Qué es |
| --- | --- |
| `PRD_unificado_examen1_mineria_textos.md` | Especificación completa (v3.0, 4 de noviembre de 2026). Fuente de verdad del proyecto |
| `CLAUDE.md` / `AGENTS.md` | Orquestador para asistentes de programación: índice de skills, convenciones y qué no tocar |
| `docs/harness/ARCHITECTURE.md` | Mapa de componentes, flujos de datos, congelaciones e invalidación |
| `docs/harness/PROGRESS.md` | Estado del trabajo entre sesiones |
| `.claude/skills/` | Skills por hito (H0 a H9); `.agents/skills/` las expone a otros agentes |

## Entregables previstos

Seis CSV en la raíz (`ranking.csv`, `juicios_relevancia.csv`, `resultados_ir.csv`,
`entidades.csv`, `gold_entidades.csv`, `resultados_ie.csv`), reporte PDF de 4 a
6 páginas, presentación de 8 minutos con demo en vivo y `make entrega`
reproducible desde un clon limpio.
