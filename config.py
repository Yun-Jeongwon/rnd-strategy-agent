from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


BASE_PATH = Path(os.getenv("BASE_PATH", ".")).resolve()
DATA_ROOT = Path(os.getenv("DATA_ROOT", "./data"))
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "./outputs"))
PROMPT_ROOT = Path(os.getenv("PROMPT_ROOT", "./prompts"))

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def get_data_path(*parts: str) -> Path:
    return (BASE_PATH / DATA_ROOT / Path(*parts)).resolve()


def get_output_path(*parts: str) -> Path:
    return (BASE_PATH / OUTPUT_ROOT / Path(*parts)).resolve()


def get_prompt_path(*parts: str) -> Path:
    return (BASE_PATH / PROMPT_ROOT / Path(*parts)).resolve()


def ensure_output_dir() -> None:
    get_output_path().mkdir(parents=True, exist_ok=True)