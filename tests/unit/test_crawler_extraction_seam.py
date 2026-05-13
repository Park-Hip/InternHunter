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


class DummyExtraction:
    def __init__(self, url: str):
        self.status = "pending"
        self.screenshot = None
        self.html = f"<html><body>{url}</body></html>"
        self._url = url

    def to_save_dict(self):
        return {
            "url": self._url,
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "full_json_dump": {"title": "Title"},
            "status": self.status,
            "extraction_method": "css",
            "raw_markdown": None,
        }


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
    blocked_markdown = "Sorry, you have been blocked. Please enable cookies. Cloudflare Ray ID: 1234567890abcdef"

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
    assert "Cloudflare Ray ID" in result.html
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


@pytest.mark.asyncio
async def test_fetch_job_links_force_recrawl_skips_dedup_filtering(mocker):
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
    mocker.patch.object(Crawler, "_fetch_single_page", side_effect=fake_fetch_single_page)
    mocker.patch("src.services.crawler.crawl.ETLRepository.filter_new_links", side_effect=AssertionError("dedup should be bypassed in force-recrawl mode"))

    outcome = await crawler.fetch_job_links("run-force-recrawl", limit=3, force_recrawl=True)

    assert outcome.is_success
    assert len(outcome.links) == 3
    assert outcome.total_scraped == 3
    assert outcome.pages_scraped == 3


@pytest.mark.asyncio
async def test_crawl_jobs_force_recrawl_skips_defensive_dedup_recheck(mocker):
    crawler = Crawler()
    mocker.patch("src.services.crawler.crawl.AsyncWebCrawler", return_value=DummyAsyncWebCrawler())
    mocker.patch("src.services.crawler.crawl.ETLRepository.get_raw_jobs_count", return_value=0)
    mocker.patch("src.services.crawler.crawl.ETLRepository.filter_new_links", side_effect=AssertionError("dedup should be bypassed in force-recrawl mode"))
    mocker.patch("src.services.crawler.crawl.ETLRepository.save_raw_job", return_value=True)
    mocker.patch("src.services.crawler.crawl.ETLRepository.save_to_audit", return_value=True)
    mocker.patch.object(Crawler, "extract_single_job", return_value=DummyExtraction("https://example.com/job/force"))

    saved, failed = await crawler.crawl_jobs([{"url": "https://example.com/job/force"}], "run-force-recrawl", force_recrawl=True)

    assert saved == 1
    assert failed == 0


@pytest.mark.asyncio
async def test_crawl_jobs_force_recrawl_refreshes_duplicate_raw_job_without_collision(mocker, test_db_session):
    from src.infrastructure.db.models import RawJobDB
    from src.internhunter.storage.repositories.etl import ETLRepository

    crawler = Crawler()
    repo = ETLRepository()
    existing_url = "https://example.com/job/force-refresh"
    assert repo.save_raw_job(
        {
            "url": existing_url,
            "title": "Original Title",
            "company": "Original Co",
            "location": "Remote",
            "full_json_dump": {"version": 1},
            "status": "pending",
            "extraction_method": "css",
            "raw_markdown": "original markdown",
        }
    )

    mocker.patch("src.services.crawler.crawl.AsyncWebCrawler", return_value=DummyAsyncWebCrawler())
    mocker.patch("src.services.crawler.crawl.ETLRepository.get_raw_jobs_count", return_value=1)
    mocker.patch("src.services.crawler.crawl.ETLRepository.filter_new_links", side_effect=AssertionError("dedup should be bypassed in force-recrawl mode"))
    mocker.patch.object(Crawler, "extract_single_job", return_value=DummyExtraction(existing_url))

    saved, failed = await crawler.crawl_jobs([{"url": existing_url}], "run-force-recrawl", force_recrawl=True)

    assert saved == 1
    assert failed == 0

    saved_job = test_db_session.query(RawJobDB).filter_by(url=existing_url).first()
    assert saved_job is not None
    assert saved_job.retry_count == 1
    assert saved_job.title == "Title"
    assert saved_job.crawl_run_id == "run-force-recrawl"


@pytest.mark.asyncio
async def test_crawl_jobs_saves_blocked_jobs_as_blocked_not_pending(mocker, test_db_session):
    from src.infrastructure.db.models import RawJobDB, AuditJobDB

    crawler = Crawler()
    blocked_url = "https://example.com/job/cloudflare-blocked"
    blocked_extraction = DummyExtraction(blocked_url)
    blocked_extraction.status = "blocked"
    blocked_extraction.html = (
        "<html><body>"
        "Please enable cookies. Sorry, you have been blocked. "
        "You are unable to access topcv.vn. Cloudflare Ray ID: abc123. "
        "Performance &amp; security by Cloudflare."
        "</body></html>"
    )

    mocker.patch("src.services.crawler.crawl.AsyncWebCrawler", return_value=DummyAsyncWebCrawler())
    mocker.patch("src.services.crawler.crawl.ETLRepository.get_raw_jobs_count", return_value=0)
    mocker.patch("src.services.crawler.crawl.ETLRepository.filter_new_links", side_effect=lambda links: links)
    mocker.patch("src.services.crawler.crawl.Crawler.extract_single_job", return_value=blocked_extraction)

    saved, failed = await crawler.crawl_jobs([{"url": blocked_url}], "run-blocked-case", force_recrawl=True)

    assert saved == 1
    assert failed == 0

    saved_job = test_db_session.query(RawJobDB).filter_by(url=blocked_url).first()
    assert saved_job is not None
    assert saved_job.status == "blocked"
    assert saved_job.crawl_run_id == "run-blocked-case"

    audit_row = test_db_session.query(AuditJobDB).filter_by(url=blocked_url).first()
    assert audit_row is not None
    assert audit_row.error_type == "BOT_DETECTED"
