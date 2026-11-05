---
name: tablas-respuesta
description: "Usa esta skill cuando vayas a generar, modificar o depurar las tablas de respuesta con evidencia de las consultas Q1-Q10 (src/mtx/respuestas.py, script 10_tablas.py, salida/respuestas.csv, salida/tablas_respuesta/*.md, config/tablas_respuesta.yaml, config/excluir_tablas.yaml, anotaciones/valoraciones.yaml, tests/test_respuestas.py)."
---
# Tablas de respuesta con evidencia (PRD §6.13, hito H8)

Una lista de entidades es un inventario. Las respuestas sobre participación, costos, pagos o fechas requieren evidencia de la relación en el texto citado (D17). "Respaldado en texto" significa que el corpus lo afirma, no que sea verdad.

## Cuándo usarla

- Al escribir o cambiar `src/mtx/respuestas.py`, `scripts/10_tablas.py` o `tests/test_respuestas.py`.
- Al definir o revisar `config/tablas_respuesta.yaml` o `config/excluir_tablas.yaml`.
- Al generar `salida/respuestas.csv`, `salida/tablas_respuesta/Q1.md` … `Q10.md` y `todas.md` (`make tablas`).
- Al validar que `anotaciones/valoraciones.yaml` existe y fue escrito por el alumno antes del reporte.
- Al responder la pregunta de demo "¿qué respuestas tienen evidencia textual y cuáles quedan incompletas?" (PRD §11).

## Prerrequisitos y congelaciones que aplican

Verificar antes de ejecutar `10_tablas.py`:

1. `data/mejor_modelo.json` existe (lo escribe `05_evaluar_ir.py`); las tablas se construyen sobre el **top-10 con filtro de fecha del mejor modelo** de cada consulta, nunca sobre otro ranking.
2. `salida/entidades_enriquecidas.csv` existe (script 08) con `en_marca`, `canonico`, `texto_normalizado`, `fecha_iso`, `valor_num`, `moneda`. Es la fuente de las tablas; `entidades.csv` conserva sus 8 columnas y no se toca (D16).
3. `salida/cantidades_auxiliares.csv` existe (D11, §6.7.3): de ahí salen dosis (Q2), litros (Q6), porcentajes (Q8), beneficiarios o sembradores (Q5) y lo que requiera Q9. Nunca se inyectan al `entidades.csv`.
4. `data/pasajes.parquet` con `intervencion_id`, `token_inicio`, `token_fin`, `interlocutor`, `es_reportero`, `inicio_cuerpo` (§6.1), necesarios para deduplicar ventanas y conservar quién habla.
5. `config/tablas_respuesta.yaml` fijado **antes** de generar; Q9 y Q10 ya definidos con su pregunta en `data/consultas.csv` (skill `corpus-segmentacion`).

Si alguno falta, detener y reportar qué script debe correr antes. Un cambio posterior en reglas, gazetteer, modelo NER o segmentación regenera las tablas y, si el cambio es sustancial, invalida las valoraciones del alumno (ver skill `integridad-congelacion`).

## Exclusiones antes de agregar

Regla U14. Se aplican sobre la copia en memoria, por consulta, antes de cualquier agrupación:

1. Quitar toda entidad con `en_marca == True` (el span cae dentro de la marca de interlocutor, `fin <= inicio_cuerpo`).
2. Quitar las PER cuyo `texto_normalizado` está en `config/excluir_tablas.yaml`. Valor por defecto: variantes del nombre del presidente. La lista aplica **solo a la columna de funcionarios o responsables** (campos de tipo PER), no a ORG, LOC, FECHA ni MONTO.
3. Registrar por consulta `n_excluidas_marca` y `n_excluidas_lista`; el script las imprime y las guarda junto con `respuestas.csv` (por ejemplo `salida/10_exclusiones.csv` con `query_id, motivo, n`). Se citan en el reporte.
4. `entidades.csv` y `entidades_enriquecidas.csv` no se modifican; las exclusiones no son correcciones, son filtros de presentación.

Lista de verificación: sin estas exclusiones, "Andrés Manuel López Obrador" encabezaría la columna de funcionarios en todas las consultas por aparecer en la marca de cada intervención. Si eso ocurre, el filtro 1 no se aplicó.

## Mapa consulta → campos y evidencia de relación

Vive en `config/tablas_respuesta.yaml` y se fija antes de generar. Reproduce la tabla del PRD §6.13.2; las consultas y lo que deben responder vienen de PRD §5.1:

