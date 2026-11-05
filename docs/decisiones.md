# Decisiones del proyecto

## Fase 0 (2026-11-04)

- SO: Linux x86_64 (Ubuntu, kernel 6.8)  Python: 3.12.3 del sistema; el proyecto usa 3.11.18 vía `uv` (`.python-version`)  uv: 0.11.14  pandoc: 3.1.3  TeX: XeTeX (TeX Live 2023), disponible para `make reporte`.
- Acceso a Hugging Face: la API del dataset `carevies/discursos_AMLO` responde 200 (2026-11-04). La descarga completa del corpus se prueba en H1.
- Repo: remoto en GitLab (`git@gitlab.com:oscar.acosta.mac/text-mining-ir-er.git`); el PRD habla de GitHub y del nombre `examen1-mineria-textos`. Se conserva GitLab; el enunciado exige entrega en GitHub, así que **pendiente**: confirmar con el alumno dónde se entrega.
- Alumno: pendiente (nombre completo para portada y láminas).
- Plazo vigente: pendiente. El enunciado fija entrega el 28 de octubre a las 20:00 y presentación el 4 de noviembre; hoy es 2026-11-04. Se registra aquí el plazo real que confirme el alumno, sin suponer prórrogas.
- Q9: pendiente (se elige tras explorar el corpus, PRD §5.2, `[VALIDAR]`).
- Q10: pendiente (ídem).
- Horas disponibles: pendiente.
- Utilerías: mensaje redactado en `docs/mensaje_profesor_utilerias.md`; enviado: pendiente; respuesta: pendiente. Mientras tanto se trabaja con ellas.
- Estado previo: ninguno. Repo con arnés y PRD; sin commit entregado ni artefactos en `salida/` o `anotaciones/`.
- Kit del profesor: pendiente. Los cuatro archivos (`corpus.py`, `consultas.csv`, `gazetteer_dependencias.csv`, `evaluar.py`) no están en el equipo; hay que indicar su ruta.

## Contratos del kit (pendiente): ver docs/contratos_kit.md; diferencias con el PRD: pendiente hasta tener el kit.

## Decisiones posteriores

- (2026-11-04) Entorno: `pyproject.toml` con `requires-python >=3.11,<3.13`, build `hatchling` con layout `src/mtx`, torch CPU desde el índice de PyTorch en Linux y Windows. `uv.lock` versionado.
- (2026-11-04) `make setup` no falla si NLTK no descarga las stopwords (NLTK bloquea su carpeta por validación de rutas); se usará `config/stopwords_es.txt` como respaldo versionado, según PRD §9.
