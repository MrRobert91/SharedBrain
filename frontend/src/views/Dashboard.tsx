import { api } from "../api";
import { useApp } from "../App";
import { EmptyState, Spinner, StatCard, useData } from "../ui";

export function Dashboard() {
  const { refreshKey, goTo } = useApp();
  const { data: stats, loading } = useData(api.stats, [refreshKey]);

  if (loading && !stats) return <Spinner />;
  if (!stats) return <EmptyState icon="◉" title="No se pudo cargar el estado" />;

  const verdicts = stats.ideas.by_verdict;
  return (
    <section>
      <h2>Dashboard</h2>
      <p className="section-hint">
        El estado de tu conocimiento, de un vistazo. Modelo activo: <code>{stats.model}</code>
      </p>

      <div className="stat-grid">
        <StatCard
          label="notas humanas"
          value={stats.notes.human}
          sub={`${stats.notes.ai} generadas por IA`}
          onClick={() => goTo("notas")}
        />
        <StatCard
          label="ideas"
          value={stats.ideas.total}
          sub={`${verdicts["hacer"] ?? 0} en hacer · ${stats.ideas.sin_critica} sin crítica`}
          onClick={() => goTo("ideas")}
        />
        <StatCard label="proyectos" value={stats.projects} onClick={() => goTo("proyectos")} />
        <StatCard
          label="perfil"
          value={`${stats.profile.validated}/${stats.profile.sections}`}
          sub="secciones validadas"
          onClick={() => goTo("perfil")}
        />
        <StatCard label="packs de contexto" value={stats.packs} onClick={() => goTo("packs")} />
      </div>

      <h3>Siguientes pasos sugeridos</h3>
      {stats.suggestions.length === 0 ? (
        <EmptyState icon="✓" title="Todo al día" hint="No hay nada pendiente que sugerir." />
      ) : (
        <ul className="suggestions">
          {stats.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
