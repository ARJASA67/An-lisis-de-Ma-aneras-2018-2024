# Contratos verificados del kit del profesor

Verificado el 2026-11-04 contra los archivos reales de `kit/` (copiados sin cambios) con pandas 3.x.
Las pruebas que respaldan cada afirmación están en `tests/test_contratos_kit.py` (`make contratos`),
sobre fixtures sintéticos; nunca usan juicios ni gold reales. `kit/` no se edita: toda adaptación
vive en `src/mtx/adaptadores_kit.py`.

## Hashes SHA-256 de los originales

```
c959bcf5036a6449c81ef6e5b15a9c7b1ba68c22bbbec0a1475834c5f4573055  kit/corpus.py
ab4faa51a71b3ab463deeaa25d6d84568c61497ecc4dece9c1e152129f87fe3e  kit/consultas.csv
11e0fa1b32e6b1fb8baf304a0efb4815806a6b3dd944c49891978e8528b6b243  kit/gazetteer_dependencias.csv
b70c33ca2cd1436a7d26186786e8ca6685e7d4e3bab8820d054bf6bea891a90f  kit/evaluar.py
f3a7d7d2fe3c397d87f6aa15850560f652dd3aeefb8188334304b92b2081ae4f  kit/README.md
```

`kit/README.md` es un quinto archivo que el PRD no lista; se conserva y se registra su hash.
`make contratos` falla si cualquiera de los cuatro archivos del kit cambia.

## kit/corpus.py

Firmas reales (coinciden con PRD §3.1):

| Función | Firma | Comportamiento verificado |
| --- | --- | --- |
| `cargar_corpus` | `(forzar: bool = False) -> DataFrame` | Descarga `carevies/discursos_AMLO` (split `train`) con `datasets`, renombra `título`→`titulo`, convierte `fecha` con `errors="coerce"` (NaT si no se puede), elimina filas con `texto` nulo y **después** asigna `doc_id = 0..N-1`. Guarda `kit/data/discursos.parquet`; con caché presente no vuelve a descargar salvo `forzar=True`. Conserva columnas extra del dataset (p. ej. `loop`). Las columnas reales de la descarga se verifican en H1. |
| `limpiar_basico` | `(texto: str) -> str` | `\r`→`\n`; espacios y tabuladores consecutivos → un espacio; 2 o más `\n` seguidos → exactamente 2; `strip()`. **Conserva los saltos de línea**, así que `RE_INTERLOCUTOR` (`re.MULTILINE`) sigue encontrando las marcas. No quita marcas. Una línea que solo contiene un espacio no cuenta como salto doble (`"\n \n"` se conserva). |
| `partir_por_interlocutor` | `(texto: str) -> list[tuple[str, str]]` | Sin marcas: `[("", texto.strip())]`. Texto previo a la primera marca: `("", prefacio)`. Marca sin texto: se descarta. Texto vacío: `[("", "")]`. |
| `ventanas` | `(tokens, tam, paso) -> list[str]` | Une cada ventana con un espacio. Con `n <= tam` tokens devuelve una sola ventana (con `n = 0`, una cadena vacía). Con `n = 201`: ventanas de 200 y 51; con `n = 250`: 200 y 100; con `n = 350`: 200 y 200. La última ventana puede ser corta y traslapa con la anterior. |
| `segmentar_pasajes` | `(df, tam=200, paso=150, min_tokens=40) -> DataFrame` | Columnas `passage_id, doc_id, fecha, titulo, posicion, interlocutor, texto`; `passage_id = f"{doc_id}_{posicion}"` con `posicion` consecutiva por discurso; descarta trozos con menos de `min_tokens`; conserva `fecha` NaT. **El `texto` del pasaje no incluye la marca de interlocutor** (queda en `interlocutor`) y se reconstruye con `" ".join(tokens)`, así que pierde los saltos de línea originales. Por eso el PRD §6.1 la sustituye por una función propia que reinyecta la marca y fija `inicio_cuerpo`. |

Constantes: `DATA_DIR = kit/data`, `CACHE = kit/data/discursos.parquet`.
`RE_INTERLOCUTOR = ^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ ,.\-\(\)]{2,80}):\s*` con `re.MULTILINE`.

Tipos con pandas 3: `fecha` es `datetime64[us]`; las columnas de texto son `StringDtype`, no `object`.

## kit/consultas.csv

Cabecera `query_id,consulta,desde,hasta,pregunta_extraccion`, 8 filas (Q1 a Q8). El contenido
coincide literalmente con la tabla del PRD §5.1 (texto, `desde`, `hasta` y pregunta). Q9 y Q10 no
se agregan aquí: van en `data/consultas.csv` (PRD §3.2).

## kit/gazetteer_dependencias.csv

Cabecera `nombre,siglas,tipo`; **76 entradas** (coincide con el PRD 1.0). Valores distintos de `tipo`
(10): `organismo` 25, `dependencia` 21, `partido` 7, `organización empresarial` 5,
`organismo internacional` 5, `organismo autónomo` 4, `obra` 4, `empresa productiva del Estado` 2,
`empresa` 2, `poder judicial` 1. Existe `obra` (→ LOC); el resto → ORG.

