---
name: evaluacion-ie
description: "Usa esta skill al evaluar la extracción de entidades contra el gold (09_evaluar_ie.py, parte IE de src/mtx/evaluacion.py, kit/evaluar.py ie, resultados_ie.csv), al comparar candidatos NER sobre el conjunto de selección (09_comparacion_ner.csv), al registrar cambios posteriores al congelamiento o al clasificar errores de IE (analizar_errores, 09_analisis_errores.csv)."
---
# Evaluación de IE y análisis de errores

Cubre la parte IE de `src/mtx/evaluacion.py`, el script `09_evaluar_ie.py`, el objetivo
`make evaluar-ie` y los artefactos `resultados_ie.csv` y `salida/09_*.csv`. Fuente: PRD §6.12,
con apoyo de §2 (contrato de `kit/evaluar.py ie`), §6.8 (selección NER), §6.11 (gold y P04),
tabla de decisiones D09 y D15, y umbrales U19.

## Cuándo usarla

- Al escribir o modificar `evaluar_ie()`, `analizar_errores()` o `09_evaluar_ie.py`.
- Al correr `python kit/evaluar.py ie gold_entidades.csv entidades.csv` para la cifra oficial.
- Al comparar candidatos NER con `anotaciones/gold_seleccion.csv` (solo si existe el conjunto de selección).
- Al registrar un ajuste de regex o gazetteer hecho después de ver resultados (D15).
- Al preparar la sección 6 del reporte (1.0 punto) o responder en la demo "¿cómo evitaste usar el gold para elegir el NER?" y "¿qué entidad falló más?" (PRD §10).

## Prerrequisitos y congelaciones que aplican

Lista de verificación antes de ejecutar nada:

1. `git tag --list reglas-congeladas` devuelve la etiqueta y precede al primer commit de los archivos gold (D15, `validar_gold()`).
2. `anotaciones/cierre_gold.json` existe: los 20 IDs del manifiesto `anotaciones/muestra_gold.csv` están en estado `cerrado` y `gold_entidades.csv` está exportado a la raíz (§6.11).
3. `data/modelo_ner.json` existe con `modelo, revision, f1_seleccion, f1_seleccion_alternativa, criterio`. Si no hay conjunto de selección, contiene el NER principal y el reporte declara que la elección fue técnica (D09).
4. `entidades.csv` fusionado en la raíz proviene del extractor congelado (reglas + modelo fijado) y solo emite `metodo` en `regla`, `modelo`, `ambos`. Cualquier otro valor se descarta en silencio por el kit (§2).
5. Las pruebas de contrato de `kit/evaluar.py ie` de H0 están documentadas: deduplicación entre consultas, pasajes gold sin entidades (P04), filas para tipos sin soporte (T10).

Si falta cualquiera de los cinco, detente y resuelve con `integridad-congelacion`; no se evalúa con una salida provisional.

## Orden de ejecución (selección NER antes del gold)

El orden es obligatorio y no se invierte aunque "ya esté el gold listo":

1. **Solo si hay conjunto de selección.** Para cada candidato, `salida/entidades_{slug}.csv` (solo `metodo == modelo`) se evalúa con `kit/evaluar.py ie anotaciones/gold_seleccion.csv salida/entidades_{slug}.csv`. Gana el mayor F1 en `metodo == modelo, tipo == TODOS`; empate al principal (§6.8).
2. Escribir `data/modelo_ner.json` con el ganador **antes** de abrir `gold_entidades.csv`. Commit.
3. Generar `salida/09_comparacion_ner.csv`: F1 por tipo de cada candidato en selección (columna que decide) y en gold (columna informativa). Las cifras en gold se calculan después del paso 2 y no cambian la elección.
4. Confirmar que `entidades.csv` fue generado con el modelo de `data/modelo_ner.json` (comparar `modelo` y `revision` del manifiesto).
5. Solo entonces correr la evaluación oficial.

Si el alumno pide "probar el otro modelo sobre el gold a ver cuál queda mejor", la respuesta es no: eso es exactamente lo que D09 prohíbe. Se puede mostrar como informativo en `09_comparacion_ner.csv`, nunca como criterio.

## Evaluación oficial con el kit

```bash
python kit/evaluar.py ie gold_entidades.csv entidades.csv
```

