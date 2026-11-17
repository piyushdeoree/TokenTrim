"""Tests for optional semantic similarity in the hybrid redundancy system."""

import numpy as np

from nlp_engine.redundancy import (
    Clause,
    find_pairs,
    select_removals,
)


def make_clause(
    text,
    *,
    kind="instruction",
    stems=None,
    head="explain",
    negated=False,
    numbers=None,
):
    """Build a Clause without depending on the text segmentation pipeline."""
    return Clause(
        text=text,
        kind=kind,
        seg_index=0,
        stems=set(stems or []),
        head=head,
        negated=negated,
        numbers=set(numbers or []),
    )


def semantic_matrix(score=0.92):
    """Return a two-clause semantic similarity matrix."""
    return np.array([
        [1.0, score],
        [score, 1.0],
    ])


def test_semantic_similarity_can_find_paraphrased_instructions():
    clauses = [
        make_clause(
            "Describe how databases organize information",
            stems={"describe", "database", "organize", "information"},
        ),
        make_clause(
            "Explain the structure used to store records",
            stems={"explain", "structure", "store", "record"},
        ),
    ]

    pairs = find_pairs(clauses, semantic_sims=semantic_matrix())

    assert any(pair.relation == "similar" for pair in pairs)


def test_semantic_similarity_alone_never_removes_instructions():
    clauses = [
        make_clause(
            "Describe how databases organize information",
            stems={"describe", "database", "organize", "information"},
        ),
        make_clause(
            "Explain the structure used to store records",
            stems={"explain", "structure", "store", "record"},
        ),
    ]

    removals = select_removals(
        clauses,
        semantic_sims=semantic_matrix(),
    )

    assert removals == []


def test_semantic_similarity_does_not_override_negation():
    clauses = [
        make_clause(
            "Explain database indexing",
            stems={"explain", "database", "index"},
            negated=False,
        ),
        make_clause(
            "Do not explain database indexing",
            stems={"explain", "database", "index"},
            negated=True,
        ),
    ]

    removals = select_removals(
        clauses,
        semantic_sims=semantic_matrix(0.98),
    )

    assert removals == []


def test_semantic_similarity_does_not_override_numeric_constraints():
    clauses = [
        make_clause(
            "Provide exactly 3 examples",
            kind="constraint",
            stems={"provide", "exact", "example"},
            head="provide",
            numbers={"3"},
        ),
        make_clause(
            "Provide exactly 5 examples",
            kind="constraint",
            stems={"provide", "exact", "example"},
            head="provide",
            numbers={"5"},
        ),
    ]

    removals = select_removals(
        clauses,
        semantic_sims=semantic_matrix(0.99),
    )

    assert removals == []


def test_semantic_similarity_does_not_mix_different_clause_kinds():
    clauses = [
        make_clause(
            "Explain database indexing",
            kind="instruction",
            stems={"explain", "database", "index"},
        ),
        make_clause(
            "What is database indexing?",
            kind="question",
            stems={"database", "index"},
            head="what",
        ),
    ]

    pairs = find_pairs(clauses, semantic_sims=semantic_matrix(0.99))

    assert pairs == []


def test_existing_exact_duplicate_removal_still_works():
    clauses = [
        make_clause(
            "Explain database indexing",
            stems={"explain", "database", "index"},
        ),
        make_clause(
            "Explain database indexing",
            stems={"explain", "database", "index"},
        ),
    ]

    removals = select_removals(clauses)

    assert len(removals) == 1
