---
name: reglas-gazetteer
description: "Usa esta skill cuando vayas a escribir, extender o probar las reglas de extracción (regex FECHA y MONTO, cantidades auxiliares, gazetteers ORG/LOC, regla de marca de interlocutor) en src/mtx/reglas.py, 06_reglas.py o tests/test_reglas.py, o cuando toque congelar las reglas antes del gold."
---
# Reglas y gazetteers (módulo `reglas.py`, P0)

## Cuándo usarla

- Vas a crear o modificar `src/mtx/reglas.py`, `06_reglas.py` o `tests/test_reglas.py`.
- Vas a minar siglas, extender `config/gazetteer_extendido.csv` o construir `config/gazetteer_loc.csv`.
- Un test de `tests/test_reglas.py` falla y hay que decidir si se corrige la regla o se documenta el caso.
- El módulo está terminado y hay que crear la etiqueta `reglas-congeladas` antes de anotar el gold.

Fuente de verdad: PRD §6.7 (6.7.1 a 6.7.10), §3.3, §3.6, decisiones D11, D13, D14, D15, anexo B, tarea T11.

## Prerrequisitos y congelaciones que aplican

1. Existen los pasajes canónicos con `texto` completo (mayúsculas y acentos intactos) e `inicio_cuerpo` por pasaje (skill `corpus-segmentacion`). Las reglas trabajan **siempre** sobre ese `texto`, nunca sobre los tokens normalizados de IR (PRD §6.7).
2. Existe `kit/gazetteer_dependencias.csv` con columnas `nombre,siglas,tipo` (PRD §3.3). Contar sus entradas y tipos al cargarlo (PV del PRD: 76 entradas esperadas; no asumas la cifra, cuéntala).
3. Offsets: índices de carácter Python sobre `texto`, `inicio` inclusivo, `fin` exclusivo, `0 <= inicio < fin <= len(texto)` y `texto[inicio:fin] == texto_entidad` (PRD §3.6). Nunca bytes ni UTF-16.
4. Convenciones de anotación fijadas en `config/criterios_anotacion.md` antes de anotar; las reglas deben ser coherentes con la tabla de PRD §3.6.
5. Si ya existe la etiqueta `reglas-congeladas`, cualquier cambio a reglas o gazetteers es **exploratorio**: se conserva el F1 anterior y se reporta el nuevo como exploratorio (D15). Consulta la skill `integridad-congelacion` antes de tocar nada.

## Regex FECHA

Reglas de span (PRD §6.7.1, §3.6, D13): `fin` exclusivo, sin espacios colgantes; incluye el modificador relativo (`próximo`, `pasado`, `este`) y excluye preposiciones y artículos introductorios (`el`, `en`, `desde`, `el año`).

| Entrada | Span esperado | Nota |
| --- | --- | --- |
| `15 de diciembre de 2023` · `primero de enero de 2020` · `1 de septiembre del 2021` | completo | fecha absoluta |
| `enero de 2021` · `diciembre del 2019` | completo | precisión mes |
| `15/12/2023` · `1/1/19` | completo | año de dos dígitos: normalizar solo con regla de siglo documentada; si es ambiguo, `fecha_iso` vacía |
| `el próximo 15 de enero` · `el pasado 20 de noviembre` · `este 1 de julio` | `próximo 15 de enero` · `pasado 20 de noviembre` · `este 1 de julio` | D13: modificador dentro, artículo fuera |
| `en diciembre de 2021` | `diciembre de 2021` | preposición fuera |
| `en 2019` · `el año 2019` · `desde 2019` | `2019` | precisión año (D13) |
| `del 1 al 15 de enero de 2021` | una sola entidad de intervalo | PRD §3.6 |

Negativos (cero coincidencias): `15 personas`, `página 15`, `2 horas`, `15 de los 32 estados`, `15 de cada 100`, `2019` sin contexto temporal.

