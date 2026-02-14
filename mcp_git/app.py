import requests
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from git import Repo
import os
import re
import tempfile
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import os

app = FastAPI(title="MCP-GIT (E2E Automation Context)")

# ============================================================
# CONFIGURATION
# ============================================================

E2E_REPO_URL = "https://github.com/meghatiw/megha-e2e-tests.git"
GIT_USERNAME = os.getenv("GIT_USERNAME")
GIT_TOKEN = os.getenv("GIT_TOKEN")
DEFAULT_BRANCH = "auto-generated-tests"
GITHUB_API = "https://api.github.com"
REPO_OWNER = "meghatiw"
REPO_NAME = "megha-e2e-tests"
MAX_RETRIES = 2


# ============================================================
# 1️⃣ CONTEXT EXTRACTION (EXISTING FEATURE)
# ============================================================

@app.get("/context")
def get_git_context(repo_url: str = Query(...)):
    """
    Extract existing features & step definitions
    """

    repo_path = clone_repo(repo_url)

    features = extract_features(repo_path)
    steps = extract_step_definitions(repo_path)

    shutil.rmtree(repo_path, ignore_errors=True)

    return {
        "repo": repo_url,
        "framework": "Cucumber + Selenium",
        "featureFiles": features,
        "existingSteps": steps
    }


# ============================================================
# 2️⃣ NEW: PUSH GENERATED TESTS TO E2E REPO
# ============================================================

class E2EPushRequest(BaseModel):
    feature_content: str
    selenium_code: str
    branch: str | None = None


@app.post("/push-e2e")
def push_e2e_tests(req: E2EPushRequest):

    if not GIT_USERNAME or not GIT_TOKEN:
        raise HTTPException(status_code=500, detail="Git credentials not configured")

    jira_id = "AUTO"  # you can dynamically extract from story
    branch = f"auto-test-{jira_id}-{datetime.now().strftime('%H%M%S')}"

    with tempfile.TemporaryDirectory() as tmpdir:

        tmpdir = tempfile.mkdtemp()

        try:
            clone_url = E2E_REPO_URL.replace(
                "https://",
                f"https://{GIT_USERNAME}:{GIT_TOKEN}@"
            )

            subprocess.run(["git", "clone", clone_url, tmpdir], check=True)
            subprocess.run(["git", "-C", tmpdir, "checkout", "-b", branch], check=True)

            features_path = os.path.join(tmpdir, "features")
            tests_path = os.path.join(tmpdir, "tests")

            os.makedirs(features_path, exist_ok=True)
            os.makedirs(tests_path, exist_ok=True)

            feature_file = os.path.join(features_path, f"{branch}.feature")
            test_file = os.path.join(tests_path, f"test_{branch}.java")

            with open(feature_file, "w", encoding="utf-8") as f:
                f.write(req.feature_content)

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(req.selenium_code)

            subprocess.run(["git", "-C", tmpdir, "add", "."], check=True)
            subprocess.run(["git", "-C", tmpdir, "commit", "-m", f"Auto E2E for {jira_id}"], check=True)
            subprocess.run(["git", "-C", tmpdir, "push", "origin", branch], check=True)

        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass

    pr_url = create_pull_request(branch)

    return {
        "status": "PR_CREATED",
        "branch": branch,
        "pull_request": pr_url
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clone_repo(repo_url: str) -> str:
    if os.path.exists(repo_url):
        return repo_url

    tmp_dir = tempfile.mkdtemp()
    Repo.clone_from(repo_url, tmp_dir)
    return tmp_dir


def extract_features(repo_path: str):
    feature_files = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".feature"):
                feature_files.append(file)

    return feature_files


def extract_step_definitions(repo_path: str):
    steps = set()

    step_pattern = re.compile(r'@(Given|When|Then|And)\("([^"]+)"\)')

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                with open(os.path.join(root, file), encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = step_pattern.findall(content)
                    for _, step in matches:
                        steps.add(step)

    return sorted(list(steps))

def create_pull_request(branch):

    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"

    headers = {
        "Authorization": f"token {GIT_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    data = {
        "title": f"Auto Generated E2E Tests - {branch}",
        "head": branch,
        "base": "main",
        "body": "Autonomous agent-generated test cases"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 201:
        raise Exception("PR creation failed")

    return response.json()["html_url"]

@app.get("/ci-status")
def get_ci_status(branch: str):

    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"

    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    runs = response.json().get("workflow_runs", [])

    for run in runs:
        if run["head_branch"] == branch:
            return {
                "status": run["status"],
                "conclusion": run["conclusion"],
                "details_url": run["html_url"]
            }

    return {"status": "NOT_FOUND"}

def merge_pull_request(pr_number):

    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"

    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    response = requests.put(url, headers=headers)

    return response.json()

def rerun_workflow(run_id):
    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/rerun"

    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    response = requests.post(url, headers=headers)
    return response.status_code == 201
import time

@app.post("/monitor-ci")
def monitor_ci(branch: str):

    retries = 0

    while retries <= MAX_RETRIES:

        status = get_ci_status(branch)

        if status.get("conclusion") == "success":
            return {"status": "PASSED"}

        if status.get("conclusion") == "failure":
            run_id = extract_run_id(status["details_url"])
            rerun_workflow(run_id)
            retries += 1
            time.sleep(30)

        time.sleep(10)

    return {"status": "FAILED_AFTER_RETRY"}

def extract_run_id(url):
    return url.split("/")[-1]
def get_workflow_logs(run_id):
    url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/logs"

    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    return response.content

