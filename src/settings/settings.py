from pathlib import Path

FILE_PATH = Path(__file__).resolve().parent
PROJECT_PATH = FILE_PATH.parent

# DIR
DATA_DIR = PROJECT_PATH / 'data'
JOBS_DIR = PROJECT_PATH / 'data' / 'jobs'
RAW_LINKS_DIR = PROJECT_PATH / 'data' / 'raw_links'
LOGS_DIR = PROJECT_PATH / 'logs'
DB_DIR = DATA_DIR / "db"
CONFIGS_DIR = PROJECT_PATH / 'configs'

DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)
RAW_LINKS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# Path