Caso especial: `31 de febrero` **se detecta** por la regex, pero la normalización lo rechaza; se registra como detección no resoluble (estado de normalización explícito, `fecha_iso` vacía). El test verifica ambas cosas.

No cubiertos (se documentan en resultados, no se fuerzan): `de 2019 a 2024` emite dos FECHA de año, no un intervalo; fechas totalmente en palabras (`quince de enero`).

Pasos:
1. Escribe los casos de la tabla y los negativos como `pytest.mark.parametrize` **antes** de la regex.
2. Implementa la regex con grupos nombrados (día, mes, año, modificador) y la función de normalización a ISO con estado.
3. Itera hasta verde; lo que no pase y no esté en el PRD como "cubierto" se anota en la lista de no cubiertos.

## Regex MONTO y cantidades auxiliares

MONTO representa dinero (D11): cifra + escala + moneda o símbolo, sin recortar el `$` (PRD §3.6). Patrón semilla de PRD §6.7.2 (se extiende hasta pasar la suite; no se entrega sin probar), compilado con `re.IGNORECASE`:

```python
NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
PALABRA_NUM = r"un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|cien"
CIFRA = rf"(?:(?:{NUM}|{PALABRA_NUM})(?:\s+mil(?!\w)(?:\s+(?:{NUM}))?)?|mil(?!\w)(?:\s+(?:{NUM}))?)"
ESCALA = r"(?:\s+(?:millones|millón|billones|billón))?"
MONEDA = r"\s+(?:de\s+)?(?:pesos|dólares|dolares)"
LIMITE_IZQ = r"(?<![\w$.,])"
RE_MONTO = rf"{LIMITE_IZQ}(?:\$\s?{CIFRA}{ESCALA}(?:{MONEDA})?|{CIFRA}{ESCALA}{MONEDA})"
RE_PORCENTAJE = rf"{LIMITE_IZQ}(?:{NUM})\s*(?:por\s+ciento|%)"
```

| Grupo | Casos |
| --- | --- |
| MONTO positivos (span completo) | `20 mil millones de pesos` · `2 mil 500 millones de pesos` · `1,200 millones de pesos` · `$1,200 millones` · `$ 5 mil` · `5 mil pesos` · `500 pesos` · `2 mil millones de dólares` · `100 millones de dólares` · `1.5 billones de pesos` · `6 mil 300 pesos` · `mil 200 pesos` · `un millón de pesos` · `dos mil millones de pesos` |
| MONTO negativos (cero coincidencias) | `20 mil personas` · `15 millones de dosis` · `3 millones de árboles` · `20 por ciento` · `20%` · `página 20` · `500 pesos` dentro de `1500 pesos` (debe salir un solo span `1500 pesos`; `LIMITE_IZQ` impide empezar a mitad de cifra) |
| PORCENTAJE (auxiliar) | `20%` → 20 · `20 por ciento` → 20 · `3.5 por ciento` → 3.5, unidad `porcentaje` |
| CANTIDAD (auxiliar) | `15 millones de dosis` · `100 mil litros` · `30 mil elementos` · `200 mil sembradores`; también `N sucursales`, `N hectáreas`, `N beneficiarios`, `N kilómetros` |

No cubiertos (se documentan): separador de miles con punto (`1.200 pesos`, ambiguo con decimales; se detecta sin valor numérico) y cifras en palabras más allá de las escalas (`trescientos cincuenta pesos`).

Cantidades auxiliares (PRD §6.7.3, D11):
1. `RE_PORCENTAJE` y `RE_CANTIDAD` producen filas de `salida/cantidades_auxiliares.csv` con columnas exactas: `query_id, passage_id, texto, inicio, fin, tipo_aux, valor_num, unidad, estado_normalizacion, regla_id`.
2. `tipo_aux` es `PORCENTAJE` o `CANTIDAD`. **Nunca** se escriben en `entidades.csv` ni se devuelven como `Entidad` desde `extraer_reglas`.
3. Un test comprueba que ningún porcentaje ni dosis aparece como MONTO y que sí aparece en las auxiliares. Alimentan Q2, Q5, Q6, Q8 y Q9 (skill `tablas-respuesta`).

