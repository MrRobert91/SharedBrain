import { useCallback, useEffect, useState } from "react";
import { api, Idea, Pack, ProfileSection, Project, Run } from "./api";

type Tab = "ideas" | "proyectos" | "packs" | "perfil" | "actividad";

const TABS: { id: Tab; label: string }[] = [
  { id: "ideas", label: "Ideas" },
  { id: "proyectos", label: "Proyectos" },
  { id: "packs", label: "Packs" },
  { id: "perfil", label: "Perfil" },
  { id: "actividad", label: "Actividad" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("ideas");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const action = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(label);
      setError(null);
      try {
        await fn();
        refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(null);
      }
    },
    [refresh],
  );

  return (
    <div className="app">
      <header>
        <h1>🧠 SharedBrain</h1>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      {busy && <div className="banner busy">⏳ Ejecutando {busy}… (puede tardar)</div>}
      {error && (
        <div className="banner error" onClick={() => setError(null)}>
          ⚠️ {error}
        </div>
      )}
      <main>
        {tab === "ideas" && <IdeasView action={action} refreshKey={refreshKey} />}
        {tab === "proyectos" && <ProjectsView action={action} refreshKey={refreshKey} />}
        {tab === "packs" && <PacksView action={action} refreshKey={refreshKey} />}
        {tab === "perfil" && <ProfileView action={action} refreshKey={refreshKey} />}
        {tab === "actividad" && <RunsView refreshKey={refreshKey} />}
      </main>
    </div>
  );
}

interface ViewProps {
  action: (label: string, fn: () => Promise<unknown>) => Promise<void>;
  refreshKey: number;
}