| Consulta | Campo ← tipo | Evidencia mínima de la relación |
| --- | --- | --- |
| Q1 Tren Maya | dependencias y empresas ← ORG; estados ← LOC ∩ entidades federativas; montos ← MONTO | Participación o inversión vinculada al Tren Maya en la cita |
| Q2 Vacunas COVID-19 | farmacéuticas ← ORG ∩ lista D14; funcionarios ← PER; fechas ← FECHA; dosis ← CANTIDAD (dosis, auxiliares) | Entrega, aplicación o gestión de vacunas; fecha y cantidad ligadas al evento citado |
| Q3 Dos Bocas | organizaciones ← ORG; responsables ← PER; montos de inversión ← MONTO | Responsabilidad o inversión explícita en Dos Bocas o refinería Olmeca |
| Q4 AIFA / Santa Lucía | dependencia constructora ← ORG; lugares ← LOC; costos ← MONTO | Construcción o costo asociado a AIFA o Santa Lucía, no a otro aeropuerto |
| Q5 Sembrando Vida | secretaría operadora ← ORG; estados ← LOC; monto por beneficiario ← MONTO con contexto `mensual\|por sembrador\|por beneficiario` | Distinguir del presupuesto total |
| Q6 Huachicol | lugares ← LOC; organizaciones ← ORG; pérdidas ← MONTO; litros ← CANTIDAD (litros, auxiliares) | Evento de robo, recuperación o pérdida de combustible; conservar sentido y unidad |
| Q7 Pensión adultos mayores | montos bimestrales ← MONTO con contexto `bimestr`; institución ← ORG; fechas de aumento ← FECHA con contexto `aument` | Distinguir monto previo y nuevo; no asumir que todo monto es bimestral |
| Q8 Salario mínimo | organizaciones empresariales ← ORG ∩ tipo organización empresarial; porcentajes ← PORCENTAJE (auxiliares); montos diarios ← MONTO con contexto `diario\|al día` | Aumento o acuerdo salarial; distinguir propuestas de valores anunciados |
| Q9, Q10 | Definidos con su pregunta en el mismo YAML | Mapa y patrones fijados antes de generar la respuesta |

Reglas de aplicación:

1. Cada campo del YAML declara `tipo`, `filtro` (lista D14, entidades federativas, organización empresarial), `patrones_contexto` (regex en minúsculas) y `relacion` (texto de la evidencia mínima). El nombre de la regla que disparó va a `regla_relacion`.
2. El contexto se busca en **±60 caracteres** alrededor del span y en la **oración contigua** (anterior y siguiente dentro del mismo pasaje). Nada más lejos cuenta como evidencia.
3. Un valor cuyo span está en el top-10 pero sin patrón de relación en ese contexto no es `respaldado_en_texto`: queda `ambiguo` con la cita del lugar donde apareció.
4. Q9 y Q10 no se generan hasta que el YAML tenga su pregunta, campos y patrones; escribirlos después de ver la salida es ajustar al resultado y se documenta como tal.

## Contrato de respuestas.csv y estados de evidencia

`salida/respuestas.csv` lleva exactamente estas 16 columnas, en este orden:

`query_id, campo_respuesta, valor, unidad, relacion, estado, passage_id, doc_id, fecha_documento, evidencia_inicio, evidencia_fin, cita, entidades_referencia, regla_relacion, grupo_evento, interlocutor`

- `estado` ∈ {`respaldado_en_texto`, `ambiguo`, `contradictorio`, `no_encontrado`}. Cualquier otro valor rompe el contrato.
- `respaldado_en_texto`: tiene `passage_id`, `cita` exacta y `evidencia_inicio`/`evidencia_fin` válidos (`texto_pasaje[inicio:fin] == cita`).
- `ambiguo`: coocurrencia sin patrón de relación o relación con más de una lectura; conserva pasaje y cita.
- `contradictorio`: dos valores incompatibles para el mismo campo y evento; cada fila conserva su propia cita y comparten `grupo_evento`.
- `no_encontrado`: una fila por campo sin valor; `valor`, `passage_id`, `cita` y offsets quedan vacíos. Así la demo distingue "respondido" de "incompleto".
- `unidad`: `MXN`, `USD`, `dosis`, `litros`, `%`, `bimestral`, `diario`, etc.; `valor` conserva el texto tal como aparece y `entidades_referencia` las entidades de apoyo (por ejemplo la ORG que paga el monto).
- `interlocutor` se copia del pasaje; nunca se normaliza a "presidente".

## Agregación y credibilidad

1. **Alias:** agrupar por `canonico` cuando el gazetteer lo verificó; si no, por `texto_normalizado`. No inventar equivalencias nuevas aquí (eso vive en `fusion-normalizacion`).
2. **Evidencias repetidas del mismo evento:** las ventanas solapadas de un mismo discurso (`intervencion_id` y rango de tokens solapado) se deduplican y cuentan como **una** confirmación; el mismo `grupo_evento` lo marca.
3. **Conservar** por valor: frecuencia total, número de pasajes distintos y número de discursos (`doc_id`) distintos. Un valor repetido en diez ventanas de un discurso vale un discurso.
4. **Contradicciones:** si dos montos o fechas incompatibles tienen evidencia para el mismo evento, ambos salen como `contradictorio`; no se resuelve por mayoría ni se elige el más reciente.
5. **Quién habla:** si `es_reportero == True` o la intervención es pregunta, el valor se conserva con su `interlocutor` y se marca en `relacion` como pregunta, anuncio o respuesta. Nunca se atribuye al presidente lo que preguntó un reportero (T14).
6. **Corte:** hasta 8 valores por campo, ordenados primero por evidencia directa (`respaldado_en_texto` > `contradictorio` > `ambiguo`) y después por frecuencia de discursos distintos. Los que quedan fuera no se pierden del CSV; solo no aparecen en la tabla Markdown.
7. Las cantidades auxiliares (Q2, Q5, Q6, Q8, Q9) siguen las mismas reglas de contexto, deduplicación y estado que las entidades.