## Gazetteers ORG y LOC (y revisión humana de siglas)

### ORG extendido (PRD §6.7.4, §3.3)

1. Base: carga `kit/gazetteer_dependencias.csv`. Etiqueta: `tipo == "obra"` → LOC; cualquier otro tipo → ORG.
2. `minar_siglas(pasajes)` genera `salida/06_siglas_candidatas.csv` con columnas `sigla, nombre_propuesto, frecuencia, ejemplo` a partir de:
   - patrón `Nombre Largo (SIGLAS)`: nombre de 2 a 8 palabras con inicial mayúscula o preposiciones, siglas de 2 a 8 mayúsculas;
   - frecuencia de tokens todo en mayúsculas de 3 a 7 letras **del cuerpo** (desde `inicio_cuerpo`, nunca de la marca) que no estén en la stoplist.
3. **Revisión del alumno** `[VALIDAR]`: en la pestaña "Gazetteer" de la app (skill `app-anotacion`) o editando el CSV. Decide aceptar, corregir tipo (ORG, LOC, descartar) y nombre. El asistente propone candidatas; no decide qué entra.
4. Resultado: `config/gazetteer_extendido.csv` con columnas exactas `nombre, variantes, siglas, tipo, etiqueta (ORG|LOC), origen (kit|minado|manual), evidencia`.
5. Sin cuota de extensión: se justifica por cobertura útil y se reportan entradas base, nuevas, rechazadas y cobertura.
6. D14: farmacéuticas, marcas de vacuna y mecanismos multilaterales (Pfizer, BioNTech, AstraZeneca, CanSino, Sputnik V, Gamaleya, Sinovac, Moderna, Janssen, Johnson & Johnson, Abdala, Patria, COVAX) son ORG; el genérico "vacuna" queda fuera del span.

Lecciones del corpus real (H5):
- Siglas de 5 letras o menos y `COMUNES_SENSIBLES` (Salud, Bienestar, Cultura, Patria, Morena): coincidencia exacta o todo en mayúsculas; nunca en minúscula.
- `Nombre (SIGLA)` casi no aparece en el cuerpo: la minería se basa en frecuencia. El alumno revisa solo las de frecuencia ≥ 50; se filtran los números romanos.
- Las pruebas de minado usan siglas inventadas (`ZXQ`): una sigla real aceptada (INAI, CNDH) la excluye de los candidatos.
- Los nombres completos de siglas aceptadas los escribe el asistente; el alumno los confirma antes de `make congelar`. `make reglas` tarda unos 3 minutos.

Entradas que deben existir (test `test_gazetteer_entradas_obligatorias`): IMSS, ISSSTE, Pemex, CFE, Sedena, Semar, Conagua, Fonatur, Insabi, Cofepris, Birmex, Pfizer, AstraZeneca, CanSino, Sputnik V, COVAX, Coparmex, CCE, Concanaco, Conasami, Morena, PAN, PRI, PRD, ONU, OMS, OPS, FMI, Banco Mundial, Banxico, SAT, Guardia Nacional, Secretaría del Bienestar, STPS, SICT, Sener, Sedatu, Grupo Carso, ICA.

### LOC (PRD §6.7.5)

`config/gazetteer_loc.csv` debe contener:
- Las 32 entidades federativas con variantes: Ciudad de México / CDMX; Estado de México / Edomex; Michoacán / Michoacán de Ocampo; Veracruz / Veracruz de Ignacio de la Llave; Coahuila / Coahuila de Zaragoza; y las demás.
- Municipios y lugares de las consultas: Palenque, Cancún, Tulum, Mérida, Chetumal, Escárcega, Tula, Salamanca, Minatitlán, Salina Cruz, Coatzacoalcos, Santa Lucía, Istmo de Tehuantepec.
- Obras como LOC (EX): Tren Maya, Dos Bocas, refinería Olmeca, AIFA, Aeropuerto Internacional Felipe Ángeles, Tren Interoceánico, Corredor Interoceánico.
- Países y capitales: Estados Unidos, Washington, China, Rusia, India, Argentina, Cuba.

