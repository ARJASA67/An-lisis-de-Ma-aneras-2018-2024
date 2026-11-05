# Decisiones del proyecto

## Fase 0 (2026-11-04)

- SO: Linux x86_64 (Ubuntu, kernel 6.8)  Python: 3.12.3 del sistema; el proyecto usa 3.11.18 vía `uv` (`.python-version`)  uv: 0.11.14  pandoc: 3.1.3  TeX: XeTeX (TeX Live 2023), disponible para `make reporte`.
- Acceso a Hugging Face: la API del dataset `carevies/discursos_AMLO` responde 200 (2026-11-04). La descarga completa del corpus se prueba en H1.
- Repo: remoto en GitLab (`git@gitlab.com:oscar.acosta.mac/text-mining-ir-er.git`); el PRD habla de GitHub y del nombre `examen1-mineria-textos`. Se conserva GitLab; el enunciado exige entrega en GitHub, así que **pendiente**: confirmar con el alumno dónde se entrega.
- Alumno: Daniel Gonzalez (portada y láminas). Falta confirmar si requiere apellido completo adicional.
- Plazo vigente: **entrega el 11 de noviembre de 2026** (nuevo plazo informado por el alumno el 2026-11-04; hora y fecha de presentación no indicadas, pendientes). El enunciado original fijaba entrega el 28 de octubre a las 20:00 y presentación el 4 de noviembre.
- Q9: pendiente (se elige tras explorar el corpus, PRD §5.2, `[VALIDAR]`).
- Q10: pendiente (ídem).
- Horas disponibles: pendiente.
- Utilerías: mensaje en `docs/mensaje_profesor_utilerias.md`, enviado por el alumno (fecha exacta no registrada, antes del 2026-11-04). Respuesta del profesor (relatada por el alumno): todo está bien excepto `matplotlib`; usar `plotly` o `cufflinks`.
- Estado previo: ninguno. Repo con arnés y PRD; sin commit entregado ni artefactos en `salida/` o `anotaciones/`.
- Kit del profesor: copiado en `kit/` (cuatro archivos más `README.md`), sin modificar; hashes en `docs/contratos_kit.md`.

## Contratos del kit (2026-11-04): ver docs/contratos_kit.md; diferencias con el PRD: `metodo` desconocido cuenta en `combinado`; el pasaje gold sin entidades no se evalúa y no penaliza falsos positivos; `evaluar.py` escribe en el directorio actual; `cargar_corpus` conserva columnas extra; juicios duplicados inflan el denominador de AP; ranking vacío revienta el evaluador. Q1 a Q8 coinciden literalmente con el PRD §5.1; el gazetteer tiene 76 entradas y 10 tipos.

## Decisiones posteriores

- (2026-11-04) Entorno: `pyproject.toml` con `requires-python >=3.11,<3.13`, build `hatchling` con layout `src/mtx`, torch CPU desde el índice de PyTorch en Linux y Windows. `uv.lock` versionado.
- (2026-11-04) `make setup` no falla si NLTK no descarga las stopwords (NLTK bloquea su carpeta por validación de rutas); se usará `config/stopwords_es.txt` como respaldo versionado, según PRD §9.
- (2026-11-04) Gráficas con `plotly` exportadas a PNG con `kaleido`, en lugar de `matplotlib`, por indicación del profesor. `cufflinks` no se usa: es un envoltorio sin mantenimiento sobre plotly. Kaleido necesita Chrome; `make setup` ejecuta `plotly_get_chrome` (los Chromium del sistema, de snap, fallan). PRD §2.2, §6.6 y §11.1 y tres skills se actualizaron para reflejarlo.
- (2026-11-04) `evaluar.py` se invoca siempre desde `adaptadores_kit.ejecutar_evaluador()` con `cwd` en el directorio de destino, porque el kit escribe `resultados_*.csv` en el directorio actual.
- (2026-11-04) Limitación a declarar en el reporte: la métrica IE oficial no penaliza falsos positivos en pasajes gold sin entidades (comportamiento del kit); la evaluación complementaria sobre los 20 IDs lo cubre.
