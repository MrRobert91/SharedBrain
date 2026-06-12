import { useMemo, useState } from "react";
import { api, Idea } from "../api";
import { useApp } from "../App";
import { Badge, Dots, EmptyState, Markdown, Spinner, useData, VERDICT_TONE } from "../ui";

const GOALS = ["monetización", "marca-personal", "educación", "investigación", "aprendizaje"];
const HORIZONS = ["corto", "medio", "largo"];
const VERDICTS = ["sin-evaluar", "hacer", "reducir", "aparcar", "descartar"];

export function Ideas() {
  const { action, busy, refreshKey } = useApp();
  const { data: ideas, loading } = useData(api.ideas, [refreshKey]);
  const [selected, setSelected] = useState<string | null>(null);
  const [filterVerdict, setFilterVerdict] = useState("");
  const [filterGoal, setFilterGoal] = useState("");
  const [showGenerate, setShowGenerate] = useState(false);

  const filtered = useMemo(
    () =>
      (ideas ?? []).filter(
        (i) =>
          (!filterVerdict || i.verdict === filterVerdict) &&
          (!filterGoal || i.goal === filterGoal),
      ),
    [ideas, filterVerdict, filterGoal],
  );
  const current = filtered.find((i) => i.slug === selected) ?? null;

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Ideas</h2>
          <p className="section-hint">Genera, critica, refina y decide.</p>
        </div>
        <button className="btn primary" onClick={() => setShowGenerate((v) => !v)}>
          ✦ Generar ideas
        </button>
      </div>

      {showGenerate && <GenerateForm onDone={() => setShowGenerate(false)} />}

      <div className="filters">
        <select value={filterGoal} onChange={(e) => setFilterGoal(e.target.value)}>
          <option value="">todos los objetivos</option>
          {GOALS.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <select value={filterVerdict} onChange={(e) => setFilterVerdict(e.target.value)}>
          <option value="">todos los veredictos</option>
          {VERDICTS.map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <span className="meta">{filtered.length} idea(s)</span>
      </div>

      {loading && !ideas ? (
        <Spinner />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="✦"
          title="No hay ideas que mostrar"
          hint="Genera la primera tanda con el botón de arriba, o ajusta los filtros."
        />
      ) : (
        <div className="master-detail">
          <div className="master">
            {filtered.map((idea) => (
              <button
                key={idea.slug}
                className={idea.slug === selected ? "list-item active" : "list-item"}
                onClick={() => setSelected(idea.slug)}
              >
                <div className="list-item-title">{idea.title}</div>
                <div className="list-item-meta">
                  <Badge tone={VERDICT_TONE[idea.verdict ?? "sin-evaluar"]}>
                    {idea.verdict ?? "sin-evaluar"}
                  </Badge>
                  {idea.goal && <Badge tone="info">{idea.goal}</Badge>}
                  {idea.horizon && <Badge>{idea.horizon}</Badge>}
                </div>
              </button>
            ))}
          </div>
          <div className="detail">
            {current ? (
              <IdeaDetail idea={current} busy={!!busy} action={action} />
            ) : (
              <EmptyState icon="←" title="Selecciona una idea" hint="Verás la ficha completa y sus acciones." />
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function GenerateForm({ onDone }: { onDone: () => void }) {
  const { action, busy } = useApp();
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [customGoal, setCustomGoal] = useState("");
  const [n, setN] = useState(5);

  return (
    <form
      className="panel generate-form"
      onSubmit={async (e) => {
        e.preventDefault();
        const ok = await action("generación de ideas", () =>
          api.post("/api/ideas/generate", {
            goal: goal || null,
            horizon: horizon || null,
            custom_goal: customGoal || null,
            n,
          }),
        );
        if (ok) onDone();
      }}
    >
      <div className="form-row">
        <label>
          Objetivo
          <select value={goal} onChange={(e) => setGoal(e.target.value)}>
            <option value="">cualquiera</option>
            {GOALS.map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
        <label>
          Horizonte
          <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
            <option value="">cualquiera</option>
            {HORIZONS.map((h) => (
              <option key={h}>{h}</option>
            ))}
          </select>
        </label>
        <label>
          Nº ideas
          <input type="number" min={1} max={10} value={n} onChange={(e) => setN(+e.target.value)} />
        </label>
      </div>
      <label>
        Objetivo específico (texto libre, manda sobre lo demás)
        <input
          placeholder='p. ej. "quiero un side-project que genere ingresos pasivos con agentes de IA"'
          value={customGoal}
          onChange={(e) => setCustomGoal(e.target.value)}
        />
      </label>
      <div className="form-actions">
        <button className="btn primary" type="submit" disabled={!!busy}>
          Generar
        </button>
        <button className="btn" type="button" onClick={onDone}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

function IdeaDetail({
  idea,
  busy,
  action,
}: {
  idea: Idea;
  busy: boolean;
  action: (label: string, fn: () => Promise<unknown>) => Promise<boolean>;
}) {
  const [feedback, setFeedback] = useState("");
  const hasUserNotes = idea.body.includes("## Notas del usuario") && !idea.body.includes("_Añade aquí");

  return (
    <article className="idea-detail">
      <div className="detail-head">
        <h3>{idea.title}</h3>
        <div className="scores">
          <Dots value={idea.effort} label="esfuerzo" />
          <Dots value={idea.impact} label="impacto" />
          <Dots value={idea.fit} label="encaje" />
        </div>
      </div>

      <div className="detail-controls">
        <label className="inline">
          Tu veredicto
          <select
            value={idea.verdict ?? "sin-evaluar"}
            disabled={busy}
            onChange={(e) =>
              action("veredicto", () => api.patch(`/api/ideas/${idea.slug}`, { verdict: e.target.value }))
            }
          >
            {VERDICTS.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        {idea.verdict_sugerido && (
          <span className="meta">sugerido por la crítica: {idea.verdict_sugerido}</span>
        )}
        <span className="spacer" />
        <button
          className="btn"
          disabled={busy}
          onClick={() => action(`crítica de "${idea.title}"`, () => api.post(`/api/ideas/${idea.slug}/critique`))}
        >
          🥊 Criticar
        </button>
        <button
          className="btn"
          disabled={busy || !hasUserNotes}
          title={hasUserNotes ? "Regenera la ficha incorporando tus notas" : "Añade feedback abajo primero"}
          onClick={() => action(`rebuild de "${idea.title}"`, () => api.post(`/api/ideas/${idea.slug}/rebuild`))}
        >
          ♻ Rebuild
        </button>
        <button
          className="btn primary"
          disabled={busy}
          onClick={() => action(`promoción de "${idea.title}"`, () => api.post(`/api/ideas/${idea.slug}/promote`))}
        >
          🚀 Promocionar
        </button>
      </div>

      <form
        className="feedback-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!feedback.trim()) return;
          const ok = await action("feedback", () =>
            api.post(`/api/ideas/${idea.slug}/feedback`, { text: feedback }),
          );
          if (ok) setFeedback("");
        }}
      >
        <input
          placeholder="Añade una nota para refinar esta idea (luego pulsa Rebuild)…"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
        <button className="btn" type="submit" disabled={busy || !feedback.trim()}>
          ＋ Nota
        </button>
      </form>

      <Markdown text={idea.body} />
    </article>
  );
}
