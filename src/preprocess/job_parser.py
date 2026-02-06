import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from src.settings.settings import *
from src.schema.schema import JobParser

from google import genai
from google.genai import types
import mlflow

log_filename = f"{LOGS_DIR}/pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT"])

demo_job = {
    "title": "SeniorAI Engineer(Computer Vision/NPL/LLM) - KhốiCông Nghệ Thông Tin(HO26.18)",
    "company": "NGÂN HÀNG TMCP QUÂN ĐỘI – MBBANK",
    "location": "Số 18 Lê Văn Lương, Phường Trung Hoà, Quận Cầu Giấy, Thành phố Hà Nội, Việt Nam",
    "description": "handsome"
}

job_parser_prompt = mlflow.genai.load_prompt("prompts:/job_parser_prompt/1").template.format(
    title = demo_job["title"],
    company = demo_job["company"],
    location = demo_job["location"],
    description = demo_job["description"]
)

with mlflow.start_run():
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=job_parser_prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=JobParser,
        )
    )


















