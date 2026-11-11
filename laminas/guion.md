# Guion de la presentación (8 minutos: unos 5 de exposición, 2 de demo y 1 de margen)

Cinco láminas 16:9, patrón concepto a la izquierda (40 %) y artefacto real a la derecha (60 %).
Pie de cada lámina: «Arturo Jaramillo Salmerón · Minería de Textos · N/5». Toda cifra sale de
`salida/` y coincide con `reporte/reporte.md`.

Ensayo registrado: pendiente (Arturo mide con cronómetro y anota aquí «Ensayo 2026-11-11: X min YY s»).
Demo medida: `13_demo.py --q Q3` 0.5 s con artefactos; consulta libre 4.2 s (carga del índice 1.8 s).

## Lámina 1 · Problema y corpus (1 min)

Izquierda:
- 2,294 versiones estenográficas, 2018 a 2024; 10 consultas.
- Limpieza por lista cerrada: 7,338 acotaciones (0.12 % de los caracteres), 5 discursos duplicados, 10 fechas reparadas.
- Unidad de recuperación: pasajes de 200 palabras, paso de 150; 127,739 pasajes.
- Pipeline: corpus → índice → TF-IDF y BM25 → juicios → reglas + NER → gold → tablas con evidencia.

Derecha: tabla 1 del reporte (`reporte/tablas/corpus.md`).

Qué decir: el formato real de las marcas no era el del kit (0 de 2,294 reconocidas), por eso se
canonizan antes de segmentar. Transición: «con los pasajes listos, el índice».

## Lámina 2 · Segmentación e índice (1 min)

Izquierda:
- La marca del interlocutor se conserva en el pasaje pero no entra al índice.
- Costo: el 64.9 % de las intervenciones de reporteros queda bajo 40 palabras.
- Stoplist de 336 palabras (24 propias de la estenográfica), stemming Snowball.

Derecha: tabla 2 del reporte, postings de tren, vacuna, refinería y huachicol (`salida/02_postings.md`).

Qué señalar: huachicol tiene df = 714 e idf BM25 = 5.19, el más alto de los cuatro; tren, con
df = 5,261, pesa menos. Transición: «con ese índice comparamos dos modelos».

## Lámina 3 · Recuperación: TF-IDF frente a BM25 (1.5 min)

Izquierda:
- BM25 con filtro: MAP 0.575; TF-IDF con filtro: 0.385 (176 juicios humanos).
- BM25 gana en 8 de 10 consultas; TF-IDF gana Q3; Q9 empata en su techo de 10/21 = 0.476.
- El filtro pesa más en Q6: AP de BM25 de 0.189 a 0.449.
- Consulta difícil: Q3 (Dos Bocas); hipótesis sin probar, el término «dos».

Derecha: `reporte/figuras/ir_ap_por_consulta.png` y tabla 3 del reporte.

Transición: «el mejor modelo, BM25 con filtro, alimenta la extracción».

## Lámina 4 · Extracción: reglas más modelo (1.5 min)

Izquierda:
- Reglas: FECHA, MONTO, gazetteers ORG y LOC, regla de marca para PER. Congeladas antes del gold.
- NER mrm8488/bert-spanish-cased-finetuned-ner, elegido por criterio técnico, sin ver el gold.
- Fusión por span exacto. F1 combinado 0.774; reglas 0.587; modelo 0.708.
- Errores reales: frontera 38 (aeropuerto Felipe Ángeles → Felipe Ángeles), mayúsculas en la marca (MAN, MANUEL LÓPEZ), sigla UMAS.

Derecha: tabla 5 del reporte (P / R / F1 por tipo y método) o `reporte/figuras/ie_f1_por_tipo_metodo.png`.

Transición: «con las entidades armamos respuestas, y aquí está la demo».

## Lámina 5 · Demo y limitaciones (1 min más la demo)

Izquierda:
- Respuestas solo «respaldadas» si el texto muestra la relación pedida; lo que dice un reportero queda ambiguo.
- Limitaciones: gold de 20 pasajes, un solo NER, preguntas cortas perdidas, juicios sin acuerdo medido.

Derecha: extracto de `salida/tablas_respuesta/Q3.md` y el comando de la demo.

## Demo (2 min)

Comando: `.venv/Scripts/python.exe scripts/13_demo.py --q Q3` (con `PYTHONUTF8=1`).

Orden de lo que se comenta:
1. Panel 1: consulta, ventana y modelo fijado.
2. Top-10 lado a lado: cuántos pasajes comparten TF-IDF y BM25 (la línea «Pasajes en ambos top-10»).
3. Tres pasajes con entidades coloreadas: gris la marca, subrayado lo que dio el modelo.
4. Tabla de respuesta de Q3: un valor respaldado y uno ambiguo, con su cita.
5. Si sobra tiempo, consulta libre: `--consulta "robo de combustible en ductos" --desde 2018-12-01 --hasta 2019-06-30`, aclarando que no tiene métricas ni NER en caliente.

Contingencia: `laminas/demo_Q3_salida_guardada.txt`, que se anuncia como salida guardada y no como demo en vivo.

## Preguntas probables

| Pregunta | Respuesta preparada | Evidencia |
| --- | --- | --- |
| ¿Por qué pasajes y no discursos? ¿Por qué 200 palabras? | Un discurso mezcla muchos temas; 200 palabras con paso de 150 dan contexto suficiente y solapamiento para no cortar ideas. El costo son las preguntas cortas. | Reporte sección 1, `salida/01_limpieza.json` |
| ¿Qué ruido limpiaste y cuánto? | Solo acotaciones de una lista cerrada, 7,338 (0.12 % de los caracteres); las siglas entre paréntesis se conservan. | `salida/01_limpieza.json` |
| ¿Por qué la marca no entra al índice? | Porque el nombre del presidente aparecería en casi todos los pasajes y sesgaría el ranking; sí se usa para PER. | Reporte sección 2 |
| ¿Por qué huachicol tiene idf alto? | Aparece en 714 de 127,739 pasajes: es raro y discrimina. | `salida/02_postings.md` |
| ¿Por qué tu BM25 no coincide con rank_bm25? | rank_bm25 usa ln((N−df+0.5)/(df+0.5)) con un piso; el sistema suma 1 dentro del logaritmo y el idf siempre es positivo. | Reporte sección 3 |
| ¿Consulta más difícil? | Q3 para BM25 (0.249); hipótesis sin probar: «dos» funciona como número. | `salida/05_ir_ganador_por_consulta.csv` |
| ¿Qué cambia con el filtro? | Quita pasajes fuera de la ventana; en Q6 sube el AP de BM25 de 0.189 a 0.449. La relevancia se juzgó por tema, sin fecha. | Tabla 3 y 4 del reporte |
| ¿Cómo evitaste usar el gold para elegir el NER o ajustar reglas? | Reglas congeladas con etiqueta git antes del gold; NER fijado por criterio técnico antes del sorteo; sin cambios después. | `docs/decisiones.md`, `data/modelo_ner.json` |
| ¿Qué entidad falló más? | Por frontera, LOC y PER; PER del modelo se rompe en la marca en mayúsculas. | `salida/09_resumen_errores.csv` |
| ¿Qué respuestas tienen evidencia? | Tabla 7 del reporte; sin evidencia: montos del Tren Maya, fechas de aumento de la pensión y organizaciones empresariales de Q8. | `salida/respuestas.csv` |
| ¿Qué mejoraría con embeddings densos? | Sinónimos: huachicol y robo de combustible, AIFA y Felipe Ángeles (Q6, Q4). | Reporte sección 3 |
