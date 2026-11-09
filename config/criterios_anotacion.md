# Criterios de anotación de entidades

Aplican al gold, al conjunto de selección y al extractor. Se fijan antes de anotar y no cambian después.

## Offsets

Los offsets son índices de carácter Python sobre el `texto` completo del pasaje, con la marca de interlocutor incluida. `inicio` es inclusivo y `fin` exclusivo, y `texto[inicio:fin]` es exactamente la entidad. No hay espacios al inicio ni al final.

## Tipos

| Tipo | Qué se anota | Convenciones |
| --- | --- | --- |
| PER | Nombres de funcionarios, empresarios y periodistas | Nombre completo presente en el texto, como una sola entidad. Se excluye el cargo adyacente: `secretario de Salud, Jorge Alcocer Varela` → `Jorge Alcocer Varela`. |
| ORG | Dependencias, empresas, partidos, organismos internacionales y organizaciones empresariales | Nombre o sigla tal como aparece. Las farmacéuticas y las marcas de vacuna son ORG. Si la organización contiene un lugar, se anota completa y sin LOC interno: ORG `Secretaría de Salud de Tabasco`. `Salud`, `Bienestar` y `Cultura` sueltas son ORG solo con mayúscula inicial. Una enfermedad (COVID), un impuesto (IEPS) o un término genérico (ONG) no son ORG. |
| LOC | Estados, municipios, países y obras con nombre propio | Tren Maya, AIFA, Dos Bocas y refinería Olmeca son LOC. |
| FECHA | Fechas absolutas y relativas resolubles | Núcleo completo, con el modificador relativo cuando lo hay (`próximo 15 de enero`, `diciembre de 2021`, `15 de diciembre de 2023`) y sin preposiciones ni artículos introductorios. `en 2019` es `2019` con precisión de año. Un número de cuatro cifras sin contexto temporal no es FECHA. Un intervalo explícito (`del 1 al 15 de enero`) es una sola entidad; una enumeración produce entidades separadas. |
| MONTO | Cantidades de dinero en pesos o dólares con su unidad | Incluye cifra, escala y moneda o símbolo (`20 mil millones de pesos`, `$1,200 millones`). No se recorta el `$`. Porcentajes, dosis, litros y elementos no son MONTO. |

## Marca de interlocutor

Las entidades dentro de la marca se anotan igual que en el cuerpo: `SECRETARIO DE SALUD, JORGE ALCOCER VARELA:` contiene la PER `JORGE ALCOCER VARELA`. `PREGUNTA`, `INTERLOCUTOR`, `INTERLOCUTORA` y las demás marcas genéricas no contienen entidades.

El cargo de la marca es un cargo, no una organización: no se anota ORG ni LOC dentro de él (`SECRETARIO DE SALUD`, `DIRECTOR GENERAL DEL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS)`). El nombre de la persona, con o sin cargo, es PER.

## Spans que se solapan

Spans que no se contienen pueden coexistir. Cualquier excepción se escribe en esta guía antes de cerrar el gold.