function useData<T>(loader: () => Promise<T>, refreshKey: number): T | null {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    loader().then(setData).catch(() => setData(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);
  return data;
}

function Markdown({ text }: { text: string }) {
  return <pre className="md">{text}</pre>;
}

function IdeasView({ action, refreshKey }: ViewProps) {
  const ideas = useData(api.ideas, refreshKey);
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  return (
    <section>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          action("ideas generate", () =>
            api.post("/api/ideas/generate", {
              goal: goal || null,
              horizon: horizon || null,
              n: 5,
            }),
          );
        }}
      >
        <select value={goal} onChange={(e) => setGoal(e.target.value)}>
          <option value="">objetivo (cualquiera)</option>
          {["monetización", "marca-personal", "educación", "investigación", "aprendizaje"].map(
            (g) => (
              <option key={g}>{g}</option>
            ),
          )}
        </select>
        <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
          <option value="">horizonte (cualquiera)</option>
          {["corto", "medio", "largo"].map((h) => (
            <option key={h}>{h}</option>
          ))}
        </select>
        <button type="submit">✨ Generar ideas</button>
      </form>
      {!ideas?.length && <p className="empty">No hay ideas todavía. Genera las primeras.</p>}
      {ideas?.map((idea: Idea) => (
        <article key={idea.slug} className="card">
          <div className="card-head" onClick={() => setOpen(open === idea.slug ? null : idea.slug)}>
            <strong>{idea.title}</strong>
            <span className="meta">
              {idea.goal} · {idea.horizon} · esfuerzo {idea.effort} · impacto {idea.impact} · fit{" "}
              {idea.fit} ·{" "}
              <em className={`verdict v-${idea.verdict}`}>
                {idea.verdict}
                {idea.verdict_sugerido ? ` (sugerido: ${idea.verdict_sugerido})` : ""}
              </em>
            </span>
          </div>
          {open === idea.slug && (
            <div className="card-body">
              <div className="actions">
                <button
                  onClick={() =>
                    action(`critique ${idea.slug}`, () =>
                      api.post(`/api/ideas/${idea.slug}/critique`),
                    )
                  }
                >
                  🥊 Criticar
                </button>
                <button
                  onClick={() =>
                    action(`promote ${idea.slug}`, () =>
                      api.post(`/api/ideas/${idea.slug}/promote`),
                    )
                  }
                >
                  🚀 Promocionar a proyecto
                </button>
              </div>
              <Markdown text={idea.body} />
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

function ProjectsView({ action, refreshKey }: ViewProps) {
  const projects = useData(api.projects, refreshKey);
  const [origin, setOrigin] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [doc, setDoc] = useState("context");

  return (
    <section>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          if (origin) action(`sync ${origin}`, () => api.post("/api/projects/sync", { origin }));
        }}
      >
        <input
          placeholder="ruta local o owner/repo de GitHub"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
        />
        <button type="submit">🔄 Sync repo</button>
      </form>
      {!projects?.length && (
        <p className="empty">Sin proyectos. Sincroniza un repo o promociona una idea.</p>
      )}
      {projects?.map((p: Project) => (
        <article key={p.slug} className="card">
          <div className="card-head" onClick={() => setOpen(open === p.slug ? null : p.slug)}>
            <strong>{p.slug}</strong>
            <span className="meta">
              {p.repo ?? ""} · docs: {Object.keys(p.docs).join(", ")}
            </span>
          </div>
          {open === p.slug && (
            <div className="card-body">
              <div className="actions">
                {Object.keys(p.docs).map((d) => (
                  <button key={d} className={doc === d ? "active" : ""} onClick={() => setDoc(d)}>
                    {d}
                  </button>
                ))}
              </div>
              <Markdown text={p.docs[doc] ?? Object.values(p.docs)[0] ?? ""} />
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

function PacksView({ action, refreshKey }: ViewProps) {
  const packs = useData(api.packs, refreshKey);
  const [task, setTask] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  return (
    <section>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          if (task) action("pack create", () => api.post("/api/packs/create", { task }));
        }}
      >
        <input
          placeholder="describe la tarea para la que necesitas contexto"
          value={task}
          onChange={(e) => setTask(e.target.value)}
        />
        <button type="submit">📦 Crear pack</button>
      </form>
      {!packs?.length && <p className="empty">Sin packs todavía.</p>}
      {packs?.map((pack: Pack) => (
        <article key={pack.slug} className="card">
          <div className="card-head" onClick={() => setOpen(open === pack.slug ? null : pack.slug)}>
            <strong>{pack.title}</strong>
            <span className="meta">{pack.task}</span>
          </div>
          {open === pack.slug && (
            <div className="card-body">
              <div className="actions">
                <button onClick={() => navigator.clipboard.writeText(pack.body)}>
                  📋 Copiar para el agente
                </button>
              </div>
              <Markdown text={pack.body} />
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

function ProfileView({ action, refreshKey }: ViewProps) {
  const profile = useData(api.profile, refreshKey);
  return (
    <section>
      <div className="toolbar">
        <button onClick={() => action("profile infer", () => api.post("/api/profile/infer"))}>
          🔍 Inferir perfil desde mis notas
        </button>
        <span className="meta">
          Revisa cada sección en Obsidian y cambia status a "validated" cuando estés conforme.
        </span>
      </div>
      {!profile?.length && <p className="empty">Sin perfil inferido todavía.</p>}
      {profile?.map((s: ProfileSection) => (
        <article key={s.section} className="card">
          <div className="card-head">
            <strong>{s.section}</strong>
            <span className="meta">
              status: {s.status ?? "—"} · confianza: {s.confidence ?? "—"}
            </span>
          </div>
          <div className="card-body">
            <Markdown text={s.body} />
          </div>
        </article>
      ))}
    </section>
  );
}

function RunsView({ refreshKey }: { refreshKey: number }) {
  const runs = useData(api.runs, refreshKey);
  return (
    <section>
      {!runs?.length && <p className="empty">Sin actividad todavía.</p>}
      <table className="runs">
        <tbody>
          {runs?.map((r: Run) => (
            <tr key={r.id} className={r.status}>
              <td>{r.status === "ok" ? "✅" : r.status === "error" ? "❌" : "⏳"}</td>
              <td>{r.pipeline}</td>
              <td className="meta">{JSON.stringify(r.args)}</td>
              <td className="meta">{new Date(r.started).toLocaleString()}</td>
              <td className="meta">{r.error ?? r.outputs.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
