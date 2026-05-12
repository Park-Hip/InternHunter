import json
from pathlib import Path

from src.core.models import LLMJobProcess, ProcessedJob


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "topcv"


def test_normal_topcv_fixture_matches_current_job_contract():
    extracted_path = FIXTURE_DIR / "normal_job.extracted.json"
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

    assert typed.standardized_title
    assert typed.is_internship is False
    assert typed.cities
    assert typed.tech_stack
    assert typed.domain_knowledge

    assert structured.standardized_title == "Software Engineer Test"
    assert structured.description.startswith("This is a representative TopCV-like")
