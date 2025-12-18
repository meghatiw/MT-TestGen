import requests
import re
from orchestrator.llm import call_llm

class TestGenerationAgent:

    def run(self, payload: dict):
        try:
            jira_ctx = self._fetch_jira_context(payload["jiraUrl"])
            ui_ctx = self._fetch_ui_context(payload["uiRepo"])
            git_ctx = self._fetch_git_context(payload["e2eRepo"])

            prompt = self._build_prompt(jira_ctx, ui_ctx, git_ctx)
            llm_output = call_llm(prompt)

            validation = self._validate_against_ui(llm_output, ui_ctx)

            return {
                "status": "SUCCESS",
                "story": jira_ctx["storyId"],
                "generatedArtifacts": llm_output,
                "validationReport": validation
            }

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ---------- MCP CALLS ----------

    def _fetch_jira_context(self, jira_url):
        return requests.get(
            "http://localhost:8002/context",
            params={"jira_url": jira_url},
            timeout=10
        ).json()

    def _fetch_ui_context(self, repo_url):
        return requests.get(
            "http://localhost:8001/context",
            params={"repo_url": repo_url},
            timeout=20
        ).json()

    def _fetch_git_context(self, repo_url):
        return requests.get(
            "http://localhost:8004/context",
            params={"repo_url": repo_url},
            timeout=20
        ).json()

    # ---------- PROMPT ----------

    def _build_prompt(self, jira, ui, git):
        return f"""
You are generating enterprise-grade E2E automation.

JIRA STORY:
{jira["summary"]}

ACCEPTANCE CRITERIA:
{jira["acceptanceCriteria"]}

ALLOWED UI SELECTORS:
{ui["elements"]}

EXISTING AUTOMATION STEPS (REUSE THESE):
{git["existingSteps"]}

RULES:
- Use ONLY allowed UI selectors
- Reuse existing steps if present
- Generate missing steps only
- Output:
  1. FEATURE FILE
  2. STEP DEFINITIONS (Java Selenium)
"""

    # ---------- VALIDATION ----------

    def _validate_against_ui(self, llm_output, ui):
        allowed = set(ui["elements"].values())

        used = set(
            re.findall(r'cssSelector\("([^"]+)"\)|By.id\("([^"]+)"\)', llm_output)
        )
        used = {s for t in used for s in t if s}

        invalid = list(used - allowed)

        return {
            "allowedSelectors": list(allowed),
            "usedSelectors": list(used),
            "invalidSelectors": invalid,
            "status": "PASS" if not invalid else "FAIL"
        }