## kit/evaluar.py

Se ejecuta como `python kit/evaluar.py ir|ie <referencia.csv> <prediccion.csv>`. **Escribe
`resultados_ir.csv` o `resultados_ie.csv` en el directorio actual**; no hay argumento de salida.
`adaptadores_kit.ejecutar_evaluador()` lo lanza con `cwd` en el destino. Imprime la tabla por
salida estándar.

### Modo IR

- Lee de `ranking.csv` solo `query_id, modelo, rango, passage_id`; las demás columnas se ignoran
  (verificado con las 9 columnas del PRD §3.5). Agrupa por `(query_id, modelo)` y ordena por `rango`.
- Juicios indexados por `(query_id, passage_id)`; `doc_id` no interviene. Pasaje no juzgado = no relevante.
- **Denominador de AP: total de filas con `relevante == 1` de esa consulta en los juicios** (no los
  recuperados). Fixture: 4 relevantes, lista con aciertos en rangos 1 y 3 → AP = (1/1 + 2/3)/4 = 0.4167.
  Consecuencia: **juicios duplicados para un mismo pasaje inflan el denominador**; `validar_juicios()`
  debe exigir clave única.
- Lista con menos de k resultados: no falla y no rellena; P@5 y P@10 dividen siempre entre k (3 filas con
  2 aciertos → P@5 = 0.4, P@10 = 0.2).
- Consulta sin relevantes en los juicios: AP = 0.0 (no NaN) y **entra en el promedio**, que baja el MAP.
- Consulta presente en el ranking pero ausente de los juicios: se evalúa en silencio con ceros. La
  validación del proyecto debe exigir cobertura completa del pool para Q1 a Q10.
- Columnas reales de salida, en orden: `query_id, modelo, P@5, P@10, AP, relevantes_recuperados,
  relevantes_en_pool, no_juzgados`. Una fila por consulta y modelo, más una fila por modelo con
  `query_id = "PROMEDIO (MAP = AP)"` que promedia `P@5, P@10, AP` redondeados a 4 decimales y deja
  vacías las tres columnas de conteo. Los conteos salen como flotantes (`2.0`).
- Ranking vacío (solo cabecera): termina con `KeyError: 'modelo'`. Nunca debe llegarle un ranking vacío.

### Modo IE

- Solo evalúa pasajes presentes en el gold; coincidencia exacta de `(passage_id, tipo, inicio, fin)`
  (`texto` y `query_id` no intervienen). Una entidad desplazada un carácter cuenta como falso positivo y
  falso negativo.
- Métodos: `regla` usa filas `regla` + `ambos`; `modelo` usa `modelo` + `ambos`; `combinado` usa
  **todas las filas sin filtrar por método**. Un `metodo` desconocido no revienta: se descarta de
  `regla` y `modelo`, pero **sí entra en `combinado`** (el PRD decía que se descartaba en silencio).
- Deduplicación: compara conjuntos de `(passage_id, tipo, inicio, fin)`, así que la misma entidad bajo
  Q1 y Q3 cuenta una sola vez (P04 resuelto).
- **Un pasaje gold sin entidades no tiene filas en el gold, luego no se evalúa** y sus predicciones se
  descartan: no penaliza falsos positivos (P04 resuelto; impacta PRD §6.11). La métrica oficial no mide
  precisión en pasajes sin entidades; la evaluación complementaria sobre los 20 IDs debe cubrirlo.
- Tipos: los de gold y predicciones, ordenados, más `TODOS`. Un tipo fuera de {PER, ORG, LOC, FECHA,
  MONTO} produce su propia fila y **cuenta en `TODOS`**: el extractor solo debe emitir los cinco tipos.
- Columnas de salida: `metodo, tipo, precision, recall, f1, tp, predichas, gold`; métodos en el orden
  `regla, modelo, combinado`; valores redondeados a 4 decimales.
- Vacíos: gold vacío o ambos vacíos → solo las tres filas `TODOS` con ceros; predicciones vacías → filas
  con ceros para cada tipo del gold. No revienta.

## Diferencias respecto al PRD

| El PRD dice | El kit hace | Efecto |
| --- | --- | --- |
| `metodo` desconocido se descarta en silencio | Se descarta de `regla` y `modelo`, pero cuenta en `combinado` | El extractor solo emite `regla`, `modelo`, `ambos`; `make validar` lo comprueba |
| Pasaje gold sin entidades: "no se evaluaría" (por verificar) | Confirmado: no se evalúa y sus falsos positivos no se penalizan | Limitación a declarar en el reporte; complementaria sobre 20 IDs |
| Dedup entre consultas (por verificar) | Cuenta una vez | Sin efecto sobre el diseño |
| `resultados_*.csv` en una ubicación conocida | Se escriben en el directorio actual | `ejecutar_evaluador` fija `cwd` |
| Salida IR con `relevantes_recuperados`, `relevantes_en_pool`, `no_juzgados` | Confirmado; la fila de promedio deja vacíos los conteos | Sin efecto |
| `cargar_corpus` devuelve `doc_id, url, titulo, fecha, texto` | Devuelve además columnas extra del dataset (p. ej. `loop`) | Verificar columnas reales en H1 |
