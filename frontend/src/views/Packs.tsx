import { useState } from "react";
import { api } from "../api";
import { useApp } from "../App";
import { EmptyState, Markdown, Spinner, useData } from "../ui";

export function Packs() {
  const { action, busy, refreshKey } = useApp();
  const { data: packs, loading } = useData(api.packs, [refreshKey]);
  const [selected, setSelected] = useState<string | null>(null);
  const [task, setTask] = useState("");

  const current = packs?.find((p) => p.slug === selected) ?? null;

  return (
    <section>
      <h2>Packs de contexto</h2>
      <p className="section-hint">
        Documentos autocontenidos con lo mínimo que un agente necesita para una tarea concreta.
      </p>
      <form
        className="filters"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!task.trim()) return;
          const ok = await action("creación de pack", () => api.post("/api/packs/create", { task }));
          if (ok) setTask("");
        }}
      >
        <input
          className="grow"
          placeholder='Describe la tarea: "escribir un artículo sobre…", "crear el MVP de…"'
          value={task}
          onChange={(e) => setTask(e.target.value)}
        />
        <button className="btn primary" type="submit" disabled={!!busy || !task.trim()}>
          ⧉ Crear pack
        </button>
      </form>

      {loading && !packs ? (
        <Spinner />
      ) : !packs?.length ? (
        <EmptyState icon="⧉" title="Sin packs todavía" hint="Describe una tarea arriba para compilar el primero." />
      ) : (
        <div className="master-detail">
          <div className="master">
            {packs.map((p) => (
              <button
                key={p.slug}
                className={p.slug === selected ? "list-item active" : "list-item"}
                onClick={() => setSelected(p.slug)}
              >
                <div className="list-item-title">{p.title}</div>
                <div className="list-item-meta meta">{p.task}</div>
              </button>
            ))}
          </div>
          <div className="detail">
            {current ? (
              <article>
                <div className="detail-head">
                  <h3>{current.title}</h3>
                  <button className="btn small" onClick={() => navigator.clipboard.writeText(current.body)}>
                    📋 Copiar para el agente
                  </button>
                </div>
                <Markdown text={current.body} />
              </article>
            ) : (
              <EmptyState icon="←" title="Selecciona un pack" />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
