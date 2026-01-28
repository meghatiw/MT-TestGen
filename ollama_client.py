import requests

def call_ollama(prompt, model="deepseek-coder:6.7b"):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 512
            }
        },
        timeout=300
    )

    response.raise_for_status()
    return response.json()["response"].strip()
