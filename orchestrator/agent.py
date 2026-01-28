import requests
import re
from mcp_critic.app import CriticAgent
from orchestrator.llm import call_llm


class TestGenerationAgent:

    # ======================================================
    # MAIN ENTRY
    # ======================================================
    def run(self, payload: dict):
        try:
            # ------------------------------
            # JIRA context
            # ------------------------------
            jira_ctx = self._safe_get(
                "http://localhost:8002/context",
                {"jira_url": payload["jiraUrl"]}
            )

            # ------------------------------
            # UI selectors context
            # ------------------------------
            ui_ctx = self._safe_get(
                "http://localhost:8001/context",
                {"repo_url": payload["uiRepo"]}
            )

            ui_elements = ui_ctx.get("elements") or {}

            # HARD STOP if no selectors
            if not ui_elements:
                return {
                    "status": "ERROR",
                    "message": "UI selectors unavailable. Cannot safely generate test automation."
                }

            # ------------------------------
            # (Optional) E2E repo context
            # ------------------------------
            _ = self._safe_get(
                "http://localhost:8004/context",
                {"repo_url": payload["e2eRepo"]}
            )

            # ==================================================
            # STEP 1: GHERKIN GENERATION (LLM)
            # ==================================================
            gherkin_prompt = self._build_gherkin_prompt(jira_ctx, ui_ctx)
            gherkin = call_llm(gherkin_prompt)
            print("\n===== GHERKIN OUTPUT =====\n", gherkin)

            # ==================================================
            # STEP 2: SELENIUM GENERATION (LLM)
            # ==================================================
            selenium_prompt = self._build_selenium_prompt(gherkin, ui_ctx)
            selenium = call_llm(selenium_prompt)

            print("\n===== SELENIUM OUTPUT =====\n", selenium)

            # ==================================================
            # VALIDATION (Selectors)
            # ==================================================
            validation = self._validate_against_ui(selenium, ui_ctx)

            critic = CriticAgent()
            review = critic.review(selenium, validation)

            # Retry once if critic allows
            if review.get("can_retry"):
                refined_prompt = selenium_prompt + (
                    "\n\nIMPORTANT: Fix selector issues and regenerate. "
                    "Do NOT invent selectors."
                )
                selenium = call_llm(refined_prompt)

                validation = self._validate_against_ui(selenium, ui_ctx)

            return {
                "status": "SUCCESS",
                "story": jira_ctx.get("storyId"),
                "generatedArtifacts": {
                    "feature": gherkin.strip(),
                    "steps": selenium.strip()
                },
                "validationReport": validation
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": str(e)
            }

    # ======================================================
    # SAFE HTTP GET
    # ======================================================
    def _safe_get(self, url: str, params: dict):
        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code != 200:
            raise Exception(
                f"MCP error at {url} | Status {resp.status_code} | {resp.text}"
            )

        if not resp.text.strip():
            raise Exception(f"Empty response from MCP at {url}")

        return resp.json()

    # ======================================================
    # PROMPT: GHERKIN ONLY
    # ======================================================
    def _build_gherkin_prompt(self, jira: dict, ui: dict):
        return f"""
Generate ONLY a Gherkin feature file.

STRICT RULES:
- Output ONLY Gherkin
- No step definitions
- No explanations
- Only visible UI actions
- Every step MUST reference a selector from UI context

JIRA STORY:
{jira}

ALLOWED UI SELECTORS:
{ui.get("elements")}

If a selector is missing, SKIP the step.
"""

    # ======================================================
    # PROMPT: SELENIUM ONLY
    # ======================================================
    def _build_selenium_prompt(self, gherkin: str, ui: dict):
        return f"""
Generate Selenium Java Step Definitions for the following Gherkin.

STRICT RULES:
- Output ONLY Java code
- Selenium + Cucumber
- Use By.cssSelector ONLY
- Use ONLY selectors from UI context
- Do NOT invent selectors
- If selector missing, add comment:
  // Step skipped — selector not available

Gherkin:
{gherkin}

ALLOWED UI SELECTORS:
{ui.get("elements")}
"""

    # ======================================================
    # VALIDATION
    # ======================================================
    def _validate_against_ui(self, llm_output: str, ui_ctx: dict):
        allowed = set(ui_ctx.get("elements", {}).values())

        used = set(
            re.findall(r'By\.cssSelector\("([^"]+)"\)', llm_output)
        )

        invalid = list(used - allowed)

        return {
            "allowedSelectors": list(allowed),
            "usedSelectors": list(used),
            "invalidSelectors": invalid,
            "status": "PASS" if not invalid else "FAIL"
        }
