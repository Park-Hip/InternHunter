import json
from pathlib import Path

import pytest

from src.core.models import LLMJobProcess, ProcessedJob


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "topcv"


@pytest.mark.parametrize(
    ("fixture_name", "expectations"),
    [
        (
            "normal_job",
            {
                "standardized_title": "Software Engineer Test",
                "description_prefix": "This is a representative TopCV-like",
                "salary_min": None,
                "salary_max": None,
                "currency": "VND",
                "is_salary_negotiable": True,
            },
        ),
        (
            "missing_salary",
            {
                "standardized_title": "Backend Engineer",
                "description_prefix": "This TopCV-like page intentionally omits salary",
                "salary_min": None,
                "salary_max": None,
                "currency": None,
                "is_salary_negotiable": False,
            },
        ),
        (
            "negotiable_salary",
            {
                "standardized_title": "Machine Learning Engineer",
                "description_prefix": "This TopCV-like page explicitly marks salary as negotiable.",
                "salary_min": None,
                "salary_max": None,
                "currency": None,
                "is_salary_negotiable": True,
            },
        ),
        (
            "multiple_locations",
            {
                "standardized_title": "Data Engineer",
                "description_prefix": "This TopCV-like page lists multiple work locations.",
                "salary_min": 1500.0,
                "salary_max": 2500.0,
                "currency": "USD",
                "is_salary_negotiable": False,
            },
        ),
    ],
)
def test_topcv_fixture_matches_current_job_contract(fixture_name, expectations):
    extracted_path = FIXTURE_DIR / f"{fixture_name}.extracted.json"
    payload = json.loads(extracted_path.read_text(encoding="utf-8"))

    # Keep this test focused on the JSON contract. If the model import changes,
    # verify the current canonical ProcessedJob / LLMJobProcess shape in code.
    structured = ProcessedJob(**payload)
    typed = LLMJobProcess(**payload)

    assert structured.standardized_title
    assert structured.description
    assert structured.is_internship is False
    assert structured.cities
    assert structured.tech_stack
    assert structured.domain_knowledge
    assert structured.salary_min == expectations["salary_min"]
    assert structured.salary_max == expectations["salary_max"]
    assert structured.currency == expectations["currency"]
    assert structured.is_salary_negotiable is expectations["is_salary_negotiable"]

    assert typed.standardized_title
    assert typed.is_internship is False
    assert typed.cities
    assert typed.tech_stack
    assert typed.domain_knowledge
    assert typed.salary_min == expectations["salary_min"]
    assert typed.salary_max == expectations["salary_max"]
    assert typed.currency == expectations["currency"]
    assert typed.is_salary_negotiable is expectations["is_salary_negotiable"]

    assert structured.standardized_title == expectations["standardized_title"]
    assert structured.description.startswith(expectations["description_prefix"])

    if fixture_name == "multiple_locations":
        assert len(structured.cities) >= 2
        assert len(typed.cities) >= 2
