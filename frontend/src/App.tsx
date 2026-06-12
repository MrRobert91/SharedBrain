import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, VaultStatus } from "./api";
import { Badge, Spinner, timeAgo } from "./ui";
import { Dashboard } from "./views/Dashboard";
import { Ideas } from "./views/Ideas";
import { Notes } from "./views/Notes";
import { Projects } from "./views/Projects";
import { Packs } from "./views/Packs";
import { Profile } from "./views/Profile";
import { Activity } from "./views/Activity";

type Tab = "dashboard" | "ideas" | "proyectos" | "notas" | "packs" | "perfil" | "actividad";

const NAV: { id: Tab; icon: string; label: string }[] = [
  { id: "dashboard", icon: "◉", label: "Dashboard" },
  { id: "ideas", icon: "✦", label: "Ideas" },
  { id: "proyectos", icon: "▣", label: "Proyectos" },
  { id: "notas", icon: "✎", label: "Notas" },
  { id: "packs", icon: "⧉", label: "Packs" },
  { id: "perfil", icon: "◈", label: "Perfil" },
  { id: "actividad", icon: "↺", label: "Actividad" },
];

interface Toast {
  id: number;
  kind: "ok" | "error";
  text: string;
}

interface AppContextValue {
  /** Lanza una acción del backend con toasts y refresco global. */
  action: (label: string, fn: () => Promise<unknown>) => Promise<boolean>;
  busy: string | null;
  refreshKey: number;
  goTo: (tab: Tab) => void;
}

const AppContext = createContext<AppContextValue>(null!);
export const useApp = () => useContext(AppContext);

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [busy, setBusy] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [vault, setVault] = useState<VaultStatus | null>(null);

  const toast = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "ok" ? 5000 : 10000);
  }, []);

  const refreshVault = useCallback(() => {
    api.vaultStatus().then(setVault).catch(() => setVault(null));
  }, []);

  useEffect(() => {
    refreshVault();
    const interval = setInterval(refreshVault, 60_000);
    return () => clearInterval(interval);
  }, [refreshVault, refreshKey]);

  const action = useCallback(
    async (label: string, fn: () => Promise<unknown>): Promise<boolean> => {
      setBusy(label);
      try {
        await fn();
        toast("ok", `${label}: completado`);
        setRefreshKey((k) => k + 1);
        return true;
      } catch (e) {
        toast("error", `${label}: ${e instanceof Error ? e.message : e}`);
        return false;
      } finally {
        setBusy(null);
      }
    },
    [toast],
  );

  const ctx: AppContextValue = { action, busy, refreshKey, goTo: setTab };

  return (
    <AppContext.Provider value={ctx}>
      <div className="layout">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-icon">🧠</span> SharedBrain
          </div>
          <nav>
            {NAV.map((item) => (
              <button
                key={item.id}
                className={tab === item.id ? "nav-item active" : "nav-item"}
                onClick={() => setTab(item.id)}
              >
                <span className="nav-icon">{item.icon}</span> {item.label}
              </button>
            ))}
          </nav>
          <VaultPanel vault={vault} />
        </aside>

        <div className="main-col">
          {busy && (
            <div className="busy-bar">
              <Spinner small /> Ejecutando <strong>{busy}</strong>… los pipelines con LLM pueden
              tardar uno o dos minutos.
            </div>
          )}
          <main className="content">
            {tab === "dashboard" && <Dashboard />}
            {tab === "ideas" && <Ideas />}
            {tab === "proyectos" && <Projects />}
            {tab === "notas" && <Notes />}
            {tab === "packs" && <Packs />}
            {tab === "perfil" && <Profile />}
            {tab === "actividad" && <Activity />}
          </main>
        </div>

        <div className="toasts">
          {toasts.map((t) => (
            <div key={t.id} className={`toast ${t.kind}`} onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}>
              {t.kind === "ok" ? "✓" : "✕"} {t.text}
            </div>
          ))}
        </div>
      </div>
    </AppContext.Provider>
  );
}

function VaultPanel({ vault }: { vault: VaultStatus | null }) {
  const { action, busy } = useApp();
  if (!vault) {
    return (
      <div className="vault-panel">
        <Spinner small /> vault…
      </div>
    );
  }
  const synced = vault.is_git && vault.dirty_files === 0;
  return (
    <div className="vault-panel">
      <div className="vault-row">
        <span className={`sync-dot ${synced ? "ok" : vault.is_git ? "warn" : "off"}`} />
        <span className="vault-state">
          {!vault.is_git
            ? "Vault sin repo git"
            : synced
              ? "Vault sincronizado"
              : `${vault.dirty_files} cambio(s) sin sincronizar`}
        </span>
      </div>
      {vault.is_git && (
        <>
          <div className="vault-meta">
            <Badge tone="neutral" title={vault.last_commit?.message}>
              {vault.branch} · {vault.last_commit?.sha ?? "—"}
            </Badge>
          </div>
          <div className="vault-meta">último sync: {timeAgo(vault.last_sync)}</div>
          <button
            className="btn small full"
            disabled={!!busy}
            onClick={() => action("sync del vault", () => api.post("/api/vault/sync"))}
          >
            ↑↓ Sincronizar ahora
          </button>
        </>
      )}
    </div>
  );
}
