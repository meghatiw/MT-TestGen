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

@app.get("/context")
def get_jira_context(jira_url: str = Query(...)):
    """
    Example jira_url:
    https://megha1312.atlassian.net/browse/SCRUM-6
    """

    issue_key = jira_url.rstrip("/").split("/")[-1]

    api_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"

    response = requests.get(
        api_url,
        auth=auth,
        headers={"Accept": "application/json"}
    )

    response.raise_for_status()
    issue = response.json()

    fields = issue["fields"]

    return {
        "storyId": issue_key,
        "summary": fields.get("summary"),
        "description": extract_text(fields.get("description")),
        "acceptanceCriteria": extract_acceptance_criteria(fields.get("description")),
        "status": fields["status"]["name"],
        "priority": fields["priority"]["name"] if fields.get("priority") else None,
        "labels": fields.get("labels", []),
        "components": [c["name"] for c in fields.get("components", [])]
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
