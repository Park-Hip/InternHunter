from fastapi.testclient import TestClient

from src.internhunter.api.app import app
import src.internhunter.api.routes.demo_routes as demo_routes


client = TestClient(app)


def test_health_endpoint_returns_ok(monkeypatch):
    monkeypatch.setattr(demo_routes, "_check_db_connection", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "search": "ready"}


def test_jobs_search_endpoint_returns_mocked_results(monkeypatch):
    monkeypatch.setattr(
        demo_routes.search_repo,
        "search_jobs_by_criteria",
        lambda **kwargs: [
            {
                "title": "Data Scientist",
                "company": "TopCV",
                "cities": ["Hanoi"],
                "url": "https://example.com/job/1",
                "salary_range": "10000000 - 20000000 VND",
            }
        ],
    )

    response = client.get("/jobs/search", params={"query": "data scientist", "limit": 5})

    assert response.status_code == 200
    assert response.json() == [
        {
            "title": "Data Scientist",
            "company": "TopCV",
            "cities": ["Hanoi"],
            "url": "https://example.com/job/1",
            "salary_range": "10000000 - 20000000 VND",
        }
    ]


def test_jobs_search_endpoint_handles_empty_results(monkeypatch):
    monkeypatch.setattr(demo_routes.search_repo, "search_jobs_by_criteria", lambda **kwargs: [])
    monkeypatch.setattr(demo_routes, "_get_recent_clean_jobs", lambda limit: [])

    response = client.get("/jobs/search", params={"query": "data scientist", "limit": 5})

    assert response.status_code == 200
    assert response.json() == []


def test_resume_match_endpoint_rejects_empty_resume_text():
    response = client.post(
        "/resume/match",
        json={"user_id": "demo-user", "resume_text": "   ", "limit": 5},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "resume_text cannot be empty."


def test_resume_match_endpoint_returns_mocked_matches(monkeypatch):
    monkeypatch.setattr(
        demo_routes,
        "execute_upload_resume",
        lambda user_id, resume_text: "Resume successfully uploaded and vectorized. You can now ask me to match jobs based on your profile!",
    )
    monkeypatch.setattr(
        demo_routes,
        "execute_match_resume",
        lambda user_id, limit=5: [
            {
                "title": "Machine Learning Engineer",
                "company": "TopCV",
                "cities": ["Ho Chi Minh City"],
                "url": "https://example.com/job/2",
                "match_score": 0.97,
            }
        ],
    )

    response = client.post(
        "/resume/match",
        json={
            "user_id": "demo-user",
            "resume_text": "Python data scientist with machine learning experience.",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "title": "Machine Learning Engineer",
            "company": "TopCV",
            "cities": ["Ho Chi Minh City"],
            "url": "https://example.com/job/2",
            "match_score": 0.97,
        }
    ]
