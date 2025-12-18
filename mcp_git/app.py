from fastapi import FastAPI, Query
import os
import re
import tempfile
import shutil
from git import Repo

app = FastAPI(title="MCP-GIT (E2E Automation Context)")

@app.get("/context")
def get_git_context(repo_url: str = Query(...)):
    """
    repo_url:
    - Local path OR
    - Git HTTPS URL
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

# ---------------- Helper Functions ----------------

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
