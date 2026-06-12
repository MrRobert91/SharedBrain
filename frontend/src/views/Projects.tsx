import { useState } from "react";
import { api } from "../api";
import { useApp } from "../App";
import { Badge, EmptyState, Markdown, Spinner, useData } from "../ui";

const DOC_LABELS: Record<string, string> = {
  context: "Contexto",
  roadmap: "Roadmap",
  decisiones: "Decisiones",
  agentes: "Para agentes",
};

export function Projects() {
  const { action, busy, refreshKey } = useApp();
  const { data: projects, loading } = useData(api.projects, [refreshKey]);
  const [selected, setSelected] = useState<string | null>(null);
  const [doc, setDoc] = useState("context");
  const [origin, setOrigin] = useState("");

  const current = projects?.find((p) => p.slug === selected) ?? null;

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Proyectos</h2>
          <p className="section-hint">
            Contexto destilado de cada proyecto: estado real, roadmap e instrucciones para agentes.
          </p>
        </div>
      </div>

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          if (origin.trim())
            action(`sync de ${origin}`, () => api.post("/api/projects/sync", { origin: origin.trim() }));
        }}
      >
        <input
          className="grow"
          placeholder="Sincronizar repo: ruta local u owner/repo de GitHub"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
        />
        <button className="btn primary" type="submit" disabled={!!busy || !origin.trim()}>
          🔄 Sync repo
        </button>
      </form>

      {loading && !projects ? (
        <Spinner />
      ) : !projects?.length ? (
        <EmptyState
          icon="▣"
          title="Sin proyectos todavía"
          hint="Sincroniza un repositorio o promociona una idea desde la pestaña Ideas."
        />
      ) : (
        <div className="master-detail">
          <div className="master">
            {projects.map((p) => (
              <button
                key={p.slug}
                className={p.slug === selected ? "list-item active" : "list-item"}
                onClick={() => {
                  setSelected(p.slug);
                  setDoc(p.docs["context"] ? "context" : Object.keys(p.docs)[0] ?? "context");
                }}
              >
                <div className="list-item-title">▣ {p.slug}</div>
                <div className="list-item-meta">
                  {p.repo && <Badge tone="info">{p.repo}</Badge>}
                  <span className="meta">{Object.keys(p.docs).length} doc(s)</span>
                </div>
              </button>
            ))}
          </div>
          <div className="detail">
            {current ? (
              <article>
                <div className="detail-head">
                  <h3>{current.slug}</h3>
                  {current.repo && (
                    <button
                      className="btn small"
                      disabled={!!busy}
                      onClick={() =>
                        action(`re-sync de ${current.slug}`, () =>
                          api.post("/api/projects/sync", { origin: current.repo, slug: current.slug }),
                        )
                      }
                    >
                      🔄 Re-sync
                    </button>
                  )}
                </div>
                <div className="doc-tabs">
                  {Object.keys(current.docs).map((d) => (
                    <button key={d} className={doc === d ? "doc-tab active" : "doc-tab"} onClick={() => setDoc(d)}>
                      {DOC_LABELS[d] ?? d}
                    </button>
                  ))}
                  <span className="spacer" />
                  <button
                    className="btn small"
                    onClick={() => navigator.clipboard.writeText(current.docs[doc] ?? "")}
                    title="Copiar este documento para pasárselo a un agente"
                  >
                    📋 Copiar
                  </button>
                </div>
                <Markdown text={current.docs[doc] ?? Object.values(current.docs)[0] ?? ""} />
              </article>
            ) : (
              <EmptyState icon="←" title="Selecciona un proyecto" />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