Regla de span con lugar interno (PRD §3.6): `Secretaría de Salud de Tabasco` es una sola ORG; no se emite LOC `Tabasco` dentro de ella (la resolución de colisiones por span más largo lo garantiza).

## Regla de marca de interlocutor

Se analiza `texto[:inicio_cuerpo]` (PRD §6.7.6, §3.6). Procedencia `fuente="marca"`, `en_marca=True`.

| Marca | Resultado |
| --- | --- |
| `SECRETARIO DE SALUD, JORGE ALCOCER VARELA:` | PER `JORGE ALCOCER VARELA` (lo que sigue a la última coma, 2 a 5 palabras) |
| `PRESIDENTE ANDRÉS MANUEL LÓPEZ OBRADOR:` | PER `ANDRÉS MANUEL LÓPEZ OBRADOR`: se quita el cargo por **lista de cargos conocidos**, no por suponer que todo lo que sigue es persona |
| Marca sin coma que coincide con el gazetteer | ORG |
| `PREGUNTA`, `INTERLOCUTOR`, `INTERLOCUTORA` y marcas genéricas | sin entidad |

Corpus real: las marcas vienen como `NOMBRE` solo y `NOMBRE, CARGO`, no `CARGO, NOMBRE` como supone el PRD. La regla va por segmentos separados por coma; el cargo inicial solo se quita si la marca no tiene comas (si no, `FEDERAL DEL CONSUMIDOR` sale como PER); un segmento que empieza con cargo es cargo completo y no genera ORG ni LOC (decisión del alumno, motivo `cargo_en_marca` en `06_colisiones_reglas.csv`).

Pasos:
1. Mantén la lista de cargos (PRESIDENTE, SECRETARIO/A, SUBSECRETARIO/A, DIRECTOR/A GENERAL, GOBERNADOR/A, etc.) en el módulo, documentada; no la amplíes a ciegas.
2. Verifica que la PER resultante cumple el invariante de offsets dentro del `texto` completo (la marca forma parte del texto).
3. El gazetteer admite coincidencia con el texto en mayúsculas de la marca (PRD §6.7.7); la procedencia `marca` se conserva para medir errores en el prefijo (skill `evaluacion-ie`).

## Motor de coincidencia y colisiones

Motor del gazetteer (PRD §6.7.7), lista de verificación:
- [ ] Todo patrón pasa por `re.escape` (nombres con `.`, `&`, paréntesis).
- [ ] Patrones ordenados por longitud descendente antes de compilar la alternancia.
- [ ] Límites de palabra que respetan acentos: `(?<![\wáéíóúñü])...(?![\wáéíóúñü])`.
- [ ] Siglas de ≤5 caracteres: sensibles a mayúsculas (`IMSS`, `Pemex`, `COVAX`, `PAN`, `SAT`); el resto, insensibles.
- [ ] Dentro del gazetteer gana la coincidencia más larga (longest match).
- [ ] Una sigla coincidente con palabra común (por ejemplo `PAN` frente a `pan`, `SAT` frente a `sat`) no se marca en minúsculas.

Colisiones entre fuentes (PRD §6.7.8):
1. Ante solape entre dos fuentes se conserva el span más largo (`fin - inicio`).
2. Ante empate de longitud, jerarquía determinista: `regex_fecha > regex_monto > gazetteer_loc > gazetteer_org > marca`.
3. Cada solape suprimido se cuenta en `salida/06_colisiones_reglas.csv` (fuente ganadora, fuente suprimida, spans y textos). Este archivo alimenta la sección de errores del reporte (skill `reporte-pdf`).

