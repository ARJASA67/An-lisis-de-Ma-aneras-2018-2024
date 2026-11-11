# Verificación técnica del NER (P06) · `mrm8488/bert-spanish-cased-finetuned-ner`

Fecha: 2026-11-11 12:59. Revisión fija: `b11721d41d9e948da32fcdabeeef4fb0f3ebcdf7`. Sin gold: ejemplos de desarrollo sintéticos.

| Comprobación | Resultado | Detalle |
|---|---|---|
| Pesos con cabeza de clasificación de tokens | sí | BertForTokenClassification |
| Tokenizador rápido (`is_fast`) | sí | BertTokenizer |
| Devuelve `offset_mapping` | sí |  |
| Invariante `texto[inicio:fin] == texto_entidad` en ejemplos | sí |  |
| Texto largo fragmentado en varias ventanas | sí | 9 ventanas |

- `id2label`: {"0": "B-LOC", "1": "B-MISC", "2": "B-ORG", "3": "B-PER", "4": "I-LOC", "5": "I-MISC", "6": "I-ORG", "7": "I-PER", "8": "O"}
- Etiquetas base: LOC, MISC, ORG, PER. Mapeadas: LOC, ORG, PER; descartadas y contadas: MISC.
- `max_position_embeddings` = 512; tokens especiales = 2; límite por ventana con margen = 494 subtokens; solapamiento = 64.
- Entorno: Python 3.11.18, transformers 5.22.1, torch 2.15.0+cpu, Windows AMD64, solo CPU.
- Carga del pipeline: 8.5 s; memoria pico 270 → 825 MB (+555 MB).

## Ejemplos de desarrollo (sintéticos)

> El presidente Andrés Manuel López Obrador se reunió con directivos de Pemex en Dos Bocas, Tabasco.

- PER «Andrés Manuel López Obrador» (1.00); ORG «Pemex» (0.83); LOC «Dos Bocas» (1.00); LOC «Tabasco» (0.99)
- Uniones interpalabra: 0; descartes: 0

> La Secretaría de Salud y el IMSS informaron que Jorge Alcocer Varela visitará Oaxaca.

- ORG «Secretaría de Salud» (1.00); ORG «IMSS» (0.96); PER «Jorge Alcocer Varela» (1.00); LOC «Oaxaca» (1.00)
- Uniones interpalabra: 0; descartes: 0

> SECRETARIO DE SALUD, JORGE ALCOCER VARELA: Buenos días. Hoy hablaremos de la vacuna.

- sin entidades
- Uniones interpalabra: 0; descartes: 0

> En Washington, el Banco Mundial y la Comisión Federal de Electricidad firmaron un acuerdo.

- LOC «Washington» (0.92); ORG «Banco Mundial» (1.00); ORG «Comisión Federal de Electricidad» (1.00)
- Uniones interpalabra: 0; descartes: 0

**Resultado: APTO** como NER del proyecto.
