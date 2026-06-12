# MVP — alcance y plan de construcción

## Criterio de éxito del MVP

El MVP está validado cuando ocurre este flujo completo, de verdad, con el
vault real:

1. `sharedbrain profile infer` produce un perfil que el usuario lee y dice
   "sí, esto soy yo" (con correcciones menores).
2. `sharedbrain ideas generate --goal educación --horizon corto` produce 5
   fichas de idea de las que **al menos una** el usuario querría empezar.
3. `sharedbrain ideas critique <slug>` añade una crítica que cambia la
   decisión del usuario sobre al menos una idea (la mejora, la reduce o la
   descarta con argumentos).
4. Un agente externo (Claude Code) conectado por MCP responde con solvencia
   a "¿qué proyecto debería priorizar este mes y por qué?" usando solo las
   tools de SharedBrain.

Si el paso 2 produce ideas genéricas que podrían ser de cualquiera, el MVP
ha fallado aunque el código funcione. La calidad del embudo contextual es el
producto.

## Comandos de la CLI

```
sharedbrain init                      # crea _ai/ en el vault, config inicial
sharedbrain profile infer             # infiere/propone perfil desde las notas
sharedbrain ideas generate [--goal --horizon --from <nota> --n 5]
sharedbrain ideas critique <slug>     # sparring: crítica constructiva
sharedbrain ideas compare <slug...>   # comparación y ranking razonado
sharedbrain ideas list [--verdict --goal]
sharedbrain pack create "<descripción de la tarea>"
sharedbrain ideas promote <slug>      # idea → proyecto (specs en _ai/projects/)
sharedbrain project sync <path|url>   # contexto de repo → _ai/projects/
sharedbrain serve                     # MCP stdio
sharedbrain serve --web               # FastAPI: panel + API + MCP HTTP
```

## Orden de construcción

Cada fase termina en algo usable con el vault real — no hay fase "solo
infraestructura".

### Fase 1 — Sustrato + lectura (1ª semana de uso real)
- Config (`sharedbrain.config.yaml`), `init`, layout `_ai/`.
- Lectura del vault: parsing de Markdown + frontmatter, índice en memoria.
- Búsqueda léxica.
- **Servidor MCP solo-lectura:** `search_context`, `read_note`.
- ✅ Usable: Claude Code ya puede explorar el vault con permisos seguros.

### Fase 2 — Perfil + escritura controlada
- Escritura en `_ai/` con enforcement de paths y frontmatter inyectado.
- Tools MCP de escritura: `create_ai_note`, `update_ai_note`.
- Pipeline `profile infer`: selección de notas relevantes → inferencia →
  `_ai/profile/*.md` como `draft` con `confidence` y `sources`.
- Ciclo de validación (status) y regla de no-sobreescritura de perfil validado.
- ✅ Usable: perfil revisable en Obsidian; agentes con `get_profile`.

### Fase 3 — Ideas (el corazón)
- Ficha de idea (plantilla con secciones fijas) y `upsert_idea`.
- `ideas generate`: perfil validado + notas relevantes al criterio → N fichas.
- `ideas critique`: crítica añadida a la ficha (tamaño, vaguedad,
  alternativas existentes, esfuerzo/impacto, ventaja real, supuestos a
  validar, primera comprobación barata).
- `ideas compare` y `ideas list`.
- ✅ Usable: el caso de uso principal del MVP completo.

### Fase 4 — Paquetes + proyectos
- `pack create`: dado un objetivo de tarea, seleccionar perfil + notas +
  ideas + contexto de proyecto relevantes y compilar un Markdown
  autocontenido en `_ai/packs/`.
- `project sync`: extracción local de contexto de repo (README, estructura,
  git log, issues vía `gh`) → `_ai/projects/<slug>/`.
- Tools MCP: `get_pack`, `list_packs`, `list_ideas`, `get_project_context`,
  `upsert_idea`, `update_project_context`.
- ✅ Núcleo completo → ejecutar el criterio de éxito antes de seguir.

### Fase 5 — Panel web (React + Vite)
- API FastAPI sobre los mismos servicios (vault, ideas, proyectos, packs);
  FastMCP montado en la misma app (MCP por HTTP además de stdio).
- Frontend React + Vite + TS: vista de proyectos (estado, stack, objetivo),
  vista de ideas filtrable por metadatos, visor de paquetes de contexto.
- **Promoción idea → proyecto** (`ideas promote` y botón en el panel):
  genera `_ai/projects/<slug>/` (context.md, roadmap.md, agentes.md) a partir
  de la ficha de idea, listo para entregar a un agente como paquete de
  contexto o brief copiable.
- Registro de ejecuciones de pipelines en SQLite y vista de actividad.
- ✅ Panel de control: seguir proyectos, estado y contexto sin la CLI.

El panel es deliberadamente la última fase: el riesgo principal es que la UI
se coma al embudo contextual. El seguimiento *en vivo* de tareas de agentes
externos queda post-MVP.

## Riesgos del propio MVP (auto-crítica)

| Riesgo | Mitigación |
|---|---|
| Ideas genéricas, no personales | El pipeline de ideas **siempre** ancla en perfil validado + notas citadas en `sources`; si no encuentra anclaje, lo dice en vez de inventar. |
| Basura contextual (el riesgo que el brief señala) | Regla dura: ningún pipeline escribe un archivo que no pase el filtro "¿ayuda a decidir/ejecutar/recordar/desbloquear?"; salidas dudosas van a `inbox/`, no a las zonas curadas. |
| Sobre-ingeniería antes de validar | Sin BD, sin embeddings, sin watchers, sin UI web, sin multiusuario. Todo eso es post-MVP explícito. |
| Perfil inferido erróneo que contamina todo | `confidence` + `sources` por afirmación; el perfil draft no alimenta generación de ideas hasta ser revisado. |
| Coste/latencia de leer vaults grandes | Selección de notas en dos pasos: búsqueda léxica barata → solo las top-K notas van al LLM. Modelo `cheap` para resúmenes intermedios. |

## Post-MVP (orden tentativo)

1. Seguimiento en vivo de tareas de agentes externos en el panel.
2. Búsqueda semántica (embeddings locales u hospedados, configurable).
3. Sync de proyectos disparado por git hook / CI.
4. Detección de cambios en notas ("hay material nuevo para destilar").
5. Revisión periódica guiada de identidad/objetivos.
6. Más fuentes (correo, mensajería, transcripciones) — solo si el núcleo
   demostró valor.
7. Auth para el servidor HTTP en uso remoto/multi-dispositivo.
