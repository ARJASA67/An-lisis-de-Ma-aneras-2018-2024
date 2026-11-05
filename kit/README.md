# Kit de inicio · Examen 1 · Minería de textos

Archivos que se entregan junto con el enunciado. Nada de esto resuelve el examen; ahorra el trabajo de plomería para que el tiempo se vaya en el sistema y en el análisis.

| Archivo | Para qué sirve |
| --- | --- |
| `corpus.py` | Descarga el corpus una sola vez (`cargar_corpus()`), lo guarda en `data/discursos.parquet` y ofrece una segmentación base en pasajes (`segmentar_pasajes()`). La segmentación es un punto de partida: cambiarla y justificarlo cuenta en la rúbrica. |
| `consultas.csv` | Las ocho consultas obligatorias con su ventana de fechas y la pregunta que debe contestar la extracción. Agrega tus Q9 y Q10 al final con el mismo formato. |
| `gazetteer_dependencias.csv` | Gazetteer base: dependencias, organismos, empresas del Estado, obras, organizaciones empresariales, partidos y organismos internacionales, con nombre completo y siglas. Extiéndelo con lo que encuentres en el corpus. |
| `evaluar.py` | Calcula P@5, P@10 y MAP (Tarea A) y precisión, recall y F1 por tipo y método (Tarea B). Todos lo usan igual para que las cifras sean comparables. |

## Instalación

```bash
pip install pandas numpy scikit-learn nltk spacy rank_bm25 datasets pyarrow
python -m spacy download es_core_news_md
python -c "import nltk; nltk.download('stopwords')"
python corpus.py          # descarga el corpus y muestra estadísticas básicas
```

## Formatos de los CSV que se entregan

`ranking.csv` (top-10 de cada modelo por consulta, con y sin filtro de fecha en archivos separados o con una columna `variante`):

```csv
query_id,modelo,rango,passage_id,doc_id,fecha,puntaje
Q1,bm25,1,1532_7,1532,2021-06-14,18.42
```

`juicios_relevancia.csv` (un renglón por pasaje del pool, juzgado a mano):

```csv
query_id,doc_id,passage_id,relevante
Q1,1532,1532_7,1
```

`entidades.csv` (salida de la Tarea B sobre los pasajes recuperados):

```csv
query_id,doc_id,passage_id,tipo,texto,inicio,fin,metodo
Q1,1532,1532_7,ORG,Fonatur,88,95,ambos
```

`gold_entidades.csv` (20 pasajes anotados a mano, offsets de caracter sobre el texto del pasaje):

```csv
passage_id,tipo,texto,inicio,fin
1532_7,ORG,Fonatur,88,95
```

Convenciones de anotación: los offsets son de caracter sobre `texto` del pasaje, `fin` exclusivo (como en `texto[inicio:fin]`); las obras con nombre propio (Tren Maya, AIFA, Dos Bocas) se etiquetan LOC; los montos incluyen la unidad ("20 mil millones de pesos", no solo "20"); las fechas se anotan completas ("15 de diciembre de 2023").

## Uso del evaluador

```bash
python evaluar.py ir juicios_relevancia.csv ranking.csv      # escribe resultados_ir.csv
python evaluar.py ie gold_entidades.csv entidades.csv        # escribe resultados_ie.csv
```
