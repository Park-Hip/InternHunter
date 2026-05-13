from math import sqrt

from src.internhunter.storage.repositories.search import SearchRepository, _distance_to_match_score
import src.internhunter.storage.repositories.search as search_repo_mod


def _cosine_distance(left, right):
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 1.0
    cosine_similarity = numerator / (left_norm * right_norm)
    return 1.0 - cosine_similarity


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement):
        statement_text = str(statement)
        assert "<=>" in statement_text or "cosine_distance" in statement_text
        assert "ORDER BY" in statement_text.upper()
        return _FakeResult(self._rows)


def test_distance_to_match_score_is_bounded():
    assert _distance_to_match_score(None) == 0.0
    assert _distance_to_match_score(0.0) == 1.0
    assert _distance_to_match_score(0.25) == 0.75
    assert _distance_to_match_score(1.0) == 0.0
    assert _distance_to_match_score(2.0) == 0.0


def test_search_jobs_by_similarity_handles_plain_float_distance(monkeypatch):
    rows = [
        {
            "clean_job_id": 1,
            "title": "Exact Match",
            "level": "Mid",
            "cities": ["Hanoi"],
            "experience_required_years": 2.0,
            "salary_min": 10000000,
            "salary_max": 20000000,
            "currency": "VND",
            "company": "TopCV",
            "url": "https://example.com/exact",
            "distance": 0.0,
        }
    ]

    monkeypatch.setattr(search_repo_mod, "SessionLocal", lambda: _FakeSession(rows))

    repo = SearchRepository()
    results = repo.search_jobs_by_similarity([1.0, 0.0, 0.0], limit=5)

    assert len(results) == 1
    assert results[0]["title"] == "Exact Match"
    assert results[0]["match_score"] == 1.0
    assert results[0]["url"] == "https://example.com/exact"


def test_search_jobs_by_similarity_returns_meaningful_scores(monkeypatch):
    query_embedding = [1.0, 0.0, 0.0]

    seeded_rows = [
        {
            "clean_job_id": 1,
            "title": "Exact Match",
            "level": "Mid",
            "cities": ["Hanoi"],
            "experience_required_years": 2.0,
            "salary_min": 10000000,
            "salary_max": 20000000,
            "currency": "VND",
            "company": "TopCV",
            "url": "https://example.com/exact",
            "distance": _cosine_distance(query_embedding, [1.0, 0.0, 0.0]),
        },
        {
            "clean_job_id": 2,
            "title": "Partial Match",
            "level": "Mid",
            "cities": ["Ho Chi Minh City"],
            "experience_required_years": 2.0,
            "salary_min": 15000000,
            "salary_max": 25000000,
            "currency": "VND",
            "company": "TopCV",
            "url": "https://example.com/partial",
            "distance": _cosine_distance(query_embedding, [0.70710678, 0.70710678, 0.0]),
        },
        {
            "clean_job_id": 3,
            "title": "Far Match",
            "level": "Mid",
            "cities": ["Da Nang"],
            "experience_required_years": 2.0,
            "salary_min": 5000000,
            "salary_max": 12000000,
            "currency": "VND",
            "company": "TopCV",
            "url": "https://example.com/far",
            "distance": _cosine_distance(query_embedding, [0.0, 1.0, 0.0]),
        },
    ]

    monkeypatch.setattr(search_repo_mod, "SessionLocal", lambda: _FakeSession(seeded_rows))

    repo = SearchRepository()
    results = repo.search_jobs_by_similarity(query_embedding, limit=5)

    assert [row["title"] for row in results] == ["Exact Match", "Partial Match", "Far Match"]
    assert results[0]["match_score"] == 1.0
    assert results[1]["match_score"] > results[2]["match_score"]
    assert len({row["match_score"] for row in results}) > 1
    assert results[0]["url"] == "https://example.com/exact"
    assert results[1]["url"] == "https://example.com/partial"
    assert results[2]["url"] == "https://example.com/far"
