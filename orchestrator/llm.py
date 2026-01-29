import requests
import json
import logging
import time

logger = logging.getLogger(__name__)

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
    logger.info(f"Calling LLM (Model: {MODEL})")
    logger.debug(f"Prompt length: {len(prompt)} characters")
    
    # Check Ollama connectivity first
    logger.debug(f"Verifying Ollama connectivity at {OLLAMA_URL}")
    try:
        health_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if health_response.status_code != 200:
            error_msg = f"Ollama health check failed with status {health_response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)
        logger.debug("Ollama connectivity verified")
    except Exception as e:
        error_msg = f"Failed to connect to Ollama at {OLLAMA_URL}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9
        }
    }
    
    logger.debug(f"Sending request to {OLLAMA_URL}")
    logger.debug(f"Total prompt size: {len(payload['prompt'])} characters")
    
    start_time = time.time()
    
    try:
        logger.info("Waiting for LLM response (this may take a while for complex prompts)...")
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=600  # Increased to 10 minutes for complex Selenium generation
        )
        
        elapsed_time = time.time() - start_time
        logger.debug(f"LLM response received in {elapsed_time:.2f} seconds")
        logger.debug(f"LLM response status code: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"Ollama LLM error: Status {response.status_code} | {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

        data = response.json()
        result = data.get("response", "").strip()
        
        if not result:
            error_msg = "LLM returned empty response"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"LLM response received successfully ({len(result)} characters in {elapsed_time:.2f}s)")
        logger.debug(f"Full LLM response:\n{result}")
        
        return result
        
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        error_msg = f"Timeout error: LLM request exceeded 600 seconds (elapsed: {elapsed_time:.2f}s)"
        logger.error(error_msg)
        raise Exception(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error to Ollama at {OLLAMA_URL}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM response JSON: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = f"Unexpected error in LLM call after {elapsed_time:.2f}s: {str(e)}"
        logger.error(error_msg)
        raise
