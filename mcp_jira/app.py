from fastapi import FastAPI, Query
import requests
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = FastAPI(title="MCP-JIRA (Enterprise)")

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

from fastapi import FastAPI, HTTPException
import requests, os

app = FastAPI()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

@app.get("/context")
def get_jira_context(jira_url: str):
    if not jira_url:
        raise HTTPException(status_code=400, detail="jira_url is required")

    issue_key = jira_url.split("/")[-1]

    api_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"

    response = requests.get(
        api_url,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json"}
    )

    response.raise_for_status()
    data = response.json()

    return {
        "storyId": data["key"],
        "summary": data["fields"]["summary"],
        "description": data["fields"]["description"]
    }


# -------- Helper Functions --------

def extract_text(description):
    """Extract plain text from Atlassian ADF"""
    if not description:
        return ""

    text = []
    for block in description.get("content", []):
        for item in block.get("content", []):
            if item["type"] == "text":
                text.append(item["text"])
    return " ".join(text)


def extract_acceptance_criteria(description):
    """
    Heuristic extraction:
    - Bullet points
    - Lines starting with AC / Acceptance Criteria
    """
    if not description:
        return []

    criteria = []

    for block in description.get("content", []):
        if block["type"] == "bulletList":
            for li in block["content"]:
                line = []
                for item in li["content"]:
                    for text in item.get("content", []):
                        if text["type"] == "text":
                            line.append(text["text"])
                if line:
                    criteria.append(" ".join(line))

    return criteria
