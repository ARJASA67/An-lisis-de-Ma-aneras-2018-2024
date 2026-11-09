# Sistema de recuperación y extracción de información sobre discursos presidenciales

Examen 1 de Minería de Textos (Licenciatura en Ciencia de Datos). Sistema en
Python que, sobre el corpus `carevies/discursos_AMLO` (versiones estenográficas
de conferencias y discursos de 2018 a 2024), recupera los 10 pasajes más
relevantes por consulta con TF-IDF y BM25 (con y sin filtro de fecha) y extrae
entidades PER, ORG, LOC, FECHA y MONTO combinando reglas con gazetteer y un NER
preentrenado para español.

## Estado

Hitos H0 a H4 hechos y reglas de H5 congeladas (etiqueta `reglas-congeladas`).
Recuperación: TF-IDF y BM25 con y sin filtro de fecha, `ranking.csv`, pool y
176 juicios de relevancia validados, `resultados_ir.csv` oficial (MAP 0.5750 de
BM25 con filtro frente a 0.3846 de TF-IDF con filtro) y `data/mejor_modelo.json`
fijado en `bm25_con_filtro`. Extracción: reglas de FECHA, MONTO, gazetteers
ORG/LOC y regla de marca probadas (`tests/test_reglas.py`); falta el NER con
modelo (siguiente), la muestra y el gold (H6, trabajo humano), la fusión, la
evaluación de IE, las tablas de respuesta, el reporte y las láminas. Este README
se reemplaza en H9 por el de 10 secciones que exige el enunciado (instalación
desde cero, reproducción de resultados, flujo completo, uso de IA).

Uso mínimo hoy (Linux, Python 3.11 y `uv`):

```bash
make setup      # entorno, torch CPU, Chrome para kaleido
make contratos  # pruebas de contrato del kit (kit/ no se modifica)
make corpus     # descarga el corpus, limpia y segmenta: data/pasajes.parquet
make consultas  # data/consultas.csv = kit + Q9 + Q10
make indice     # preprocesa y construye el índice invertido y TF-IDF
make ranking    # ranking.csv con las cuatro variantes
make pool       # pool de relevancia (salida/04_pool.csv)
make app        # app de anotación (Estado y Juicios); make app-cli sin Streamlit
make validar    # valida los juicios y exporta juicios_relevancia.csv
make evaluar-ir # resultados_ir.csv, vista con ventana, figuras y mejor modelo
make reglas     # reglas sobre todo el corpus (unos 3 minutos)
make test       # pruebas rápidas, sin red (make test-lento añade las del corpus real)
```

`make hoja-juicios` genera una hoja de cálculo para repartir juicios entre
compañeros; `scripts/04c_importar_juicios_hoja.py` los importa con revisión.

## Documentos de referencia

| Archivo | Qué es |
| --- | --- |
| `PRD_unificado_examen1_mineria_textos.md` | Especificación completa (v3.0, 4 de noviembre de 2026). Fuente de verdad del proyecto |
| `CLAUDE.md` / `AGENTS.md` | Orquestador para asistentes de programación: índice de skills, convenciones y qué no tocar |
| `docs/harness/ARCHITECTURE.md` | Mapa de componentes, flujos de datos, congelaciones e invalidación |
| `docs/harness/PROGRESS.md` | Estado del trabajo entre sesiones |
| `docs/decisiones.md` | Fase 0 y cada decisión con fecha (formato real del corpus, juicios, reglas, cambios tras congelar) |
| `docs/contratos_kit.md` | Hashes y comportamiento verificado de `kit/` |
| `docs/pruebas_app.md` | Los 10 pasos de la prueba manual de la app de anotación |
| `.claude/skills/` | Skills por hito (H0 a H9); `.agents/skills/` las expone a otros agentes |

## Entregables previstos

Seis CSV en la raíz (`ranking.csv`, `juicios_relevancia.csv`, `resultados_ir.csv`,
`entidades.csv`, `gold_entidades.csv`, `resultados_ie.csv`), reporte PDF de 4 a
6 páginas, presentación de 8 minutos con demo en vivo y `make entrega`
reproducible desde un clon limpio.
