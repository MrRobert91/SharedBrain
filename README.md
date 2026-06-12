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

## Despliegue en Sliplane (contenedor suelto, sin compose)

La imagen funciona sin archivo de config: todo se define por variables de
entorno. Servicio desde este repo (Dockerfile en la raíz), puerto **8765**.

**Variables de entorno:**

| Variable | Obligatoria | Valor |
| --- | --- | --- |
| `SHAREDBRAIN_PASSWORD` | ✅ (expuesto a internet) | Contraseña: panel, API y MCP exigen Basic Auth |
| `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | ✅ la del proveedor que uses | Clave de API |
| `SHAREDBRAIN_VAULT_REPO` | ✅ si tu vault vive en git | `owner/repo` o URL; se clona en `/vault` en el primer arranque |
| `GITHUB_TOKEN` | ✅ si el repo del vault es privado | También habilita `project-sync` de repos privados |
| `SHAREDBRAIN_MODEL` | recomendada | `openrouter:anthropic/claude-sonnet-4.6`, `anthropic:claude-fable-5`, `openai:gpt-5.2`… |
| `SHAREDBRAIN_MODEL_CHEAP` | no | Modelo barato para tareas menores |
| `SHAREDBRAIN_VAULT_BRANCH` | no | Rama del repo del vault (default: la principal) |
| `SHAREDBRAIN_VAULT` | no | Default `/vault` (ya fijado en la imagen) |
| `SHAREDBRAIN_DB` | no | Default `/data/sharedbrain.sqlite3` |

**Volúmenes persistentes:**

| Ruta en contenedor | Contenido |
| --- | --- |
| `/vault` | El vault (notas + zona `_ai/`). Imprescindible. |
| `/data` | SQLite de actividad. Prescindible (solo pierdes el historial del panel). |

Si Sliplane solo permite un volumen por servicio, monta uno en `/vault` y
define `SHAREDBRAIN_DB=/vault/.sharedbrain/sharedbrain.sqlite3`.

**El vault en el servidor:** con `SHAREDBRAIN_VAULT_REPO` definido, el
contenedor clona tu repo (con `GITHUB_TOKEN` si es privado) en el primer
arranque. Después, `vault sync` (botón 🔄 del panel o `sharedbrain
vault-sync`) hace commit de los cambios locales —las ideas y contexto
generados en el servidor—, `pull --rebase` y `push`, de modo que todo vuelve
a tu repo y aparece en tu Obsidian local al hacer pull. El token se inyecta
por invocación de git y nunca se escribe en el volumen.

El panel y el MCP quedan en `https://tu-app.sliplane.app` y
`https://tu-app.sliplane.app/mcp/` (con `Authorization: Basic …`).

## Selección de modelo

Formato pydantic-ai `proveedor:modelo` — en `sharedbrain.config.yaml`
(`models.default` / `models.cheap`) o por entorno (`SHAREDBRAIN_MODEL`,
`SHAREDBRAIN_MODEL_CHEAP`, que tienen prioridad sobre el YAML):

- `anthropic:claude-fable-5` (requiere `ANTHROPIC_API_KEY`)
- `openai:gpt-5.2` (requiere `OPENAI_API_KEY`)
- `openrouter:<cualquier-modelo-de-openrouter.ai/models>` (requiere `OPENROUTER_API_KEY`)
- También: `google-gla:`, `groq:`, `mistral:`… (proveedores de pydantic-ai)

## Estado

✅ MVP implementado (fases 1–5 de [docs/02-mvp.md](docs/02-mvp.md)).
Documentación en [docs/](docs/):

- [00-brief.md](docs/00-brief.md) — visión y principios (documento fuente).
- [01-arquitectura.md](docs/01-arquitectura.md) — arquitectura, layout del
  vault, esquema de frontmatter, permisos, superficie MCP, stack.
- [02-mvp.md](docs/02-mvp.md) — alcance del MVP, comandos, fases de
  construcción y criterio de éxito.
