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
        self.markdown = SimpleNamespace(raw_markdown=markdown)
        self.screenshot = None


class DummyAsyncWebCrawler:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):
        return False


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
                "It includes responsibilities, requirements, and benefits sections. "
                "The content is intentionally long enough to satisfy the crawler's CSS quality gate. "
                "Additional detail ensures the info field is clearly non-trivial and representative."
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


@pytest.mark.asyncio
async def test_extract_single_job_marks_blocked_or_empty_content_as_blocked(mocker):
    html = (FIXTURE_DIR / "blocked_or_empty.html").read_text(encoding="utf-8")
    blocked_metadata = json.loads((FIXTURE_DIR / "blocked_or_empty.expected_failure.json").read_text(encoding="utf-8"))
    blocked_markdown = "Verify you are human. Access denied."

    mock_result = MockCrawlResult(
        html=html,
        extracted_content="[]",
        markdown=blocked_markdown,
    )

    mocker.patch("src.services.crawler.crawl.random.uniform", return_value=0)
    mocker.patch.object(Crawler, "_arun_with_retry", return_value=mock_result)

    crawler = Crawler()
    result = await crawler.extract_single_job(SimpleNamespace(), "https://example.com/job/blocked")

    assert blocked_metadata["fixture_name"] == "blocked_or_empty"
    assert blocked_metadata["expected_valid"] is False
    assert blocked_metadata["expected_failure_reason"] == "blocked_or_empty_content"
    assert blocked_metadata["required_missing_fields"] == ["standardized_title", "description"]
    assert result is not None
    assert result.status == "blocked"
    assert result.extraction_method == "raw"
    assert result.raw_markdown is not None
    assert "Verify you are human" in result.html
    assert result.full_json_dump["is_blocked"] is True
    assert result.full_json_dump["blocked_reason"] == "blocked_or_empty_content"


@pytest.mark.asyncio
async def test_extract_single_job_uses_raw_fallback_for_unparseable_css_content(mocker):
    html = (FIXTURE_DIR / "normal_job.html").read_text(encoding="utf-8")
    raw_markdown = "This is representative markdown for a TopCV job detail page with usable fallback text."

    mock_result = MockCrawlResult(
        html=html,
        extracted_content="[]",
        markdown=raw_markdown,
    )

    mocker.patch("src.services.crawler.crawl.random.uniform", return_value=0)
    mocker.patch.object(Crawler, "_arun_with_retry", return_value=mock_result)

    crawler = Crawler()
    result = await crawler.extract_single_job(SimpleNamespace(), "https://example.com/job/raw-fallback")

    assert result is not None
    assert result.status == "pending"
    assert result.extraction_method == "raw"
    assert result.raw_markdown is not None
    assert result.raw_markdown == raw_markdown
    assert result.full_json_dump["is_blocked"] is False
    assert result.full_json_dump["blocked_reason"] == "empty_or_unparseable_css_content"


@pytest.mark.asyncio
async def test_fetch_job_links_stops_after_requested_limit(mocker):
    crawler = Crawler()
    crawler.search_urls = ["https://example.com/search"]
    crawler.max_pages = 10

    async def fake_fetch_single_page(crawler_obj, url):
        page_num = 1
        if "page=" in url:
            page_num = int(url.split("page=")[-1])
        return (
            [
                {
                    "url": f"https://example.com/job/{page_num}",
                    "scraped_at": "2026-01-01T00:00:00Z",
                    "source": "topcv",
                }
            ],
            None,
        )

    mocker.patch("src.services.crawler.crawl.AsyncWebCrawler", return_value=DummyAsyncWebCrawler())
    mocker.patch("src.services.crawler.crawl.ETLRepository.filter_new_links", side_effect=lambda links: links)
    mock_fetch = mocker.patch.object(Crawler, "_fetch_single_page", side_effect=fake_fetch_single_page)

    outcome = await crawler.fetch_job_links("run-limit-3", limit=3)

    assert outcome.is_success
    assert len(outcome.links) == 3
    assert outcome.total_scraped == 3
    assert outcome.pages_scraped == 3
    assert mock_fetch.call_count == 3
