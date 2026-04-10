import json
from openai import OpenAI

from config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE


client = OpenAI(api_key=OPENAI_API_KEY)


def run_chat(prompt: str, system_message: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=LLM_TEMPERATURE,
    )
    return response.choices[0].message.content or "[응답 없음]"


def parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "parse_error": "LLM 응답이 JSON 형식이 아님",
            "raw_response": text,
        }