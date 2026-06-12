# Arquitectura

## Idea central

SharedBrain se divide en dos planos que comparten un mismo sustrato (el vault):

```
┌──────────────────────────────┐  ┌───────────────────────┐
│  Agentes externos            │  │  Panel web (React)    │
│  (Claude Code, otros, ...)   │  │  proyectos · estado · │
│                              │  │  contexto · acciones  │
└──────────────┬───────────────┘  └───────────┬───────────┘
               │ MCP (stdio / HTTP)           │ API HTTP (FastAPI)
┌──────────────▼──────────────────────────────▼────────────┐
│  PLANO PASIVO — Servidor (FastAPI + FastMCP, 1 proceso)  │
│  · búsqueda y lectura de contexto                        │
│  · escritura controlada en la zona IA                    │
│  · enforcement de permisos (humano = solo lectura)       │
└────────────────────────┬────────────────────────────────┘
                         │ filesystem (Markdown + frontmatter)
┌────────────────────────▼────────────────────────────────┐
│  SUSTRATO — Vault de Obsidian                            │
│  · notas humanas (cualquier estructura, sin requisitos)  │
│  · zona IA: _ai/ (perfil, ideas, proyectos, paquetes)    │
└────────────────────────▲────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│  PLANO ACTIVO — Pipelines de destilación (CLI)           │
│  · inferir perfil · generar/criticar ideas               │
│  · construir paquetes de contexto                        │
│  · extraer contexto de repositorios                      │
│  · usa el LLM que configure el usuario                   │
└──────────────────────────────────────────────────────────┘
```

**Plano pasivo (servidor MCP + API web):** no llama a ningún LLM. Es la API de
contexto: cualquier agente puede buscar, leer y escribir (solo en la zona IA).
Es lo que hace a SharedBrain agnóstico de agente — el agente pone la
inteligencia, el servidor pone el contexto y las reglas. El servidor MCP
(FastMCP) se monta dentro de la misma app FastAPI que sirve la API del panel
web: un solo proceso, una sola fuente de verdad.

**Plano activo (CLI de pipelines):** sí llama a LLMs (configurables por el
usuario). Ejecuta los trabajos de destilación: inferir el perfil, generar y
criticar ideas, construir paquetes de contexto, resumir el estado de un repo.
Sus salidas son siempre archivos Markdown en la zona IA.

Esta separación evita el acoplamiento más peligroso: un agente potente (p. ej.
Claude Code conectado por MCP) puede hacer él mismo la generación de ideas
usando las tools de lectura/escritura, sin que SharedBrain gaste tokens; y un
usuario sin agente puede obtener lo mismo con `sharedbrain ideas generate`.

## Sustrato: archivos como base de datos

El **conocimiento** vive siempre como Markdown con frontmatter YAML dentro del
vault — el vault es la única fuente de verdad y el panel web *lee del vault*,
lo que garantiza que CLI, MCP y web nunca divergen. Para **estado operativo**
que no es conocimiento (ejecuciones de pipelines, actividad de agentes,
estados efímeros del panel) se usa **SQLite** cuando haga falta; nunca para
notas, ideas, perfil ni contexto. Consecuencias deliberadas:

- Todo es visible y editable desde Obsidian (validar una inferencia = editar
  una línea de frontmatter).
- Sincronización, backup y versionado los resuelve el usuario como ya hace
  con su vault (git, Obsidian Sync, Syncthing...).
- La trazabilidad humano/IA se materializa en la estructura de carpetas y el
  frontmatter, no en una tabla.

Búsqueda en el MVP: léxica (ripgrep sobre el vault + match de frontmatter).
Embeddings/búsqueda semántica quedan para post-MVP; con vaults personales
(<10k notas) la búsqueda léxica bien hecha cubre el 90 % de los casos y no
añade infraestructura.

## Layout del vault

La zona IA vive **dentro** del vault, en `_ai/`, para que sea navegable desde
Obsidian. Las notas humanas son todo lo demás — sin requisitos de estructura.

