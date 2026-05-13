import pytest

import src.services.chat.tools as tools


def test_is_missing_embedding_handles_none_and_empty():
    assert tools.is_missing_embedding(None) is True
    assert tools.is_missing_embedding([]) is True
    assert tools.is_missing_embedding(()) is True


def test_execute_match_resume_accepts_list_embedding(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        tools.chat_repo,
        "get_user_profile",
        lambda user_id: {"user_id": user_id, "resume_embedding": [0.1, 0.2, 0.3]},
    )

    def fake_search_jobs_by_similarity(embedding, limit=5):
        captured["embedding"] = embedding
        captured["limit"] = limit
        return [{"title": "Data Scientist", "match_score": 0.99}]

    monkeypatch.setattr(tools.search_repo, "search_jobs_by_similarity", fake_search_jobs_by_similarity)

    results = tools.execute_match_resume("user-list", limit=7)

    assert results == [{"title": "Data Scientist", "match_score": 0.99}]
    assert captured["embedding"] == [0.1, 0.2, 0.3]
    assert captured["limit"] == 7


def test_execute_match_resume_accepts_numpy_embedding(monkeypatch):
    np = pytest.importorskip("numpy")
    captured = {}

    monkeypatch.setattr(
        tools.chat_repo,
        "get_user_profile",
        lambda user_id: {"user_id": user_id, "resume_embedding": np.array([0.1, 0.2, 0.3])},
    )

    def fake_search_jobs_by_similarity(embedding, limit=5):
        captured["embedding"] = embedding
        captured["limit"] = limit
        return [{"title": "Machine Learning Engineer", "match_score": 0.95}]

    monkeypatch.setattr(tools.search_repo, "search_jobs_by_similarity", fake_search_jobs_by_similarity)

    results = tools.execute_match_resume("user-np", limit=3)

    assert results == [{"title": "Machine Learning Engineer", "match_score": 0.95}]
    assert captured["limit"] == 3
    assert np.array_equal(captured["embedding"], np.array([0.1, 0.2, 0.3]))


def test_execute_match_resume_returns_error_for_missing_embedding(monkeypatch):
    monkeypatch.setattr(
        tools.chat_repo,
        "get_user_profile",
        lambda user_id: {"user_id": user_id, "resume_embedding": None},
    )

    results = tools.execute_match_resume("user-missing", limit=5)

    assert results == [{"error": "No resume found for this user. Please upload a resume first."}]
