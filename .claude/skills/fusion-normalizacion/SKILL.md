---
name: fusion-normalizacion
description: "Usa esta skill cuando vayas a implementar, modificar o probar la fusión de entidades reglas + modelo (src/mtx/fusion.py, scripts/08_extraer.py), el contrato de entidades.csv y sus derivados, o la normalización prudente de fechas, montos, ORG/LOC y personas (src/mtx/normalizacion.py)."
---
# Fusión reglas + modelo y normalización prudente

## Cuándo usarla

- Vas a tocar `src/mtx/fusion.py`, `src/mtx/normalizacion.py`, `scripts/08_extraer.py`, `tests/test_fusion.py` o `tests/test_normalizacion.py`.
- Vas a generar o validar `entidades.csv`, `salida/entidades_unicas.csv`, `salida/entidades_enriquecidas.csv` o `salida/08_solapes_parciales.csv`.
- Necesitas decidir qué `metodo` lleva una entidad, cómo tratar un solape parcial o cómo convertir "2 mil 500 millones de pesos" en un número.
- No la uses para escribir reglas o gazetteers (`reglas-gazetteer`), ejecutar el NER (`ner-modelo`) ni correr el evaluador (`evaluacion-ie`).

## Prerrequisitos y congelaciones que aplican

Lista de verificación antes de escribir código:

1. Existen las salidas de los pasos previos: entidades por reglas (script 06) y entidades del modelo con `salida/07_uniones_spans.csv` y caché en `data/cache_ner/` (script 07).
2. `docs/contratos_kit.md` (H0) ya registra cómo `kit/evaluar.py ie` trata un pasaje repetido entre consultas, un pasaje gold sin entidades y tipos sin soporte (PRD §3.4, línea "Verificar en H0"). Si no está, detén la fusión y resuelve primero con `kit-contratos`.
3. Si la etiqueta git `reglas-congeladas` ya existe (D15), la fusión y la normalización no pueden tocar reglas ni gazetteers. Cualquier cambio en `fusion.py` posterior al gold conserva el F1 anterior y marca el nuevo como exploratorio (ver `integridad-congelacion`).
4. El kit en `kit/` no se edita nunca; cualquier diferencia se absorbe en `src/mtx/adaptadores_kit.py`.
5. Decisiones congeladas que gobiernan esta skill: D11 (porcentajes y cantidades son auxiliares, no MONTO), D12 (fusión por coincidencia exacta), D16 (8 columnas exactas en `entidades.csv`; lo auxiliar vive en `entidades_enriquecidas.csv`).

## Fusión reglas + modelo (D12)

Procedimiento en `fusion.py`, orquestado por `08_extraer.py`:

1. Extrae **una sola vez por pasaje** (`passage_id`), no por par consulta-pasaje. Después asocia cada entidad a todas las consultas que recuperaron ese pasaje; la clave pública lleva `query_id`.
2. Construye dos conjuntos indexados por `(passage_id, tipo, inicio, fin)`: uno de reglas y otro del modelo.
3. Asigna `metodo` con esta tabla y nada más:

| En reglas | En modelo | `metodo` | Filas resultantes |
|---|---|---|---|
| sí | sí (misma clave exacta) | `ambos` | 1 fila; `fuentes` concatena ambas procedencias |
| sí | no | `regla` | 1 fila |
| no | sí | `modelo` | 1 fila |
| span solapado parcialmente | span solapado parcialmente | el de cada fuente | 2 filas independientes + 1 registro en `salida/08_solapes_parciales.csv` |
| mismo span, tipo distinto | mismo span, tipo distinto | el de cada fuente | 2 filas independientes + 1 registro en `salida/08_solapes_parciales.csv` |

4. `08_solapes_parciales.csv` cuantifica cada discrepancia: `passage_id`, span y tipo de cada fuente, clase de discrepancia (`solape_parcial` o `tipo_distinto`) y longitud del solape. Alimenta el análisis de errores (PRD §6.12); no se usa para elegir ganador.
5. El extractor emite únicamente `regla`, `modelo` o `ambos`. El evaluador descarta en silencio cualquier otro valor (PRD §3.4), así que un `metodo` distinto equivale a perder la fila.
6. Orden determinista de salida: `query_id, passage_id, inicio`. Dos corridas con las mismas entradas producen bytes idénticos.
7. Si H0 mostró que el evaluador **no** deduplica entre consultas y por tanto cuenta doble un pasaje compartido (T08), exporta la vista única por pasaje mediante un adaptador en `adaptadores_kit.py`, documentado en `docs/contratos_kit.md`. El `entidades.csv` completo se conserva intacto; el adaptador solo produce la vista que recibe el evaluador.

