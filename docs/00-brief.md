# Brief de producto (origen: David, 2026-06-12)

> Documento fuente escrito por el usuario. Es la referencia canónica de la visión.
> Los demás documentos de `docs/` derivan de este.

## Resumen

SharedBrain es una **capa de contexto personal para agentes de IA**: un embudo
contextual que toma conocimiento personal en bruto (vault de Obsidian, repos de
proyectos), lo destila y lo convierte en contexto accionable para pensar,
decidir y ejecutar con agentes.

**Problema que resuelve:** el bloqueo por exceso de posibilidades. Con agentes
se puede construir casi cualquier cosa; el cuello de botella es decidir qué
merece la pena hacer, priorizarlo y convertir intuiciones en propuestas
ejecutables.

## Principios de diseño (no negociables)

1. **Personal-first, no SaaS.** Auto-hosteable, open source, claves de API
   propias, modelos configurables, agnóstico de agente.
2. **Separación humano / IA.** Los agentes leen las notas humanas pero nunca
   las modifican. Todo lo generado por IA vive en una zona propia y queda
   marcado como tal. Trazabilidad: escrito por humano / generado por IA /
   validado.
3. **Validación explícita para lo sensible.** Cambios sobre identidad,
   valores, objetivos o decisiones personales requieren confirmación del
   usuario.
4. **Calidad sobre cantidad.** Cada pieza de contexto generada debe servir
   para decidir, ejecutar, recordar una preferencia, reducir fricción,
   mejorar una idea o detectar un riesgo. Si no, es ruido y no se genera.
5. **No exige notas perfectas.** El contexto de entrada puede ser desordenado,
   incompleto o contradictorio; el sistema destila, no impone estructura.

## Caso de uso del MVP

**Generar, evaluar, criticar, mejorar y priorizar ideas de proyectos a partir
del contexto personal.** Incluye trabajar sobre ideas existentes: reducir
alcance, ampliar, reformular para distintos objetivos (monetización, marca
personal, educación, investigación, proyectos cortos/largos) y convertirlas
en propuestas accionables con descripción, encaje personal, impacto,
dificultad, MVP mínimo, riesgos, puntos ciegos y criterios de decisión.

## Capas de conocimiento

1. **Notas humanas** — solo lectura para agentes.
2. **Notas generadas por IA** — zona de escritura de agentes, etiquetada.
3. **Contexto accionable** — subconjunto filtrado para una tarea concreta
   (paquetes de contexto).
4. **Contexto de proyecto** — estado, decisiones, roadmap, issues,
   instrucciones para agentes, derivado de notas + repositorio.

## Alcance del MVP

- Leer un vault de Obsidian.
- Separación clara humano / IA.
- Perfil personal inferido (revisable y corregible).
- Generación, evaluación y crítica de ideas de proyectos.
- Ideas y análisis guardados como Markdown.
- Paquetes de contexto para tareas concretas.
- Contexto básico de repositorios de software.
- Servidor MCP para exponer todo a cualquier agente.
- Configuración de modelos y claves por el usuario.
- Auto-hosteable.

**Fuera del MVP:** email, Telegram, WhatsApp, Discord, Slack, calendario,
videollamadas, transcripciones.

## Visión futura

Más fuentes de contexto (mensajes, correos, reuniones, documentos),
integración con sistemas de memoria para agentes. Meta final: un **sistema
operativo contextual personal** que ayude a pensar, priorizar, decidir y
ejecutar — no solo a recordar.
