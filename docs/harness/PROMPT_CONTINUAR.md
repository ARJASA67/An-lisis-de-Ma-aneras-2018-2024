Continúo mi Examen 1 de Minería de Textos (UNAM FES Acatlán). El repo está en C:\Ciencias\Textos\text-mining-ir-er; lo inició el profesor y yo, Arturo Jaramillo Salmerón, lo continúo individualmente por indicación suya.

Antes de tocar nada:
1. Usa la skill `session-resume` y lee completo docs/harness/PROGRESS.md (secciones "Pendiente" y "Entorno").
2. Lee CLAUDE.md y la skill `integridad-congelacion`.

Estado: H0 a H8 cerrados. H9 casi cerrado: reporte final en mi formato de prácticas (reporte/reporte.pdf y .docx, 8 páginas: portada, índice y 6 de cuerpo, letra 10 e interlineado 1.0 por decisión mía), README de 10 secciones, requirements.txt, demo scripts/13_demo.py, láminas laminas/laminas.pptx (las edito yo) y guía de defensa. Todo comprometido en local; ya hice push de una versión anterior.

Lo único pendiente:
1. Yo escribo anotaciones/valoraciones.yaml (claves Q1 a Q10, cada una con `texto` de 2 a 3 líneas y `tabla_sha256` copiado de salida/10_tablas_hash.json). Tú NO las redactas ni sugieres: solo validas el formato con respuestas.validar_valoraciones().
2. Cuando estén: regenera el reporte con scripts/11b_reporte_practica.py y confirma que el cuerpo siga en 6 páginas (revisa las páginas como imagen). Necesita:
   - PATH con "C:\Program Files\nodejs" y "C:\Users\arjas\AppData\Local\Pandoc"
   - NODE_PATH apuntando al node_modules donde está el paquete `docx` (si no existe, `npm install docx` en una carpeta temporal fuera del repo)
   - --skill con la ruta de la skill practicas-arturo y --python python (el Python del sistema tiene pygments y Pillow); Word hace el PDF.
3. Commit con data(valoraciones) y docs(reporte), registra en docs/decisiones.md y crea la etiqueta local v1.0-entrega con la hora real.

Reglas de trabajo:
- Windows sin make. Corre todo con .venv/Scripts/python.exe y PYTHONUTF8=1.
- No cambies los saltos de línea (eol=lf).
- Tú haces commits locales; yo hago el push con `git push github main` y `git push github v1.0-entrega`. Nunca hagas push a origin (es el GitLab del profesor).
- Los juicios, el gold y las valoraciones son trabajo mío; no los escribas ni los sugieras.
- Plazo: hoy, 11 de noviembre de 2026 a las 20:00.
