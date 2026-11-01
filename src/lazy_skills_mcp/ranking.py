"""Rank catalog entries against a free-text `find_skills` query.

Agents write queries that span several concepts ("nix flake python packaging"), so
a skill is kept when it contains any query term rather than every one. Each term is
weighted by its inverse document frequency over the catalog, in BM25's form, so a word
that appears in nearly every description ("a", "the", "to") adds almost nothing and a
rare one decides the order. The weight stays positive even for a word in every entry,
so a one-skill catalog still matches. A term found in the skill's name counts more
than one found only in its description. Hyphens are ignored when comparing, so
"bring-up" matches "bringup".
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from lazy_skills_mcp.catalog import SkillEntry

MAX_RESULTS = 10
_NAME_WEIGHT = 2.0


def _compact(text: str) -> str:
    """Lowercase `text` and drop hyphens, the form every comparison uses."""
    return text.lower().replace("-", "")


def query_terms(query: str | None) -> list[str]:
    """Split `query` into its distinct compacted terms, in first-seen order."""
    if not query:
        return []
    terms = (_compact(term) for term in query.split())
    return list(dict.fromkeys(term for term in terms if term))


def rank_entries(catalog: Sequence[SkillEntry], query: str | None) -> list[SkillEntry]:
    """Return the entries matching `query`, best first.

    Args:
        catalog: The scanned catalog, in name order.
        query: The agent's free-text query; empty or `None` selects everything.

    Returns:
        The whole catalog, unchanged, for an empty query. Otherwise at most
        `MAX_RESULTS` entries with a positive score, highest score first, ties
        kept in catalog order.
    """
    terms = query_terms(query)
    if not terms:
        return list(catalog)

    names = [_compact(entry.name) for entry in catalog]
    texts = [
        f"{name} {_compact(entry.description)}" for name, entry in zip(names, catalog, strict=True)
    ]
    weights = {term: _inverse_document_frequency(term, texts) for term in terms}

    scored: list[tuple[float, SkillEntry]] = []
    for entry, name, text in zip(catalog, names, texts, strict=True):
        score = sum(
            weights[term] * (_NAME_WEIGHT if term in name else 1.0)
            for term in terms
            if term in text
        )
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:MAX_RESULTS]]


def _inverse_document_frequency(term: str, texts: Sequence[str]) -> float:
    """BM25's `log(1 + (N - df + 0.5) / (df + 0.5))` for `term`; zero when it is absent."""
    document_frequency = sum(term in text for text in texts)
    if document_frequency == 0:
        return 0.0
    return math.log(1 + (len(texts) - document_frequency + 0.5) / (document_frequency + 0.5))
