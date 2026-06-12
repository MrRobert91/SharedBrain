"""Búsqueda léxica sobre el vault (MVP: sin embeddings)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .vault import Note, Scope, Vault

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(_normalize(text))


@dataclass
class SearchResult:
    note: Note
    score: float
    snippet: str


def search(vault: Vault, query: str, scope: Scope = "all", limit: int = 10) -> list[SearchResult]:
    terms = set(_tokens(query))
    if not terms:
        return []
    results: list[SearchResult] = []
    for note in vault.iter_notes(scope):
        title_tokens = set(_tokens(note.title) + _tokens(note.path))
        fm_tokens = set(_tokens(" ".join(str(v) for v in note.frontmatter.values())))
        body_norm = _normalize(note.body)
        score = 0.0
        matched_any = False
        for term in terms:
            in_title = term in title_tokens
            in_fm = term in fm_tokens
            body_hits = body_norm.count(term)
            if in_title or in_fm or body_hits:
                matched_any = True
            score += 3.0 * in_title + 2.0 * in_fm + min(body_hits, 10) * 1.0
        if matched_any:
            results.append(SearchResult(note=note, score=score, snippet=_snippet(note, terms)))
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def _snippet(note: Note, terms: set[str], width: int = 180) -> str:
    body_norm = _normalize(note.body)
    pos = min((p for t in terms if (p := body_norm.find(t)) >= 0), default=-1)
    if pos < 0:
        return note.body[:width].strip()
    start = max(0, pos - width // 3)
    return note.body[start : start + width].strip()