Decisiones que ya están tomadas y no se reabren aquí: no hay prioridad entre reglas y modelo en discrepancias (ambas filas sobreviven); no hay umbral de puntaje del modelo para descartar filas en la fusión; no hay ajuste de spans para "hacer coincidir" las dos fuentes.

## Contrato de entidades.csv y archivos derivados

`entidades.csv` (en la raíz y en `salida/`), PRD §3.5:

```csv
query_id,doc_id,passage_id,tipo,texto,inicio,fin,metodo
Q1,1532,1532_7,ORG,Fonatur,88,95,ambos
```

Verificación obligatoria (debe estar en `tests/test_formatos.py` y correrse en `99_validar.py`):

- Exactamente 8 columnas, en ese orden, sin ninguna columna extra (D16).
- Clave única `(query_id, passage_id, tipo, inicio, fin)` sin duplicados.
- `tipo` ∈ {PER, ORG, LOC, FECHA, MONTO}; `metodo` ∈ {regla, modelo, ambos}.
- `inicio` y `fin` son offsets enteros sobre el texto del pasaje; `texto == pasaje[inicio:fin]`.
- UTF-8 sin BOM, separador coma, comillas dobles solo cuando el texto las requiere.
- Ordenado por `query_id, passage_id, inicio`.

Derivados en `salida/`:

| Archivo | Contenido | Clave |
|---|---|---|
| `entidades_unicas.csv` | Una fila por entidad y pasaje, sin repetir asociaciones a consultas | `(passage_id, tipo, inicio, fin)` |
| `entidades_enriquecidas.csv` | Las 8 columnas más los grupos de abajo; campos no aplicables vacíos | misma que `entidades.csv` |
| `08_solapes_parciales.csv` | Discrepancias cuantificadas entre reglas y modelo | ver sección anterior |
| `cantidades_auxiliares.csv` | PORCENTAJE y CANTIDAD (D11); lo produce el script 06, nunca entra a `entidades.csv` | — |

Columnas adicionales de `entidades_enriquecidas.csv` (PRD §6.9), en este orden tras las 8 oficiales:

1. Procedencia: `fuentes`, `en_marca`, `modelo_id`, `modelo_revision`, `puntaje_modelo`, `version_extractor`. `fuentes` puede llevar varias procedencias cuando `metodo = ambos`.
2. Identidad: `canonico`, `texto_normalizado`, `estado_identidad`.
3. Tiempo: `fecha_iso`, `fecha_inicio`, `fecha_fin`, `precision_fecha`, `fecha_relativo`, `fecha_ancla`, `resuelta_desde_ancla`, `estado_fecha`.
4. Dinero: `valor_num`, `valor_min`, `valor_max`, `moneda`, `escala`, `estado_monto`.

Cada archivo derivado se registra en `salida/manifiesto_ejecucion.json` con versión de esquema, productor y hashes de entradas.

## Normalización prudente

`normalizacion.py` produce representaciones auxiliares. Recibe texto, span, contexto del pasaje y fecha ancla (la `fecha` del discurso), no solo la cadena. Nunca escribe en `inicio`, `fin` ni `texto`. Prioridades: P0 para MONTO, FECHA absoluta y ORG/LOC; P2 para fechas relativas y vínculo de personas.

**FECHA (PRD §6.10):**

| Entrada | `fecha_iso` | `precision_fecha` | Nota |
|---|---|---|---|
| `15 de enero de 2021` | `2021-01-15` | `dia` | validar día del mes |
| `diciembre de 2021` | `2021-12` | `mes` | no inventar día |
| `en 2019` | `2019` | `anio` | D13: es FECHA de precisión año |
| `del 1 al 15 de marzo de 2020` | vacío; `fecha_inicio`/`fecha_fin` | `intervalo` | validar `inicio <= fin` |
| `29 de febrero de 2021` | vacío | — | `estado_fecha = invalida` (no bisiesto) |
| `el próximo 15 de enero` (P2) | siguiente ocurrencia estricta tras el ancla | `dia` | `resuelta_desde_ancla = True`, `fecha_relativo = proximo` |
| `el pasado 15 de enero` (P2) | ocurrencia anterior estricta al ancla | `dia` | `resuelta_desde_ancla = True`, `fecha_relativo = pasado` |
| `15 de enero` sin año | año del ancla si hay ancla válida; si no, parcial | `dia` o parcial | sin ancla: `estado_fecha = parcial` |

El ancla se usa solo cuando la `fecha` del discurso es válida (no NaT, no fuera de rango). Años de dos dígitos se tratan como caso de prueba explícito; no se expanden sin regla documentada.

**MONTO (PRD §6.10):**

