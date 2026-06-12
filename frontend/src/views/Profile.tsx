import { api } from "../api";
import { useApp } from "../App";
import { Badge, EmptyState, Markdown, Spinner, useData } from "../ui";

const ORDER = ["objetivos", "identidad", "valores", "patrones"];

export function Profile() {
  const { action, busy, refreshKey } = useApp();
  const { data: profile, loading } = useData(api.profile, [refreshKey]);

  const sorted = (profile ?? []).slice().sort(
    (a, b) => (ORDER.indexOf(a.section) + 99) - (ORDER.indexOf(b.section) + 99),
  );

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Perfil inferido</h2>
          <p className="section-hint">
            Lo que el sistema cree saber de ti a partir de tus notas. Revísalo: las ideas se anclan
            aquí, sobre todo en tus objetivos.
          </p>
        </div>
        <button
          className="btn primary"
          disabled={!!busy}
          onClick={() => action("inferencia de perfil", () => api.post("/api/profile/infer"))}
        >
          ◈ Inferir desde mis notas
        </button>
      </div>

      {loading && !profile ? (
        <Spinner />
      ) : !sorted.length ? (
        <EmptyState
          icon="◈"
          title="Sin perfil todavía"
          hint="Pulsa 'Inferir desde mis notas'. Tardará un par de minutos."
        />
      ) : (
        sorted.map((s) => (
          <article key={s.section} className="panel">
            <div className="detail-head">
              <h3>{s.section}</h3>
              <Badge tone={s.status === "validated" ? "good" : "warn"}>
                {s.status === "validated" ? "validado por ti" : `borrador (${s.status})`}
              </Badge>
              {s.confidence && <Badge>confianza: {s.confidence}</Badge>}
            </div>
            {s.status !== "validated" && (
              <p className="meta">
                Cuando estés conforme, edita la nota en Obsidian y pon <code>status: validated</code>.
                Una sección validada no se sobreescribe: las propuestas nuevas van a <code>_ai/inbox/</code>.
              </p>
            )}
            <Markdown text={s.body} />
          </article>
        ))
      )}
    </section>
  );
}