```
vault/
├── ... (notas humanas, cualquier estructura)        ← solo lectura
└── _ai/                                             ← zona de escritura IA
    ├── profile/
    │   ├── identidad.md          # quién es, habilidades, intereses
    │   ├── objetivos.md          # metas declaradas e inferidas
    │   ├── valores.md            # valores y restricciones
    │   └── patrones.md           # patrones detectados en ideas/proyectos
    ├── ideas/
    │   └── <slug>.md             # una idea por archivo (ficha completa)
    ├── projects/
    │   └── <slug>/
    │       ├── context.md        # descripción, estado, objetivo actual
    │       ├── roadmap.md
    │       ├── decisiones.md
    │       └── agentes.md        # instrucciones para agentes
    ├── packs/
    │   └── <slug>.md             # paquetes de contexto autocontenidos
    └── inbox/
        └── ...                   # salidas IA sin clasificar / borradores
```

## Esquema de frontmatter

Campos comunes a todo archivo de `_ai/`:

```yaml
---
origin: ai                    # ai | human (las notas humanas no lo necesitan)
type: inference | idea | critique | project-context | pack | note
status: draft | reviewed | validated | rejected
created: 2026-06-12
updated: 2026-06-12
model: claude-fable-5         # qué modelo lo generó
sources:                      # trazabilidad: de qué notas/repos se deriva
  - "Notas/proyectos/idea-x.md"
  - "repo:github.com/user/proyecto#main@abc123"
confidence: high | medium | low   # solo para inferencias
---
```

Campos adicionales para `type: idea`:

```yaml
goal: monetización | marca-personal | educación | investigación | aprendizaje
horizon: corto | medio | largo
effort: 1-5
impact: 1-5
fit: 1-5                      # encaje con perfil
verdict: hacer | reducir | aparcar | descartar | sin-evaluar
```

**Ciclo de validación:** todo nace `draft`. El usuario lo revisa y cambia
`status` a `validated` (o lo edita, o lo mueve a su zona humana, o lo marca
`rejected`). Los pipelines tratan el contenido `validated` con más peso que
el `draft` al construir contexto. El perfil (`profile/`) nunca se sobreescribe
automáticamente si está `validated`: el pipeline genera una propuesta de
actualización en `inbox/` y el usuario decide.

## Ficha de idea (el artefacto central del MVP)

Cada idea es un archivo con secciones fijas — es el contrato entre generación,
crítica y priorización:

```markdown
# <Título>

## Descripción            ## Problema que resuelve
## Por qué encaja conmigo ## Público objetivo
## Impacto posible        ## Dificultad estimada
## MVP mínimo             ## Riesgos principales
## Puntos ciegos          ## Cómo reducirla
## Cómo ampliarla         ## Outputs posibles
## Criterios de decisión  ## Crítica          ← la añade el pipeline de crítica
## Veredicto              ← lo decide el usuario (o propone el sistema)
```

La crítica se **añade a la misma ficha** (sección `## Crítica`), no a un
archivo aparte: una idea y su evaluación viajan juntas.

## Permisos (enforcement, no convención)

El servidor MCP es quien garantiza las reglas; no se confía en que el agente
se porte bien:

| Zona                  | Agente (vía MCP) | Pipelines (CLI) | Usuario |
|-----------------------|------------------|-----------------|---------|
| Notas humanas         | lectura          | lectura         | todo    |
| `_ai/` (general)      | lectura+escritura| lectura+escritura| todo   |
| `_ai/profile/` validado | lectura        | propone en inbox | todo   |

Toda escritura por MCP: (1) se restringe por path a `_ai/`, (2) inyecta
`origin: ai` y el resto de frontmatter aunque el agente no lo envíe, (3) se
registra en un log de escrituras (`_ai/.log/`).

## Superficie MCP (tools del MVP)

