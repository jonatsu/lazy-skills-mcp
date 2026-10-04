"""`rank_entries`, the `find_skills` scoring, exercised on in-memory catalogs."""

from __future__ import annotations

from pathlib import Path

from lazy_skills_server.catalog import SkillEntry
from lazy_skills_server.ranking import MAX_RESULTS, query_terms, rank_entries


def _entry(name: str, description: str) -> SkillEntry:
    return SkillEntry(name=name, description=description, directory=Path(name), files=())


def _names(entries: list[SkillEntry]) -> list[str]:
    return [entry.name for entry in entries]


NIX_CATALOG = [
    _entry("direnv-nix-direnv", "Load Nix shells per directory with direnv"),
    _entry("nix-flakes", "Author and debug Nix flakes for a project"),
    _entry("nix-packaging", "Package software as Nix derivations for a project"),
    _entry("python-style", "Write and review Python code for a project"),
]


def test_an_empty_query_returns_the_whole_catalog_in_order() -> None:
    assert _names(rank_entries(NIX_CATALOG, "")) == _names(NIX_CATALOG)
    assert _names(rank_entries(NIX_CATALOG, None)) == _names(NIX_CATALOG)


def test_a_query_spanning_two_skills_returns_both_ahead_of_partial_matches() -> None:
    ranked = _names(rank_entries(NIX_CATALOG, "nix flake packaging"))

    assert set(ranked[:2]) == {"nix-flakes", "nix-packaging"}
    assert ranked[2:] == ["direnv-nix-direnv"]


def test_an_unmatched_word_does_not_hide_the_skill_the_other_words_match() -> None:
    assert _names(rank_entries(NIX_CATALOG, "python zzzunknown")) == ["python-style"]


def test_a_query_matching_nothing_returns_nothing() -> None:
    assert rank_entries(NIX_CATALOG, "zzzunknown") == []


def test_a_word_in_every_description_cannot_outrank_a_distinguishing_one() -> None:
    """ "project" appears in every entry, so only "another" separates them."""
    catalog = [
        _entry("alpha", "a project tool"),
        _entry("beta", "another project tool"),
    ]

    assert _names(rank_entries(catalog, "project")) == ["alpha", "beta"]
    assert _names(rank_entries(catalog, "project another")) == ["beta", "alpha"]


def test_a_one_skill_catalog_still_matches() -> None:
    catalog = [_entry("only", "the single skill")]

    assert _names(rank_entries(catalog, "single")) == ["only"]


def test_a_rare_word_outranks_a_common_one() -> None:
    catalog = [
        _entry("common-one", "shared shared"),
        _entry("common-two", "shared"),
        _entry("rare-one", "unusual"),
        _entry("filler", "nothing relevant"),
    ]

    assert _names(rank_entries(catalog, "shared unusual"))[0] == "rare-one"


def test_a_name_match_outranks_a_description_only_match() -> None:
    catalog = [
        _entry("other", "mentions flakes in passing"),
        _entry("flakes-guide", "a guide"),
        _entry("filler", "nothing relevant"),
    ]

    assert _names(rank_entries(catalog, "flakes")) == ["flakes-guide", "other"]


def test_matching_ignores_case_and_hyphens() -> None:
    catalog = [
        _entry("embedded-linux-bringup", "Bring a new board up"),
        _entry("filler", "nothing relevant"),
    ]

    assert _names(rank_entries(catalog, "BRING-UP")) == ["embedded-linux-bringup"]


def test_equal_scores_keep_catalog_order() -> None:
    catalog = [_entry(f"skill-{index}", "same words") for index in range(3)]
    catalog.append(_entry("filler", "nothing relevant"))

    assert _names(rank_entries(catalog, "same")) == ["skill-0", "skill-1", "skill-2"]


def test_results_stop_at_the_cap() -> None:
    catalog = [_entry(f"skill-{index:02}", "match") for index in range(MAX_RESULTS + 2)]
    catalog.append(_entry("filler", "nothing relevant"))

    assert len(rank_entries(catalog, "match")) == MAX_RESULTS


def test_query_terms_are_distinct_compacted_and_ordered() -> None:
    assert query_terms("Nix  nix BRING-UP -") == ["nix", "bringup"]
