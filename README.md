# SharedBrain

**Capa de contexto personal para agentes de IA.** Convierte conocimiento
disperso (un vault de Obsidian, repositorios de proyectos) en contexto
accionable para generar, evaluar, criticar y priorizar ideas de proyectos —
y para que cualquier agente trabaje con tu contexto de forma segura.

No es un almacén de notas ni una memoria pasiva: es un **embudo contextual**.

## Cómo funciona

- **Tu vault es el sustrato.** Las notas humanas son de solo lectura para
  los agentes; todo lo generado por IA vive en `_ai/` dentro del vault,
  etiquetado y trazable, revisable desde Obsidian.
- **Servidor MCP** (plano pasivo): cualquier agente puede buscar contexto,
  leer el perfil, consultar ideas y escribir —solo— en la zona IA.
- **Pipelines CLI** (plano activo): inferir tu perfil personal, generar y
  criticar ideas de proyectos, crear paquetes de contexto para tareas,
  extraer contexto de repositorios. Con los modelos y claves que tú
  configures.
- **Panel web** (React + Vite): seguir proyectos, estado e ideas, visualizar
  el contexto activo y promocionar ideas a proyectos sin pasar por la CLI.
- **Auto-hosteable y open source.** Python (FastAPI + FastMCP + pydantic-ai);
  el conocimiento es siempre Markdown con frontmatter en tu vault.

## Quickstart (desarrollo local)

```powershell
uv venv .venv; uv pip install -e ".[dev]"
.venv\Scripts\sharedbrain init "C:\ruta\a\tu\vault"   # crea _ai/ y la config
$env:ANTHROPIC_API_KEY = "sk-..."

.venv\Scripts\sharedbrain profile infer                # 1. infiere tu perfil
.venv\Scripts\sharedbrain ideas generate --goal educación --horizon corto
.venv\Scripts\sharedbrain ideas critique <slug>        # sparring de una idea
.venv\Scripts\sharedbrain ideas compare                # ranking razonado
.venv\Scripts\sharedbrain ideas promote <slug>         # idea → proyecto
.venv\Scripts\sharedbrain project-sync owner/repo      # contexto de un repo GitHub
.venv\Scripts\sharedbrain pack "escribir un artículo sobre X"

.venv\Scripts\sharedbrain serve          # MCP stdio para agentes locales
.venv\Scripts\sharedbrain serve --web    # panel web + API + MCP HTTP en :8765
```

Para el panel hace falta compilar el frontend una vez:
`cd frontend && npm install && npm run build`.

## Quickstart (Docker, self-host)

```bash
cp .env.example .env        # rellena VAULT_PATH y tus claves
mkdir -p data
# crea data/sharedbrain.config.yaml con al menos:  vault: /vault
docker compose up -d        # panel en http://localhost:8765
```

El agente se conecta por MCP a `http://localhost:8765/mcp/` (HTTP) o vía
stdio con `sharedbrain serve`. `GITHUB_TOKEN` habilita leer repos privados.

## Estado

✅ MVP implementado (fases 1–5 de [docs/02-mvp.md](docs/02-mvp.md)).
Documentación en [docs/](docs/):

- [00-brief.md](docs/00-brief.md) — visión y principios (documento fuente).
- [01-arquitectura.md](docs/01-arquitectura.md) — arquitectura, layout del
  vault, esquema de frontmatter, permisos, superficie MCP, stack.
- [02-mvp.md](docs/02-mvp.md) — alcance del MVP, comandos, fases de
  construcción y criterio de éxito.
