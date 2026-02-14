import requests
import re
import logging
import asyncio
from mcp_critic.app import CriticAgent
from orchestrator.llm import call_llm

logger = logging.getLogger(__name__)


class TestGenerationAgent:

    # ======================================================
    # MAIN ENTRY – ASYNC GENERATION ONLY
    # ======================================================
    async def run(self, payload: dict):

        try:
            logger.info("Starting async test generation pipeline")

            # --------------------------------------------------
            # Fetch JIRA context
            # --------------------------------------------------
            jira_ctx = self._safe_get(
                "http://localhost:8002/context",
                {"jira_url": payload["jiraUrl"]}
            )

            # --------------------------------------------------
            # Fetch UI context
            # --------------------------------------------------
            ui_ctx = self._safe_get(
                "http://localhost:8001/context",
                {"repo_url": payload["uiRepo"]}
            )

            ui_elements = ui_ctx.get("elements") or {}
            if not ui_elements:
                return {
                    "status": "ERROR",
                    "message": "UI selectors unavailable"
                }

            # --------------------------------------------------
            # STEP 1 – Generate Gherkin (Non-blocking)
            # --------------------------------------------------
            logger.info("Generating Gherkin (async)")
            gherkin = await asyncio.to_thread(
                call_llm,
                self._build_gherkin_prompt(jira_ctx, ui_ctx)
            )

            # --------------------------------------------------
            # STEP 2 – Generate Selenium (Non-blocking)
            # --------------------------------------------------
            logger.info("Generating Selenium Step Definitions (async)")
            selenium = await asyncio.to_thread(
                call_llm,
                self._build_selenium_prompt(gherkin, ui_ctx)
            )

            # --------------------------------------------------
            # Validate Selectors
            # --------------------------------------------------
            validation = self._validate_against_ui(selenium, ui_ctx)

            critic = CriticAgent()
            review = critic.review(selenium, validation)

            # Retry if critic suggests
            if review.get("can_retry"):
                logger.info("Retrying Selenium generation with critic feedback")
                selenium = await asyncio.to_thread(
                    call_llm,
                    self._build_selenium_prompt(gherkin, ui_ctx)
                    + "\n\nFix selector issues strictly."
                )

                validation = self._validate_against_ui(selenium, ui_ctx)

            return {
                "status": "SUCCESS",
                "generatedArtifacts": {
                    "feature": gherkin.strip(),
                    "steps": selenium.strip()
                },
                "validationReport": validation
            }

        except Exception as e:
            logger.exception("Async generation pipeline failed")
            return {
                "status": "ERROR",
                "message": str(e)
            }

    # ======================================================
    # SAFE HTTP
    # ======================================================
    def _safe_get(self, url, params):
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            raise Exception(resp.text)
        return resp.json()

    # ======================================================
    # PROMPTS
    # ======================================================
    def _build_gherkin_prompt(self, jira, ui):
        return f"""
Generate ONLY a valid Gherkin feature file.
No explanations.
Strict BDD format.

JIRA STORY:
{jira}

ALLOWED SELECTORS:
{ui.get("elements")}
"""

    def _build_selenium_prompt(self, gherkin, ui):
        return f"""
Generate Selenium Java step definitions.

STRICT RULES:
- Use ONLY By.cssSelector
- Do NOT invent selectors
- Output ONLY Java code
- No explanations

Gherkin:
{gherkin}

ALLOWED SELECTORS:
{ui.get("elements")}
"""

    # ======================================================
    # VALIDATION
    # ======================================================
    def _validate_against_ui(self, output, ui_ctx):
        allowed = set(ui_ctx.get("elements", {}).values())

        used = set(
            re.findall(r'By\.cssSelector\("([^"]+)"\)', output)
        )

        invalid = list(used - allowed)

        return {
            "status": "PASS" if not invalid else "FAIL",
            "invalidSelectors": invalid,
            "usedSelectors": list(used)
        }
