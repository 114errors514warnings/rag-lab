"""Golden Dataset 加载、字段映射与分层。"""

from __future__ import annotations

from pathlib import Path

from rag_lab.golden import by_query_type, filter_split, load_cases

ROOT = Path(__file__).resolve().parents[1]


def test_load_cases_field_mapping() -> None:
    cases, sha = load_cases(ROOT / "data/golden/cases.jsonl")
    assert len(cases) >= 30
    assert len(sha) == 16
    first = cases[0]
    assert first.id and first.question  # case_id/query -> id/question
    assert first.query_type in {"symbol", "semantic", "dependency", "literal", "no_answer", "update"}


def test_two_projects_present_for_isolation() -> None:
    cases, _ = load_cases(ROOT / "data/golden/cases.jsonl")
    projects = {c.project_id for c in cases if c.project_id}
    assert {"proj-auth", "proj-sched"} <= projects


def test_query_type_distribution_covers_all_types() -> None:
    cases, _ = load_cases(ROOT / "data/golden/cases.jsonl")
    types = set(by_query_type(cases))
    assert {"symbol", "semantic", "dependency", "literal", "no_answer"} <= types


def test_no_answer_cases_have_no_evidence() -> None:
    cases, _ = load_cases(ROOT / "data/golden/cases.jsonl")
    for case in cases:
        if case.query_type == "no_answer":
            assert case.gold_evidence == []


def test_filter_split() -> None:
    cases, _ = load_cases(ROOT / "data/golden/cases.jsonl")
    blind = filter_split(cases, "blind")
    assert blind and all(c.split == "blind" for c in blind)
    answerable = filter_split(cases, "answerable")
    assert all(c.gold_evidence for c in answerable)
    assert all(c.query_type != "no_answer" for c in answerable)
