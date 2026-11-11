# Guía de defensa

Para estudiar antes de la presentación. Por módulo de `src/mtx/`: qué hace en cinco líneas, un
ejemplo real y dónde ver más. Arturo puede corregir cualquier parte. Las cifras vienen de `salida/`.

## Fórmulas clave

- **idf de BM25**: $\mathrm{idf}(t) = \ln\left(1 + \frac{N - df_t + 0.5}{df_t + 0.5}\right)$. Con
  N = 127,739 y df(huachicol) = 714 da 5.19; con df(tren) = 5,261 da 3.19.
- **BM25** ($k_1 = 1.5$, $b = 0.75$): $\sum_{t \in q} \mathrm{idf}(t) \cdot \frac{tf\,(k_1+1)}{tf + k_1(1 - b + b\,|p|/\mathrm{avgdl})}$,
  sobre términos únicos de la consulta; avgdl = 72.2. $k_1$ satura el tf; $b$ penaliza pasajes largos.
- **TF-IDF sublineal**: $w = (1 + \ln tf)(\ln\frac{1+N}{1+df} + 1)$, vector normalizado L2.
- **Coseno**: producto punto de los vectores L2 de la consulta y del pasaje.
- **AP**: $\sum_{r=1}^{10} P@r \cdot rel(r) / R$, con R los relevantes del pool. MAP = promedio de AP.
  Techo cuando R > 10: 10/R (Q9: 10/21 = 0.476).
- **P, R, F1**: P = TP/(TP+FP), R = TP/(TP+FN), F1 = 2PR/(P+R); TP exige mismo pasaje, tipo, inicio y fin.

## Módulos

**adaptadores_kit.py**. Único punto de contacto con `kit/`, que nunca se edita. Importa
`kit/corpus.py` por ruta y corre `kit/evaluar.py ir|ie` como subproceso con `cwd` en la carpeta de
destino, porque el kit escribe su CSV en el directorio actual. Verifica los SHA-256 de los cuatro
archivos del kit contra `docs/contratos_kit.md`.
Ejemplo: `ejecutar_evaluador("ie", gold, entidades, salida/)` deja `salida/resultados_ie.csv`.

**config.py / consultas.py**. Rutas, semilla 42 y lectura de YAML. `data/consultas.csv` = las 8
consultas del kit tal cual más Q9 y Q10 aprobadas; todos los scripts leen esa copia.
Ejemplo: Q9 = «operación y apertura de sucursales del Banco del Bienestar», 2019-01-01 a 2023-12-31.

**corpus.py**. Carga el snapshot, limpia y segmenta. Canoniza las marcas de interlocutor (el patrón
del kit no reconoce ninguna en este corpus), quita acotaciones de una lista cerrada, repara fechas
con el título, excluye duplicados y parte cada intervención en ventanas de 200 palabras con paso
de 150 y mínimo de 40. Cada pasaje guarda `inicio_cuerpo`, donde termina la marca.
Ejemplo: «PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR: …» con `inicio_cuerpo` justo después de «: ».

**descubrimiento.py**. Cuenta señal en el corpus para proponer Q9 y Q10; no decide, el alumno elige.

**preproceso.py**. NFC y minúsculas, tokens alfanuméricos con guion interno, stoplist de 336
palabras, descarte de tokens de dos caracteres o menos salvo números y stemming Snowball. Los
pasajes se tokenizan sin la marca.
Ejemplo: «refinería refinerías covid-19 presidente gracias» → `refin, refin, covid-19`.

**indice.py**. Índice invertido a mano: `postings[término][pasaje] = tf`, más df, N, longitud de
cada pasaje y avgdl. Se construye una vez sobre todo el corpus; el filtro de fecha no cambia N ni idf.
Ejemplo: `huachicol` tiene df = 714; su pasaje con mayor tf es 2191_4 (tf 7).