1. Calcular con `Decimal`; exportar en representación decimal estable (sin notación científica).
2. `valor_num` siempre en unidades; `escala` ∈ {uno, mil, millones, mil_millones, billones} documenta la expresión original.
3. Parser de cifras habladas: `2 mil 500 millones` → `2500000000`; `mil 200 millones` → `1200000000`; `tres mil millones` → `3000000000`.
4. `billón` = 10^12 (escala larga). Si el contexto lo contradice (por ejemplo, una comparación que solo cuadra con 10^9), `estado_monto = ambiguo` y `valor_num` vacío.
5. `moneda` ∈ {MXN, USD, vacío}. `pesos` → MXN; `dólares` → USD; `$` solo no fija moneda.
6. Expresiones ambiguas (`varios millones`, `entre 2 y 3 mil millones` sin unidad clara) quedan sin `valor_num`; rangos explícitos van a `valor_min`/`valor_max` con `estado_monto = rango`.
7. No se convierten monedas ni se suman montos entre pasajes de forma automática.

**PORCENTAJE y CANTIDAD (D11):** `20%` guarda `valor_num = 20` con unidad porcentaje, nunca `0.20`; las cantidades conservan unidad y escala. Viven en `salida/cantidades_auxiliares.csv`.

**ORG/LOC:** `canonico` solo por equivalencias verificadas en `config/gazetteer_extendido.csv` (sigla → nombre); `texto_normalizado` en minúsculas sin acentos para agrupar. Sin equivalencia verificada, `canonico` queda vacío, no se adivina.

**PER (P2):** `texto_normalizado`; vincular alias solo cuando un nombre es sufijo del otro y ambos aparecen en el mismo pasaje (`estado_identidad = vinculado_por_sufijo`). Compartir apellido no une personas.

## Pruebas

`tests/test_fusion.py`:

1. T08: un pasaje recuperado por Q1 y Q3 produce las mismas entidades bajo ambos `query_id`, una sola vez en `entidades_unicas.csv`, y la vista para el evaluador (si H0 la exige) no cuenta doble.
2. T13: tres fixtures sintéticos: coincidencia exacta → `ambos`; solape parcial → dos filas con `regla` y `modelo` más un registro en `08_solapes_parciales.csv`; mismo span con tipo distinto → dos filas conservadas.
3. Determinismo: dos corridas sobre el mismo fixture producen archivos byte a byte idénticos.
4. Contrato: 8 columnas, orden, clave única y dominios de `tipo` y `metodo`.

`tests/test_normalizacion.py` (PRD §6.10, mínimo exigido):

1. Al menos 15 casos de MONTO: cifras habladas, `mil millones`, `billón` con y sin contradicción, `$` sin moneda, `pesos`/`dólares`, rango, ambiguo, decimales con coma y punto.
2. Al menos 10 casos de FECHA: día, mes, año, intervalo, intervalo invertido, día inválido, bisiesto válido e inválido, año de dos dígitos, relativa con ancla y relativa sin ancla.
3. Prueba de no mezcla: tras normalizar, `inicio`, `fin` y `texto` de cada fila son idénticos a los de entrada, y `entidades.csv` no contiene ninguna columna de normalización.
4. PORCENTAJE: `20%` → 20, no 0.20.

Todas las pruebas usan fixtures sintéticos en `tests/fixtures/`; nunca el gold ni los juicios reales.

## Prohibiciones

- Nunca borrar, ajustar o filtrar filas de `entidades.csv` a partir de `gold_entidades.csv` o `gold_seleccion.csv`.
- Nunca emitir un `metodo` fuera de {regla, modelo, ambos}.
- Nunca añadir columnas a `entidades.csv` (D16); todo lo auxiliar va a `entidades_enriquecidas.csv`.
- Nunca modificar `inicio`, `fin` o `texto` durante la normalización, ni usar valores normalizados en la evaluación por span exacto.
- Nunca inventar un día para fechas de precisión mes o año, convertir monedas, sumar montos entre pasajes ni fijar moneda a partir de `$` solo.
- Nunca meter PORCENTAJE ni CANTIDAD en `entidades.csv` (D11).
- Nunca editar `kit/evaluar.py` ni leer `.env`; las diferencias con el kit van a `adaptadores_kit.py`.

## Skills relacionadas

- `kit-contratos`: resultados de H0 sobre deduplicación por pasaje y pasajes gold sin entidades, que deciden si hace falta el adaptador de vista única.
- `reglas-gazetteer`: produce las entidades por reglas, `cantidades_auxiliares.csv` y el gazetteer extendido que alimenta `canonico`.
- `ner-modelo`: produce las entidades del modelo y `07_uniones_spans.csv` que entran a la fusión.
- `evaluacion-ie`: consume `entidades.csv` y `08_solapes_parciales.csv` para la evaluación oficial y el análisis de errores.
- `integridad-congelacion`: etiqueta `reglas-congeladas` y manejo de cambios exploratorios posteriores al gold.
