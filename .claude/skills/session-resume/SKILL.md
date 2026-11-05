---
name: session-resume
description: "Usa esta skill al empezar una sesión de trabajo (para saber en qué quedó el sistema) y al cerrarla (para dejar el estado actualizado). Lee y escribe docs/harness/PROGRESS.md."
---

# Retomar trabajo entre sesiones

## Al empezar una sesión

1. Lee `docs/harness/PROGRESS.md` completo antes de tocar código.
2. Si no existe, créalo con la plantilla de abajo — es la primera sesión.
3. Resume en 2-3 líneas al usuario: qué se completó, qué falta, y cualquier
   bloqueo o decisión pendiente que encuentres en el archivo.

## Al cerrar una sesión (o terminar una tarea grande)

Actualiza `docs/harness/PROGRESS.md` con:

- **Completado**: qué se terminó en esta sesión (lista corta, no un changelog).
- **Pendiente**: qué sigue, en el orden en que se debería abordar.
- **Decisiones**: cualquier decisión de diseño tomada que no sea obvia desde
  el código (y por qué).
- **Bloqueos**: cualquier cosa que impidió avanzar (falta de acceso, pregunta
  sin responder del usuario, dependencia externa).

No dupliques aquí lo que ya está en git log o en el plan de implementación —
solo lo que esos dos no capturan: contexto, decisiones, bloqueos.

## Plantilla inicial de `docs/harness/PROGRESS.md`

```markdown
# Progreso — Sistema de recuperación y extracción de información sobre discursos presidenciales

## Completado

(nada aún)

## Pendiente

- Ver PRD / implementation plan inicial

## Decisiones

(ninguna aún)

## Bloqueos

(ninguno)
```
