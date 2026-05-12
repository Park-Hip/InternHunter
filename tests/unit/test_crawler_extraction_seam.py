import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.crawler.crawl import Crawler


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "topcv"


class MockCrawlResult:
    def __init__(self, html: str, extracted_content: str, markdown: str):
        self.success = True
        self.error_message = None
        self.extracted_content = extracted_content
        self.html = html
        self.markdown = markdown
        self.markdown_v2 = SimpleNamespace(raw_markdown=markdown)
        self.screenshot = None


@pytest.mark.asyncio
async def test_extract_single_job_returns_pending_raw_extraction_for_normal_topcv_fixture(mocker):
    html = (FIXTURE_DIR / "normal_job.html").read_text(encoding="utf-8")
    raw_markdown = "This is representative markdown for a TopCV job detail page."
    extracted_content = json.dumps([
        {
            "title": "Software Engineer Test",
            "company": "Boundary Co",
            "salary": "Negotiable",
            "location": "Hanoi, Vietnam",
            "experience": "2 years",
            "info": (
                "This is a representative TopCV-like job detail page used for fixture-based extraction tests. "
                "It includes responsibilities, requirements, and benefits sections."
            ),
        }
    ])

    mock_result = MockCrawlResult(
        html=html,
        extracted_content=extracted_content,
        markdown=raw_markdown,
    )

    mocker.patch("src.services.crawler.crawl.random.uniform", return_value=0)
    mocker.patch.object(Crawler, "_arun_with_retry", return_value=mock_result)

    crawler = Crawler()
    result = await crawler.extract_single_job(SimpleNamespace(), "https://example.com/job/normal")

    assert result is not None
    assert result.status == "pending"
    assert result.extraction_method == "css"
    assert result.title
    assert result.company
    assert result.location
    assert result.full_json_dump is not None
    assert result.raw_markdown is None
