import re
import json
from abc import ABC, abstractmethod

from src.core.models import ProcessedJob, RawJob


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Enforces a common interface so the router can treat them interchangeably.
    """

    @abstractmethod
    def process_raw_job(self, job_data: RawJob) -> ProcessedJob:
        """Process a raw job posting into structured data using the LLM."""
        ...

    @abstractmethod
    def translate(self, text: str) -> str:
        """Translate text to English."""
        ...

    @staticmethod
    def _extract_info(info: str):
        """Extracts Description, Requirements, and Benefits from raw info text."""
        if not info:
            return None, None, None

        flags = re.DOTALL | re.IGNORECASE

        des_pattern = r"(?:Mô tả công việc|Job\s*Summary)(.*?)(?=Yêu cầu ứng viên|Responsibilities|$)"
        req_pattern = r"(?:Yêu cầu ứng viên|Responsibilities)(.*?)(?=Quyền lợi|Benefits|$)"
        ben_pattern = r"(?:Quyền lợi|Benefits)(.*)"

        des_match = re.search(des_pattern, info, flags)
        req_match = re.search(req_pattern, info, flags)
        ben_match = re.search(ben_pattern, info, flags)

        des = des_match.group(1).strip() if des_match else info
        req = req_match.group(1).strip() if req_match else None
        ben = ben_match.group(1).strip() if ben_match else None

        return des, req, ben

    def _prepare_job_context(self, job_data: RawJob):
        """
        Shared logic: parse raw JSON and extract description/requirement/benefit.
        Returns (raw_context_dict, description, requirement, benefit).
        """
        raw_context = {}
        description, requirement, benefit = None, None, None

        if job_data.full_json_dump:
            try:
                raw_context = json.loads(job_data.full_json_dump)
                info = raw_context.get("info", "")
                description, requirement, benefit = self._extract_info(info)
            except Exception:
                pass

        return raw_context, description, requirement, benefit
