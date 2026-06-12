import { useMemo, useState } from "react";
import { api, TreeNote } from "../api";
import { useApp } from "../App";
import { Badge, EmptyState, Markdown, Spinner, useData } from "../ui";

interface Folder {
  name: string;
  path: string;
  folders: Map<string, Folder>;
  notes: TreeNote[];
}

function buildTree(notes: TreeNote[]): Folder {
  const root: Folder = { name: "", path: "", folders: new Map(), notes: [] };
  for (const note of notes) {
    const parts = note.path.split("/");
    let node = root;
    for (const part of parts.slice(0, -1)) {
      if (!node.folders.has(part)) {
        node.folders.set(part, {
          name: part,
          path: node.path ? `${node.path}/${part}` : part,
          folders: new Map(),
          notes: [],
        });
      }
      node = node.folders.get(part)!;
    }
    node.notes.push(note);
  }
  return root;
}

export function Notes() {
  const { refreshKey } = useApp();
  const { data: tree, loading } = useData(api.vaultTree, [refreshKey]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const { data: note } = useData(
    () => (selectedPath ? api.note(selectedPath) : Promise.resolve(null)),
    [selectedPath],
  );

  const filtered = useMemo(() => {
    if (!tree) return [];
    const q = query.toLowerCase();
    return q ? tree.filter((n) => n.path.toLowerCase().includes(q) || n.title.toLowerCase().includes(q)) : tree;
  }, [tree, query]);

  const root = useMemo(() => buildTree(filtered), [filtered]);

  if (loading && !tree) return <Spinner />;

  return (
    <section>
      <h2>Notas del vault</h2>
      <p className="section-hint">
        Navega todo el vault: tus notas humanas y lo generado en <code>_ai/</code>.
      </p>
      <input
        className="search-box"
        placeholder="Filtrar por nombre o ruta…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="master-detail">
        <div className="master tree">
          {filtered.length === 0 ? (
            <EmptyState icon="✎" title="Sin notas" hint="El vault está vacío o el filtro no encuentra nada." />
          ) : (
            <FolderView folder={root} depth={0} selected={selectedPath} onSelect={setSelectedPath} />
          )}
        </div>
        <div className="detail">
          {note ? (
            <article>
              <div className="detail-head">
                <h3>{note.title}</h3>
                <Badge tone={note.path.startsWith("_ai/") ? "info" : "good"}>
                  {note.path.startsWith("_ai/") ? "generada por IA" : "nota humana"}
                </Badge>
                {typeof note.frontmatter.status === "string" && (
                  <Badge tone={note.frontmatter.status === "validated" ? "good" : "neutral"}>
                    {String(note.frontmatter.status)}
                  </Badge>
                )}
              </div>
              <div className="meta mono">{note.path}</div>
              <Markdown text={note.body} />
            </article>
          ) : (
            <EmptyState icon="←" title="Selecciona una nota" />
          )}
        </div>
      </div>
    </section>
  );
}

function FolderView({
  folder,
  depth,
  selected,
  onSelect,
}: {
  folder: Folder;
  depth: number;
  selected: string | null;
  onSelect: (p: string) => void;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  return (
    <div>
      {[...folder.folders.values()].map((sub) => (
        <div key={sub.path}>
          <button
            className="tree-folder"
            style={{ paddingLeft: 8 + depth * 14 }}
            onClick={() => setCollapsed((c) => ({ ...c, [sub.path]: !c[sub.path] }))}
          >
            {collapsed[sub.path] ? "▸" : "▾"} {sub.name === "_ai" ? "🤖 _ai" : `📁 ${sub.name}`}
          </button>
          {!collapsed[sub.path] && (
            <FolderView folder={sub} depth={depth + 1} selected={selected} onSelect={onSelect} />
          )}
        </div>
      ))}
      {folder.notes.map((n) => (
        <button
          key={n.path}
          className={n.path === selected ? "tree-note active" : "tree-note"}
          style={{ paddingLeft: 8 + depth * 14 }}
          onClick={() => onSelect(n.path)}
          title={n.path}
        >
          {n.origin === "ai" ? "◆" : "•"} {n.title}
        </button>
      ))}
    </div>
  );
}
