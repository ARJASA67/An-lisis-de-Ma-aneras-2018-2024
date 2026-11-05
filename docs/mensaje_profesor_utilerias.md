# Mensaje al profesor sobre utilerías (PRD §1.3 punto 7, P07)

Para que lo envíe el alumno. Registrar fecha de envío y respuesta en `docs/decisiones.md`.

---

Profesor, buen día. Para el Examen 1 uso, además de las bibliotecas que menciona el enunciado
(`pandas`, `numpy`, `scikit-learn`, `nltk`, `spacy`, `regex`, `rank_bm25`, `datasets`,
`transformers`), las siguientes utilerías que no construyen el índice ni el ranking. ¿Hay algún
inconveniente con alguna?

- `torch` (CPU): lo requiere `transformers` para el NER.
- `pyarrow`: guardar los pasajes en formato Parquet.
- `streamlit`: app local para capturar mis juicios de relevancia y mi gold; no sugiere ni precarga valores.
- `plotly` y `kaleido`: figuras del reporte (sustituyen a matplotlib por indicación del profesor).
- `pypdf`: contar las páginas del PDF.
- `python-pptx`: generar las láminas.
- `pytest`: pruebas del código.
- `pyyaml`: archivos de configuración.
- `rich`: formato de la demo en terminal.
- `uv`: entorno reproducible y `uv.lock`; entrego también `requirements.txt`.

El índice invertido y BM25 los escribo a mano; TF-IDF usa `scikit-learn`.

Gracias.