**ranking.py**. BM25 propio y TF-IDF de scikit-learn sobre el mismo índice. El filtro de fecha
primero elige los pasajes dentro de la ventana y después ordena; desempate por doc_id y posición.
`Buscador` sirve también para consultas libres (lo usa la demo).
Ejemplo: Q10 con BM25 con filtro tiene AP 0.866; con TF-IDF con filtro, 0.284.

**pool.py**. Pool = unión sin duplicados de los top-10 de las cuatro variantes (176 pares), en orden
barajado con semilla 42. `validar_juicios` es de solo lectura y exporta `juicios_relevancia.csv`.

**hoja_juicios.py / app/**. Herramientas de anotación. La hoja reparte juicios entre compañeros sin
mostrar modelo ni rango. La app (Streamlit) tiene Estado, Juicios (solo lectura desde H4) y Gold en
modo ciego, con escritura atómica, revisión y respaldo. Nunca sugiere ni precarga valores.

**evaluacion.py**. IR: corre el kit, arma la vista con ventana, etiquetas por consulta y elige el
mejor modelo por MAP entre las variantes con filtro (BM25 con filtro, 0.575). IE: corre el kit,
reproduce su semántica con FP, FN y estados (`no_aplicable`, `sin_cobertura`), evalúa los 20 IDs
del sorteo y clasifica errores en frontera, tipo, sigla, en marca, omisión y espuria.
Ejemplo: gold «aeropuerto Felipe Ángeles», predicción «Felipe Ángeles» → `frontera` (1606_0).

**reglas.py**. Expresiones regulares de FECHA y MONTO (solo dinero), cantidades auxiliares aparte,
gazetteers ORG y LOC y la regla de marca para PER, que separa nombre y cargo. Trabaja sobre el texto
original con offsets de carácter. Congelado con la etiqueta `reglas-congeladas` antes del gold.
Ejemplo: «14 de febrero de 2021» → FECHA; «dos mil 550 pesos» → MONTO.

**ner_modelo.py**. NER con mrm8488/bert-spanish-cased-finetuned-ner (revisión fija). Parte el
pasaje en ventanas de 494 subtokens con solape de 64, proyecta los spans al texto, descarta MISC y
guarda las predicciones crudas en una caché versionada (la demo y los scripts no necesitan red).
Ejemplo: en la marca en mayúsculas produce fragmentos como «MAN» o «MANUEL LÓPEZ».

**muestreo.py / gold.py**. Sortea 20 pasajes gold con semilla 42, dos por consulta (rango 1 a 5 y
6 a 10), con emparejamiento para no repetir pasajes. `gold.py` guarda las anotaciones, valida
(offsets, tipos, anidamiento) y cierra el gold con `cierre_gold.json`.

**fusion.py**. Une reglas y modelo por coincidencia exacta de tipo, inicio y fin: igual → `ambos`;
si no, cada uno conserva su fila. Los solapes parciales se registran, no se resuelven.
Ejemplo: INAH en 1298_13 lo dan el gazetteer y el modelo → `ambos`.

**normalizacion.py**. Fechas a ISO con la fecha del discurso como ancla; montos a `Decimal` con
moneda y escala; nombre canónico de ORG y LOC solo si el gazetteer registra la equivalencia.
Ejemplo: «INAH» → Instituto Nacional de Antropología e Historia.

**respuestas.py**. Arma las tablas de respuesta: excluye entidades en la marca y el nombre del
presidente en campos PER, exige un patrón de la relación a ±60 caracteres o en la oración del valor
y sus contiguas, marca como ambiguo lo que dice un reportero y deduplica ventanas solapadas.
Ejemplo: en Q7, «dos mil 550 pesos» queda respaldado porque «bimestr» aparece en su contexto.

**reporte.py**. Genera las tablas del reporte desde `salida/`, rellena los marcadores de
`reporte.md` en una copia y compila con pandoc y XeLaTeX; actualiza la sección 8 del README.

**sistema.py**. Mide la memoria del proceso (pico de 1.3 GB al construir el índice).