## API y suite de pruebas (bloqueante)

API (PRD §6.7.9):

```python
@dataclass
class Entidad:
    tipo: str          # PER | ORG | LOC | FECHA | MONTO
    texto: str
    inicio: int
    fin: int
    metodo: str = "regla"
    fuente: str = ""   # regex_fecha | regex_monto | gazetteer_org | gazetteer_loc | marca
    en_marca: bool = False

def extraer_reglas(texto: str, inicio_cuerpo: int) -> list[Entidad]: ...
```

Invariante en todo test: `texto_pasaje[inicio:fin] == entidad.texto`.

Suite `tests/test_reglas.py` (PRD §6.7.10, T11), parametrizada y bloqueante:
1. FECHA: positivos con span exacto, negativos con cero coincidencias, valores normalizados (`fecha_iso`, precisión, estado; `31 de febrero` no resoluble).
2. MONTO y auxiliares: positivos con span, negativos, `valor_num`/`unidad` de PORCENTAJE y CANTIDAD, y que ninguna auxiliar sea `Entidad`.
3. Gazetteer: longest match, siglas sensibles a mayúsculas, acentos en límites, sigla coincidente con palabra común, entradas obligatorias presentes, `Secretaría de Salud de Tabasco` como ORG completa, `Tren Maya` / `Ciudad de México` / `Dos Bocas` como LOC.
4. Regla de marca: los cuatro casos de la tabla anterior.
5. Colisiones: span más largo gana; empate resuelto por jerarquía; fila escrita en `06_colisiones_reglas.csv`.
6. Invariante de offsets sobre 200 pasajes reales incluidas las marcas.

Reglas de conducta:
- Los ejemplos de prueba son sintéticos y no se presentan como anotaciones del corpus.
- Un caso que falla **se guarda para explicarlo**, no se maquilla ni se borra del parametrize; se marca con `xfail(strict=True)` y razón citando el PRD, y se lista en resultados.
- El módulo no se da por terminado hasta `uv run pytest tests/test_reglas.py` en verde.
- `06_reglas.py` corre `extraer_reglas` sobre todos los pasajes y escribe `salida/cantidades_auxiliares.csv`, `salida/06_siglas_candidatas.csv` y `salida/06_colisiones_reglas.csv`.

## Congelar antes del gold

Orden obligatorio (D15, PRD §6.7): suite en verde → revisión de siglas cerrada por el alumno → congelar → **después** abrir el gold.

1. `uv run pytest tests/test_reglas.py` en verde y `config/gazetteer_extendido.csv`, `config/gazetteer_loc.csv`, `config/criterios_anotacion.md` ya revisados por el alumno.
2. `make congelar` → crea la etiqueta git `reglas-congeladas` sobre el commit que contiene reglas, gazetteers y criterios.
3. Verifica: `git tag -l reglas-congeladas` y `git diff reglas-congeladas -- src/mtx/reglas.py config/` sin cambios.
4. Solo entonces se abre la anotación del gold (skill `gold-anotacion`).
5. Todo cambio posterior a reglas o gazetteers conserva el F1 anterior en los resultados y marca el nuevo como exploratorio; nunca se reescribe la cifra congelada.

## Skills relacionadas

- `corpus-segmentacion`: produce el `texto` canónico e `inicio_cuerpo` sobre los que operan las reglas.
- `integridad-congelacion`: mecánica de `make congelar`, etiquetas git y qué hacer tras `reglas-congeladas`.
- `gold-anotacion`: se abre únicamente después de la etiqueta; comparte convenciones de span (PRD §3.6).
- `fusion-normalizacion`: consume las `Entidad` con `fuente` y `en_marca` para fusionar con el NER (D12).
- `evaluacion-ie`: usa la procedencia `marca` y `06_colisiones_reglas.csv` para la categoría de errores por mayúsculas.
