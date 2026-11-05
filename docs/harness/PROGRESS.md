# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

- Arnés (`/harnesser`): CLAUDE.md, AGENTS.md, 17 skills, `docs/harness/`.
- H0 cerrado (2026-11-04): entorno `uv` (Python 3.11, torch CPU, plotly y kaleido), `Makefile`, kit copiado a `kit/` con hashes, `src/mtx/adaptadores_kit.py`, 42 pruebas de contrato, `docs/contratos_kit.md`, `docs/decisiones.md`. Alumno: Daniel Gonzalez. Plazo: entrega y presentación el 11 de noviembre de 2026, presentación a las 20:00 (CDMX). Repo de entrega: este GitLab.
- H1 (2026-11-04): `src/mtx/corpus.py` (limpieza, canonización de marcas, fechas, duplicados, segmentación), `config/limpieza.yaml`, `scripts/01_corpus_y_pasajes.py`, `make corpus` verde: 127,739 pasajes, 5 discursos excluidos, 10 fechas reparadas. Descubrimiento de Q9 y Q10 (`make explorar`, `salida/00_candidatos_q9q10.md`). `data/consultas.csv` con Q9 y Q10 en borrador (`make consultas`). 79 pruebas rápidas verdes.

## Pendiente

1. **Daniel aprueba o corrige Q9 y Q10** (`config/consultas_q9q10.yaml`, estado `borrador_pendiente_de_validar`): Banco del Bienestar y Tren Interoceánico, con ventanas y preguntas tomadas del PRD. Registrar la aprobación en `docs/decisiones.md`. Sin eso no se generan rankings.
2. H2: `preproceso.py`, `indice.py`, `ranking.py`, scripts 02 y 03, pool (skill `indice-ranking`). Lo que no depende del texto de Q9 y Q10 (tokenizador, índice, TF-IDF, BM25, filtro, pruebas) puede avanzar ya.
3. H3 (Daniel): `config/criterios_relevancia.md` `[VALIDAR]` y juicios en la app. Luego H4 a H9 (PRD §12.2).
4. Daniel: verificar que el profesor tenga acceso a este repo de GitLab (el enunciado habla de GitHub).

## Decisiones

Ver `docs/decisiones.md`. Las no obvias: el corpus real tiene otro formato de marcas que el PRD (parser propio); acotaciones por lista y no por mayúsculas (se conservan siglas como `(IMSS)`); candidatas de fecha fuera de rango se descartan; el 65 % de las intervenciones de reporteros queda bajo 40 palabras y el reporte debe discutirlo (costo de D02); plotly en lugar de matplotlib por indicación del profesor.

## Bloqueos

- Aprobación de Q9 y Q10 (punto 1 de Pendiente).
- NLTK no descarga stopwords aquí (validación de rutas); `preproceso.py` debe usar `config/stopwords_es.txt`, que hay que crear versionado en H2.
- Kaleido necesita el Chrome que instala `plotly_get_chrome` (`make setup` lo hace); los Chromium de snap fallan.
