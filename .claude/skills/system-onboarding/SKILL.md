---
name: system-onboarding
description: "Usa esta skill cuando seas un agente nuevo en este sistema y necesites entenderlo para hacer bugfixing o mantenimiento. Punto de entrada obligatorio antes de tocar código en un bug no trivial."
---

# Entender el sistema para hacer bugfixing

## Antes de tocar código

1. Lee `docs/harness/ARCHITECTURE.md` completo: componentes, flujos de datos,
   decisiones clave heredadas del PRD original.
2. Si el bug involucra un componente que `docs/harness/ARCHITECTURE.md` no cubre o
   describe de forma que ya no coincide con el código, actualízalo como parte
   de tu trabajo — no dejes que se desalinee más.
3. Usa `session-resume` para saber si alguien más ya investigó este bug o uno
   relacionado.

## Flujo de debugging

1. Reproduce el bug antes de proponer una causa. Si no puedes reproducirlo,
   dilo explícitamente en vez de adivinar.
2. Ubica el componente responsable usando `docs/harness/ARCHITECTURE.md` como mapa,
   no explorando el repo a ciegas.
3. Formula una hipótesis de causa raíz falsable, no un parche que hace
   desaparecer el síntoma.
4. Verifica la hipótesis (logs, test que reproduzca el bug, lectura del código
   señalado) antes de tocar nada.
5. Corrige la causa raíz. Si el fix toca un área no cubierta por
   `docs/harness/ARCHITECTURE.md`, agrégala.
6. Deja evidencia de que el fix funciona (test que antes fallaba y ahora
   pasa, o el paso de reproducción manual que ya no reproduce el bug).