## Tablas Markdown y valoraciones del alumno

Salida: `salida/tablas_respuesta/Q1.md` … `Q10.md` y `todas.md` (concatenación en orden). Cada archivo:

1. Encabezado con el ID y la pregunta literal de `data/consultas.csv`.
2. Línea de contexto: modelo usado, ventana de fechas, exclusiones aplicadas (marca y lista).
3. Tabla compacta por campo: `valor | tipo o rol | pasaje de evidencia (passage_id) | fecha del discurso | cita breve`, con el estado visible; los `no_encontrado` aparecen como fila "sin evidencia en el top-10".
4. Bloque `valoracion:` al final, tomado de `anotaciones/valoraciones.yaml` (clave `Q1` … `Q10`, 2 a 3 líneas: ¿es creíble?, ¿qué le falta?, ¿qué está mal?). Si la entrada no existe, el bloque se imprime vacío con la leyenda `[VALIDAR] pendiente del alumno`.

Reglas sobre `anotaciones/valoraciones.yaml`:

- Las escribe el **alumno** (hito H8, unos 40 minutos). Está **prohibido** que el asistente las redacte, sugiera borradores o "complete" entradas vacías.
- `[VALIDAR]` antes de `11_reporte.py`: existen las 10 entradas y ninguna está vacía ni es texto generado. El script de reporte falla con mensaje claro si falta alguna.
- Guardar junto a cada valoración el hash de la tabla que valoró (`tabla_sha256`). Si `10_tablas.py` regenera una tabla con cambio sustancial (valores, estados o pasajes distintos), la valoración se marca como invalidada y el alumno la vuelve a escribir.
- La evaluación de credibilidad es un entregable del examen (R08): las tablas sin valoración no son entregables.

## Pruebas y prohibiciones

`tests/test_respuestas.py`, rápidas y con fixtures sintéticas (sin corpus ni modelos):

1. **T14:** pasaje con varias ORG, varios MONTO y una pregunta de reportero → ninguna relación se atribuye sin patrón de contexto; ventanas solapadas de la misma intervención se deduplican en un `grupo_evento`; `interlocutor` del reportero conservado.
2. Exclusiones U14: entidad con `en_marca == True` y PER de la lista no aparecen; el conteo por consulta coincide; la lista no afecta ORG/LOC; `entidades.csv` con hash intacto.
3. Contrato: 16 columnas exactas, `estado` dentro del conjunto, cada `respaldado_en_texto` cumple `texto_pasaje[inicio:fin] == cita`, cada `no_encontrado` con campos de evidencia vacíos.
4. Patrones de contexto: un MONTO sin `bimestr` en ±60 caracteres ni en la oración contigua no sale como monto bimestral en Q7; un MONTO con `diario|al día` sí sale en Q8; `mensual|por sembrador|por beneficiario` separa el monto por beneficiario del presupuesto en Q5.
5. Contradicciones: dos montos incompatibles para el mismo evento → ambas filas `contradictorio`, ninguna eliminada; corte de 8 valores respeta el orden evidencia directa y luego frecuencia.
6. Valoraciones: faltante o vacía → `[VALIDAR]` falla; cambio de hash de tabla → valoración invalidada.

Prohibido:

- Generar tablas sobre un ranking distinto del top-10 con filtro del mejor modelo.
- Modificar `entidades.csv`, `entidades_enriquecidas.csv` o `cantidades_auxiliares.csv` desde `respuestas.py`.
- Cambiar `config/tablas_respuesta.yaml` o `config/excluir_tablas.yaml` después de ver las tablas sin anotarlo en el registro de cambios y regenerar.
- Resolver contradicciones por mayoría, atribuir al presidente dichos de reporteros o presentar `ambiguo` como respaldado.
- Redactar, completar o "mejorar" `anotaciones/valoraciones.yaml`.

## Skills relacionadas

- `integridad-congelacion`: qué invalida tablas y valoraciones tras un cambio de reglas, modelo o segmentación.
- `fusion-normalizacion`: origen de `canonico`, `texto_normalizado`, `en_marca` y `cantidades_auxiliares.csv`.
- `pool-juicios-ir`: cómo se fija `data/mejor_modelo.json`, base del top-10 de cada consulta.
- `corpus-segmentacion`: `intervencion_id`, tokens de ventana, `interlocutor` y definición de Q9/Q10.
- `reporte-pdf`: consume `respuestas.csv`, las tablas y `valoraciones.yaml`; exige el `[VALIDAR]` previo.
