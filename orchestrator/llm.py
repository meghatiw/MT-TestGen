import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-coder:6.7b"

SYSTEM_PROMPT = (
    "You are a senior QA automation engineer. "
    "You generate Cucumber Gherkin scenarios and Selenium Java step definitions. "
    "You STRICTLY follow provided UI selectors and context. "
    "You NEVER invent selectors, messages, URLs, or logic. "
    "If something is missing, you explicitly skip it."
)

def call_llm(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300
    )

    if response.status_code != 200:
        raise Exception(f"Ollama LLM error: {response.text}")

    data = response.json()
    return data.get("response", "").strip()