1. La salida es `resultados_ie.csv`; se copia idéntica a `salida/resultados_ie.csv`. No se insertan columnas auxiliares (§8).
2. Registrar en `salida/manifiesto_ejecucion.json`: hash de `gold_entidades.csv`, de `entidades.csv`, del kit, commit del código, modelo y revisión del NER, versión de gazetteers y reglas (D18).
3. Semántica del kit (§2): TP solo con coincidencia exacta de `(passage_id, tipo, inicio, fin)`; `regla` se evalúa con filas `regla` + `ambos`; `modelo` con `modelo` + `ambos`; `combinado` con todas. Fórmulas: P = TP/(TP+FP), R = TP/(TP+FN), F1 = 2PR/(P+R).
4. Solo evalúa pasajes presentes en el gold: un pasaje cerrado con cero entidades no aparece. Registrar cuántos pasajes evaluó realmente y conservar la cifra oficial sin modificarla (P04).
5. Verificar los criterios de aceptación de la sección "Salidas" antes de dar la cifra por buena.

## Detalle, complementaria de 20 IDs y cambios post-congelamiento

**`salida/09_ie_detalle.csv`** (producido por `evaluar_ie()` en `evaluacion.py`, no por el kit):

- Una fila por `(metodo, tipo)` con `metodo` en `regla`, `modelo`, `combinado` y `tipo` en PER, ORG, LOC, FECHA, MONTO, TODOS.
- Columnas: P, R, F1, TP, FP, FN y soporte (entidades gold del tipo).
- Tipos sin soporte en el gold se marcan "no aplicable", nunca 0.0 disfrazado. El CSV oficial no se altera.
- Un NER limitado a PER/ORG/LOC no cubre FECHA/MONTO: las filas `modelo × FECHA` y `modelo × MONTO` se muestran explícitamente como sin cobertura, y el reporte lo dice.

**`salida/09_evaluacion_20_ids.csv`** (evaluación complementaria, P04 y T10):

1. Tomar los 20 `passage_id` del manifiesto `anotaciones/muestra_gold.csv`, no los IDs con filas en el gold.
2. Contar como FP toda predicción en un pasaje cerrado con cero entidades gold.
3. Reportar P/R/F1 por método y tipo con esa base; indicar cuántos pasajes evaluó el kit y cuántos la complementaria.
4. No se inventa una entidad centinela ni se sustituyen pasajes vacíos. La cifra oficial sigue siendo la del kit.

**`salida/09_cambios_post_congelamiento.csv`** (D15):

- Se crea solo si, después de ver resultados, se ajusta una regex, el gazetteer o `criterios_anotacion.md`.
- Columnas mínimas: `fecha, archivo, descripcion, commit_antes, commit_despues, f1_antes, f1_despues, tipo, metodo`.
- El F1 anterior se conserva como oficial; el reporte presenta ambas cifras y marca la segunda como exploratoria. Nunca se sustituye `resultados_ie.csv` por el resultado ajustado.

## Análisis de errores

`analizar_errores(gold, pred, pasajes)` corre sobre los 20 pasajes gold y clasifica cada FN y cada FP. Las categorías no son partición exclusiva: un error puede llevar dos o más.

| Categoría | Condición (§6.12) | Subcasos |
|---|---|---|
| `frontera` | predicción del mismo tipo que solapa parcialmente el gold | `entidad_partida` (dos o más predicciones dentro de un gold), `monto_sin_unidad` (predicción prefijo del gold) |
| `tipo` | mismo span, tipo distinto | `obra_LOC_vs_ORG` cuando el texto está en el gazetteer de obras |
| `sigla_no_reconocida` | gold en mayúsculas de 2 a 7 letras sin predicción que lo cubra | — |
| `en_marca` | el span cae dentro de la marca de interlocutor (`fin <= inicio_cuerpo`) | describe dónde ocurre, no demuestra causa |
| `omision` | FN sin predicción que solape | — |
| `espuria` | FP sin gold que solape | subclasificada por `fuente`: `regex`, `gazetteer`, `marca`, `modelo` |

Pasos:

1. Cargar gold, `entidades.csv` y `data/pasajes.parquet` (para `texto` e `inicio_cuerpo`).
2. Para cada `passage_id` del gold, emparejar gold y predicciones por solape de offsets y tipo; aplicar las reglas de la tabla.
3. Escribir `salida/09_analisis_errores.csv` con columnas exactas: `passage_id, tipo, texto_gold, texto_pred, inicio, fin, metodo, categoria, fuente, contexto` (contexto: ventana de texto alrededor del span).
4. Escribir `salida/09_resumen_errores.csv`: conteo por `categoria`, `tipo` y `metodo`.
5. Revisar los ejemplos reales antes de redactar conclusiones: abrir el CSV, leer al menos un caso por categoría y confirmar que la etiqueta automática es correcta.
6. Para cada categoría del enunciado (entidad partida, sigla no reconocida, monto sin unidad, obra LOC u ORG, efecto de mayúsculas) el reporte incluye un caso observado con `passage_id` y texto, o declara explícitamente que no apareció. No se inventan errores para llegar a una cuota; la meta de 8 ejemplos es orientativa.

## Salidas, figuras y criterios de aceptación

Artefactos (todos UTF-8 sin BOM, fechas ISO):

| Archivo | Contenido |
|---|---|
| `resultados_ie.csv` (raíz y `salida/`) | salida literal del kit |
| `salida/09_ie_detalle.csv` | P/R/F1, TP/FP/FN, soporte por método y tipo |
| `salida/09_evaluacion_20_ids.csv` | complementaria sobre los 20 IDs del manifiesto |
| `salida/09_comparacion_ner.csv` | solo si hubo conjunto de selección |
| `salida/09_cambios_post_congelamiento.csv` | solo si hubo ajustes tras ver resultados |
| `salida/09_analisis_errores.csv`, `salida/09_resumen_errores.csv` | errores clasificados y resumen |
| `reporte/figuras/ie_f1_por_tipo_metodo.png`, `reporte/figuras/ie_errores_por_categoria.png` | figuras de la sección 6 |

Criterios de aceptación (lista de verificación final):

- [ ] `resultados_ie.csv` tiene filas para `regla`, `modelo`, `combinado` × cada tipo más `TODOS`.
- [ ] Hashes de gold, entidades y kit registrados en `salida/manifiesto_ejecucion.json`; `salida/tiempos_ejecucion.json` con la duración del script.
- [ ] Complementaria de 20 IDs generada y coherente con el número de pasajes que evaluó el kit.
- [ ] `09_comparacion_ner.csv` guardado si se hizo comparación; `data/modelo_ner.json` con commit anterior al uso del gold.
- [ ] Ejemplos de error reales clasificados (meta orientativa: 8) y cada categoría del enunciado con caso o con "no apareció".

## Umbrales de alerta y prohibiciones

Umbrales (U19, son alertas, no metas):

1. **F1 combinado TODOS < 0.30** obliga a buscar un bug antes de reportar: offsets de `entidades.csv` contra `texto` canónico, mapa de etiquetas del NER (B-/I- a PER/ORG/LOC), tipo en mayúsculas, `passage_id` coincidente con el gold. Solo tras descartar bug se reporta la cifra baja con explicación.
2. **F1 = 1.0 en un tipo con más de 5 entidades gold** dispara la alerta de gold copiado: verificar que el gold no se anotó a partir de predicciones (modo ciego, `cierre_gold.json`) y que `entidades.csv` no se generó leyendo el gold.
3. Los validadores técnicos no certifican que las decisiones humanas sean correctas: una métrica plausible no sustituye la revisión de ejemplos.

Prohibiciones:

- Ajustar reglas, gazetteer, mapa de etiquetas o gold mirando resultados sin registrarlo en `09_cambios_post_congelamiento.csv` como exploratorio (D15).
- Elegir o reajustar el NER con el gold de 20 (D09). El gold nunca elige ni ajusta nada.
- Evaluar con una salida provisional de otro modelo y presentarla como oficial.
- Retocar el gold para subir métricas; una corrección de error humano exige revisión explícita del alumno, motivo y nueva versión (§6.11).
- Rellenar, completar o "corregir" anotaciones gold o del conjunto de selección: las produce el alumno (§1).
- Inventar errores, entidades centinela o sustituir pasajes vacíos para cuadrar cuotas o métricas.

## Skills relacionadas

- `integridad-congelacion`: antes de tocar gold, reglas o modelo, y ante cualquier métrica anómala.
- `ner-modelo`: generación de `salida/entidades_{slug}.csv`, verificación previa al gold y `data/modelo_ner.json`.
- `fusion-normalizacion`: construcción del `entidades.csv` fusionado que entra a la evaluación.
- `gold-anotacion`: muestra gold, conjunto de selección, `validar_gold()` y cierre ciego.
- `kit-contratos`: pruebas de contrato de `kit/evaluar.py ie` (deduplicación, P04, tipos sin soporte).