Lectura:
- `search_context(query, scope?, type?)` — búsqueda en vault (humano + IA).
- `read_note(path)` — leer una nota concreta.
- `get_profile(section?)` — perfil personal inferido.
- `get_project_context(project)` — contexto consolidado de un proyecto.
- `get_pack(slug)` / `list_packs()` — paquetes de contexto.
- `list_ideas(filter?)` — ideas con sus metadatos (goal, effort, verdict...).

Escritura (solo `_ai/`):
- `create_ai_note(path, content, frontmatter)` — crear nota IA.
- `update_ai_note(path, content)` — actualizar nota IA existente.
- `upsert_idea(slug, fields)` — crear/actualizar ficha de idea (valida secciones).
- `update_project_context(project, section, content)`

Tareas (puentes hacia el plano activo, opcionales en el MVP):
- `request_pack(task_description)` — construir un paquete para una tarea.

## Contexto de repositorios

En el MVP, la extracción de contexto de un repo es **local y bajo demanda**
(`sharedbrain project sync <path-o-url>`): lee README, estructura, commits
recientes, issues (si hay `gh` disponible), y genera/actualiza
`_ai/projects/<slug>/context.md` con el LLM configurado. Sin webhooks ni
watchers en el MVP — el coste de mantenerlos no se justifica hasta validar
el núcleo. Post-MVP: hook de git o acción de CI que dispare el sync.

## Configuración

Archivo `sharedbrain.config.yaml` + variables de entorno para claves:

```yaml
vault: ~/Documentos/MiVault
ai_dir: _ai                # nombre de la zona IA dentro del vault
models:
  default: anthropic:claude-fable-5         # formato pydantic-ai
  cheap: anthropic:claude-haiku-4-5-20251001  # tareas de bajo nivel (resúmenes)
projects:
  - slug: sharedbrain
    repo: ~/Desktop/SharedBrain
```

Las claves de API se leen de variables de entorno estándar
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ...), que es lo que pydantic-ai espera.

## Panel web

El panel es un cliente más de la misma API — no tiene lógica propia de
conocimiento. Funciones:

- **Vista de proyectos:** lista, estado, stack, objetivo actual, roadmap.
- **Vista de ideas:** fichas con sus metadatos (goal, effort, impact, fit,
  verdict), filtrables; acciones sobre la ficha.
- **Promoción idea → proyecto:** un botón que dispara el pipeline de
  promoción: genera las especificaciones iniciales del proyecto
  (`_ai/projects/<slug>/` con context.md, roadmap.md, agentes.md) listas
  para pasárselas a un agente (vía paquete de contexto o copiando el brief).
- **Contexto activo:** visualizar qué paquetes de contexto existen y qué
  contiene cada uno.
- **Actividad:** seguimiento de ejecuciones de pipelines (y, post-MVP,
  tareas de agentes). Respaldado por SQLite.

## Stack

- **Python ≥ 3.12.** Backend, CLI y pipelines en un solo lenguaje.
- **FastAPI** — API HTTP del panel; sirve también el build estático del front.
- **FastMCP** — servidor MCP, montado en la misma app FastAPI (stdio para
  agentes locales, HTTP para remotos).
- **pydantic-ai** — pipelines con LLM: multi-proveedor, claves configurables
  y salidas tipadas (las fichas de idea y el perfil son modelos Pydantic).
- **Typer** — CLI; **python-frontmatter** — parsing de notas.
- **SQLite** — solo estado operativo (ejecuciones, actividad); el
  conocimiento vive en el vault.
- **React + Vite + TypeScript** — frontend del panel desde el principio.
- Distribución: `uv`/`pipx` + Docker Compose para self-host.

Alternativa considerada y descartada: TypeScript/Node end-to-end (MCP SDK +
Vercel AI SDK). Ecosistema equivalente, pero con panel web el backend Python
(FastAPI + FastMCP en un proceso) es más limpio y el autor es desarrollador
Python — la velocidad de iteración sobre el embudo contextual pesa más que
la comodidad de distribución de npm.
