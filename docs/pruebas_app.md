# Prueba manual de la app de anotación

Diez pasos que el alumno recorre una vez (PRD §7). Los pasos 6, 7, 9 y 10 dependen de pestañas que
se construyen en H5 y H6; hoy solo se puede recorrer del 1 al 5 y el 8. Para no ensuciar
`anotaciones/` con datos de prueba, haz el recorrido antes del primer juicio real o en un clon.

| # | Acción | Resultado esperado | Disponible |
| --- | --- | --- | --- |
| 1 | `make app` | Abre el navegador con las pestañas Estado y Juicios, sin red y sin cargar el modelo NER. | Ahora |
| 2 | Abrir Estado | Ningún artefacto aparece como "válido" solo por existir; sin `config/criterios_relevancia.md` los criterios y los juicios salen "pendiente humano". | Ahora |
| 3 | En Juicios (con criterios escritos), pulsar Relevante, Omitir, No relevante y Anterior | Cada clic guarda al instante en `anotaciones/juicios_relevancia.csv`; el omitido queda vacío, no 0. | Ahora |
| 4 | Cerrar la pestaña y reabrir | Retoma en el primer pasaje pendiente con el mismo conteo; el omitido sigue pendiente. | Ahora |
| 5 | Abrir la app en dos pestañas, juzgar en una y luego en la otra | La segunda muestra "editado desde otra pestaña: recarga antes de guardar" y no escribe. "Recargar desde disco" lo resuelve. | Ahora |
| 6 | En Gold, buscar un texto que aparece dos veces | Muestra cada aparición con 40 caracteres de contexto para elegir cuál. | H6 |
| 7 | En Gold, selección por tokens sobre un monto con `$` | Con "recortar puntuación final" activada el `$` se conserva. | H6 |
| 8 | En Juicios, revisar que no aparezcan puntajes, rangos ni modelo | Solo consulta, pregunta, pasaje con resaltado, `doc_id`, título, interlocutor y fecha. | Ahora |
| 9 | En Gazetteer, aceptar, corregir y descartar una sigla | Escribe `config/gazetteer_extendido.csv`; tras `reglas-congeladas` avisa y bloquea. | H5 |
| 10 | En Gold, agregar un duplicado y cerrar el gold | El duplicado se rechaza con error visible; el cierre solo funciona si `validar_gold()` pasa y escribe `cierre_gold.json`. | H6 |

Alternativa sin Streamlit: `make app-cli` ofrece los mismos juicios (1, 0, o, a, s) con la misma
persistencia y el mismo gate de criterios.
