export interface ProfileSection {
  section: string;
  status: string | null;
  confidence: string | null;
  body: string;
}

export interface Idea {
  slug: string;
  title: string;
  status: string | null;
  body: string;
  goal: string | null;
  horizon: string | null;
  effort: number | null;
  impact: number | null;
  fit: number | null;
  verdict: string | null;
  verdict_sugerido: string | null;
}

export interface Project {
  slug: string;
  repo: string | null;
  docs: Record<string, string>;
}

export interface Pack {
  slug: string;
  title: string;
  task: string | null;
  body: string;
}

export interface Run {
  id: number;
  pipeline: string;
  args: Record<string, unknown>;
  status: string;
  outputs: string[];
  error: string | null;
  started: string;
  finished: string | null;
}

export interface VaultStatus {
  repo: string | null;
  is_git: boolean;
  branch: string | null;
  dirty_files: number;
  last_commit: { sha: string; date: string; message: string } | null;
  last_sync: string | null;
  error: string | null;
}

export interface TreeNote {
  path: string;
  title: string;
  origin: "human" | "ai";
  type: string | null;
  status: string | null;
}

export interface Note {
  path: string;
  title: string;
  frontmatter: Record<string, unknown>;
  body: string;
}

export interface Stats {
  model: string;
  notes: { human: number; ai: number };
  ideas: { total: number; by_verdict: Record<string, number>; sin_critica: number };
  projects: number;
  packs: number;
  profile: { sections: number; validated: number };
  suggestions: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body !== undefined ? JSON.stringify(body) : undefined,
});

export const api = {
  profile: () => request<ProfileSection[]>("/api/profile"),
  ideas: () => request<Idea[]>("/api/ideas"),
  projects: () => request<Project[]>("/api/projects"),
  packs: () => request<Pack[]>("/api/packs"),
  runs: () => request<Run[]>("/api/runs"),
  stats: () => request<Stats>("/api/stats"),
  vaultStatus: () => request<VaultStatus>("/api/vault/status"),
  vaultTree: () => request<TreeNote[]>("/api/vault/tree"),
  note: (path: string) => request<Note>(`/api/note?path=${encodeURIComponent(path)}`),
  post: (path: string, body?: unknown) => request<{ written: string[] }>(path, json("POST", body)),
  patch: (path: string, body: unknown) => request<{ written: string[] }>(path, json("PATCH", body)),
};
