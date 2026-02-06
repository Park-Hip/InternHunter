import os
import re

import yaml
from typing import Any
from src.settings.settings import CONFIGS_DIR

config_path = CONFIGS_DIR / "configs.yaml"

def load_configs() -> dict[str, Any]:
    """Load configuration from the YAML file."""

    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)

    with open(config_path, "r") as f:
        configs = yaml.safe_load(f)
    return configs


def parse_info(raw_text: str | None) -> dict[str, str | None]:
    """
    Splits the mashed TopCV description block into 3 clean sections.
    """
    info = {
        "job_description": None,
        "requirements": None,
        "benefits": None
    }

    if not raw_text:
        return info

    # 1. Normalize: Remove invisible characters/excess spaces
    text = " ".join(raw_text.split())

    # --- REGEX EXPLANATION ---
    # (?=...) is a "Lookahead". It means "Stop capturing when you see this next phrase"

    # 1. JOB DESCRIPTION
    # From "Mô tả công việc" -> Stop at "Yêu cầu ứng viên" OR "Quyền lợi"
    desc_match = re.search(
        r'Mô tả công việc[:\s]*(.*?)(?=Yêu cầu ứng viên|Yêu cầu công việc|Quyền lợi|Địa điểm làm việc|$)',
        text,
        re.IGNORECASE
    )
    if desc_match:
        info['job_description'] = desc_match.group(1).strip()

    # 2. REQUIREMENTS
    # From "Yêu cầu ứng viên" -> Stop at "Quyền lợi" OR "Địa điểm làm việc"
    req_match = re.search(
        r'(?:Yêu cầu ứng viên|Yêu cầu công việc)[:\s]*(.*?)(?=Quyền lợi|Địa điểm làm việc|Cách thức ứng tuyển|$)',
        text,
        re.IGNORECASE
    )
    if req_match:
        info['requirements'] = req_match.group(1).strip()

    # 3. BENEFITS
    # From "Quyền lợi" -> Stop at "Địa điểm làm việc" OR "Thời gian làm việc"
    ben_match = re.search(
        r'Quyền lợi[:\s]*(.*?)(?=Địa điểm làm việc|Thời gian làm việc|Cách thức ứng tuyển|$)',
        text,
        re.IGNORECASE
    )
    if ben_match:
        info['benefits'] = ben_match.group(1).strip()

    return info

def normalize_url(url: str) -> str:
    """Canonical URL for dedup (strip query/fragment and whitespace)."""
    if not url or not isinstance(url, str):
        return ""
    return url.split("?")[0].split("#")[0].strip()
