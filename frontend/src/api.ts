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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  profile: () => request<ProfileSection[]>("/api/profile"),
  ideas: () => request<Idea[]>("/api/ideas"),
  projects: () => request<Project[]>("/api/projects"),
  packs: () => request<Pack[]>("/api/packs"),
  runs: () => request<Run[]>("/api/runs"),
  post: (path: string, body?: unknown) =>
    request<{ written: string[] }>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    }),
};
