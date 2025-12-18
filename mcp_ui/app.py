from fastapi import FastAPI, Query
import os
import re
import tempfile
import shutil
from git import Repo

app = FastAPI(title="MCP-UI (React Repo Parser)")

SELECTOR_PATTERNS = {
    "data-testid": r'data-testid=["\']([^"\']+)["\']',
    "id": r'id=["\']([^"\']+)["\']',
    "name": r'name=["\']([^"\']+)["\']',
    "aria-label": r'aria-label=["\']([^"\']+)["\']'
}

@app.get("/context")
def get_ui_context(repo_url: str = Query(...)):
    """
    repo_url can be:
    - Local path
    - GitHub / Bitbucket HTTPS URL
    """

    repo_path = clone_repo(repo_url)

    selectors = extract_selectors(repo_path)

    shutil.rmtree(repo_path, ignore_errors=True)

    return {
        "repo": repo_url,
        "selectorCount": len(selectors),
        "elements": selectors
    }


# ---------------- Helper Functions ----------------

def clone_repo(repo_url: str) -> str:
    if os.path.exists(repo_url):
        return repo_url

    tmp_dir = tempfile.mkdtemp()
    Repo.clone_from(repo_url, tmp_dir)
    return tmp_dir


def extract_selectors(repo_path: str) -> dict:
    selectors = {}

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".jsx", ".tsx")):
                file_path = os.path.join(root, file)
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    extract_from_file(content, selectors)

    return selectors


def extract_from_file(content: str, selectors: dict):
    for attr, pattern in SELECTOR_PATTERNS.items():
        matches = re.findall(pattern, content)
        for match in matches:
            css_selector = build_css_selector(attr, match)
            selectors[f"{attr}:{match}"] = css_selector


def build_css_selector(attr: str, value: str) -> str:
    if attr == "data-testid":
        return f'[data-testid="{value}"]'
    if attr == "id":
        return f'#{value}'
    if attr == "name":
        return f'[name="{value}"]'
    if attr == "aria-label":
        return f'[aria-label="{value}"]'
    return value
