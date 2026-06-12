import { api } from "../api";
import { useApp } from "../App";
import { Badge, EmptyState, Spinner, timeAgo, useData } from "../ui";

const PIPELINE_LABELS: Record<string, string> = {
  "profile.infer": "Inferir perfil",
  "ideas.generate": "Generar ideas",
  "ideas.critique": "Criticar idea",
  "ideas.rebuild": "Rebuild de idea",
  "ideas.compare": "Comparar ideas",
  "packs.create": "Crear pack",
  "project.sync": "Sync de proyecto",
  "project.promote": "Promoción a proyecto",
  "vault.sync": "Sync del vault",
};

export function Activity() {
  const { refreshKey } = useApp();
  const { data: runs, loading } = useData(api.runs, [refreshKey]);

  if (loading && !runs) return <Spinner />;
  if (!runs?.length)
    return (
      <section>
        <h2>Actividad</h2>
        <EmptyState icon="↺" title="Sin actividad todavía" hint="Aquí verás cada pipeline ejecutado y su resultado." />
      </section>
    );

  return (
    <section>
      <h2>Actividad</h2>
      <p className="section-hint">Historial de pipelines: qué se ejecutó, cuándo y qué produjo.</p>
      <div className="activity-list">
        {runs.map((r) => (
          <div key={r.id} className="activity-item">
            <Badge tone={r.status === "ok" ? "good" : r.status === "error" ? "bad" : "warn"}>
              {r.status === "ok" ? "✓" : r.status === "error" ? "✕" : "…"}
            </Badge>
            <div className="activity-body">
              <div>
                <strong>{PIPELINE_LABELS[r.pipeline] ?? r.pipeline}</strong>
                <span className="meta"> · {timeAgo(r.started)}</span>
              </div>
              {Object.keys(r.args).length > 0 && (
                <div className="meta mono">
                  {Object.entries(r.args)
                    .filter(([, v]) => v != null && v !== "")
                    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                    .join("  ")}
                </div>
              )}
              <div className={r.error ? "meta error-text" : "meta"}>
                {r.error ?? r.outputs.join(" · ")}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
