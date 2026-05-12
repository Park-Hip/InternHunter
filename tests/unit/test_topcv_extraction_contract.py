import json
from pathlib import Path

import pytest

from src.core.models import LLMJobProcess, ProcessedJob


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "topcv"

REQUIRED_FIELDS = (
    "standardized_title",
    "description",
    "is_internship",
    "cities",
    "tech_stack",
    "domain_knowledge",
)


def assert_required_payload_fields(payload: dict) -> None:
    missing_fields = [field for field in REQUIRED_FIELDS if field not in payload]
    assert not missing_fields, f"Missing required payload fields: {missing_fields}"


def assert_jobprocessor_success_fields(job: ProcessedJob | LLMJobProcess) -> None:
    assert job.standardized_title
    assert job.description
    assert job.is_internship is False
    assert job.cities
    assert job.tech_stack
    assert job.domain_knowledge


def assert_salary_policy(job: ProcessedJob | LLMJobProcess, expectations: dict) -> None:
    assert job.salary_min == expectations["salary_min"]
    assert job.salary_max == expectations["salary_max"]
    assert job.currency == expectations["currency"]
    assert job.is_salary_negotiable is expectations["is_salary_negotiable"]


def assert_location_policy(job: ProcessedJob | LLMJobProcess, fixture_name: str) -> None:
    assert job.cities
    if fixture_name == "multiple_locations":
        assert len(job.cities) >= 2


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
    assert_required_payload_fields(payload)

    # Keep this test focused on the JSON contract. If the model import changes,
    # verify the current canonical ProcessedJob / LLMJobProcess shape in code.
    structured = ProcessedJob(**payload)
    typed = LLMJobProcess(**payload)

    assert_jobprocessor_success_fields(structured)
    assert_jobprocessor_success_fields(typed)
    assert_salary_policy(structured, expectations)
    assert_salary_policy(typed, expectations)
    assert_location_policy(structured, fixture_name)
    assert_location_policy(typed, fixture_name)

    assert structured.standardized_title == expectations["standardized_title"]
    assert structured.description.startswith(expectations["description_prefix"])
    # TODO: normal_job currently mixes "negotiable" semantics with a VND currency
    # placeholder. Keep the fixture stable for now and revisit if we add a true
    # salary-bearing baseline case.
