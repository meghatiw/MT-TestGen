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
            if file.endswith((".jsx", ".tsx", ".js", ".ts", ".html")):
                file_path = os.path.join(root, file)

                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                    extract_from_file(content, selectors)

                    # also detect className selectors
                    class_matches = re.findall(r'class(Name)?=["\']([^"\']+)["\']', content)
                    for _, cls in class_matches:
                        cls_val = cls.split(" ")[0]   # first class only
                        selectors[f"class:{cls_val}"] = f".{cls_val}"

                    # detect button text
                    btn_texts = re.findall(r'<button[^>]*>([^<]+)</button>', content)
                    for txt in btn_texts:
                        cleaned = txt.strip()
                        if cleaned:
                            selectors[f"text:{cleaned}"] = f'button:contains("{cleaned}")'

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
