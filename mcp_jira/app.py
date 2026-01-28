from fastapi import FastAPI, HTTPException
import requests
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = FastAPI(title="MCP-JIRA (Enterprise)")

JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_EMAIL or not JIRA_API_TOKEN:
    raise RuntimeError("JIRA_EMAIL or JIRA_API_TOKEN missing")

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

@app.get("/context")
def get_jira_context(jira_url: str):
    """
    Accepts full Jira issue URL from UI
    Example:
    https://xyz.atlassian.net/browse/PROJ-123
    """

    if not jira_url:
        raise HTTPException(status_code=400, detail="jira_url is required")

    try:
        base_url = jira_url.split("/browse/")[0]
        issue_key = jira_url.split("/")[-1]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Jira URL format")

    api_url = f"{base_url}/rest/api/3/issue/{issue_key}"

    response = requests.get(
        api_url,
        auth=auth,
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    data = response.json()

    return {
        "storyId": data["key"],
        "summary": data["fields"]["summary"],
        "description": extract_text(data["fields"]["description"])
    }

# -------- Helper --------
def extract_text(description):
    """Extract plain text from Jira ADF"""
    if not description:
        return ""

    text = []
    for block in description.get("content", []):
        for item in block.get("content", []):
            if item.get("type") == "text":
                text.append(item.get("text", ""))

    return " ".join(text)
