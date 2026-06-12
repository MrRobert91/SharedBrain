"""Selección de contexto compartida por los pipelines (el "embudo")."""

from __future__ import annotations

from ..search import search
from ..vault import Note, Vault

NOTES_CHAR_BUDGET = 60_000


def profile_context(vault: Vault) -> str:
    """Perfil personal como texto, marcando qué está validado por el usuario.
    Los objetivos van primero: las ideas deben anclarse en los goals actuales."""
    profile_dir = vault.ai_path / "profile"
    if not profile_dir.is_dir():
        return "(No hay perfil inferido todavía. Ejecuta `sharedbrain profile infer`.)"
    order = {"objetivos": 0, "identidad": 1, "valores": 2, "patrones": 3}
    files = sorted(profile_dir.glob("*.md"), key=lambda f: order.get(f.stem, 9))
    chunks = []
    for f in files:
        note = vault.read(vault.relpath(f))
        validated = note.status == "validated"
        tag = "VALIDADO POR EL USUARIO" if validated else f"borrador, status={note.status}"
        chunks.append(f"### Perfil/{f.stem} ({tag})\n{note.body.strip()}")
    return "\n\n".join(chunks) if chunks else "(Perfil vacío.)"


def relevant_notes(vault: Vault, query: str, budget: int = NOTES_CHAR_BUDGET) -> list[Note]:
    """Notas humanas relevantes a la consulta, hasta agotar presupuesto.
    Si la búsqueda no llena el presupuesto, completa con las más recientes."""
    selected: list[Note] = []
    seen: set[str] = set()
    used = 0

    def take(note: Note) -> bool:
        nonlocal used
        if note.path in seen or len(note.body) < 20:
            return True
        if used + len(note.body) > budget:
            return False
        selected.append(note)
        seen.add(note.path)
        used += len(note.body)
        return True

    for result in search(vault, query, scope="human", limit=50):
        if not take(result.note):
            break
    if used < budget // 2:
        recent = sorted(
            vault.iter_notes("human"),
            key=lambda n: vault.resolve(n.path).stat().st_mtime,
            reverse=True,
        )
        for note in recent:
            if not take(note):
                break
    return selected


def notes_dump(notes: list[Note]) -> str:
    return "\n\n".join(f"<<< NOTA: {n.path} >>>\n{n.body.strip()}" for n in notes)
