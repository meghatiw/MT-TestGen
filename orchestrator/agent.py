import requests
import re
import logging
import asyncio
from mcp_critic.app import CriticAgent
from orchestrator.llm import call_llm

logger = logging.getLogger(__name__)


class TestGenerationAgent:

    # ======================================================
    # MAIN ENTRY – ASYNC GENERATION
    # ======================================================
    async def run(self, payload: dict):

        try:
            logger.info("Starting async test generation pipeline")

            # ---------------- JIRA CONTEXT ----------------
            jira_ctx = self._safe_get(
                "http://localhost:8002/context",
                {"jira_url": payload["jiraUrl"]}
            )

            jira_summary = jira_ctx.get("summary", "")
            jira_description = jira_ctx.get("description", "")
            jira_ac = jira_ctx.get("acceptanceCriteria", "")

            # ---------------- UI CONTEXT ----------------
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

            logger.info(f"Loaded {len(ui_elements)} UI selectors")

            # ======================================================
            # STEP 1 – GENERATE GHERKIN
            # ======================================================
            gherkin = await asyncio.to_thread(
                call_llm,
                self._build_gherkin_prompt(
                    jira_summary,
                    jira_description,
                    jira_ac
                )
            )

            # ======================================================
            # STEP 2 – GENERATE BUY STEPS
            # ======================================================
            selenium = await asyncio.to_thread(
                call_llm,
                self._build_selenium_prompt(
                    gherkin,
                    ui_elements
                )
            )

            # ======================================================
            # VALIDATION
            # ======================================================
            validation = self._validate_against_ui(
                selenium,
                ui_elements
            )

            critic = CriticAgent()
            review = critic.review(selenium, validation)

            if review.get("can_retry"):
                logger.info("Retrying Selenium generation with strict selector enforcement")

                selenium = await asyncio.to_thread(
                    call_llm,
                    self._build_selenium_prompt(
                        gherkin,
                        ui_elements
                    ) + "\n\nSTRICT: Use ONLY provided selectors."
                )

                validation = self._validate_against_ui(
                    selenium,
                    ui_elements
                )

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
        resp = requests.get(url, params=params, timeout=90)
        if resp.status_code != 200:
            raise Exception(resp.text)
        return resp.json()

    # ======================================================
    # PROMPT BUILDERS (CONTROLLED & LIGHTWEIGHT)
    # ======================================================
    def _build_gherkin_prompt(self, summary, description, acceptance_criteria):

        return f"""
Generate a SINGLE Gherkin Feature file.

STRICT RULES:
- Do NOT invent applications.
- Do NOT invent URLs.
- Use only acceptance criteria.
- Valid BDD syntax only.
- No explanations.

Summary:
{summary}

Description:
{description}

Acceptance Criteria:
{acceptance_criteria}
"""

    def _build_selenium_prompt(self, gherkin, selectors):

        # Limit selector size to avoid LLM overload
        selector_list = list(selectors.values())[:50]

        return f"""
Generate a COMPLETE Java class named BuySteps.

STRICT RULES:
- Package: steps
- Use io.cucumber.java.en.*
- Use WebDriverWait + ExpectedConditions
- Use By.cssSelector ONLY
- Use Hooks.driver
- Use ScreenshotUtil.capture() in Then step
- DO NOT invent selectors
- Use ONLY from list below
- Output ONLY Java code

Gherkin:
{gherkin}

ALLOWED SELECTORS:
{selector_list}
"""

    # ======================================================
    # VALIDATION
    # ======================================================
    def _validate_against_ui(self, output, selectors_dict):

        allowed = set(selectors_dict.values())
        used = set(re.findall(r'By\.cssSelector\("([^"]+)"\)', output))
        invalid = list(used - allowed)

        forbidden_keywords = [
            "Test Generator",
            "Sample App",
            "Demo App",
            "example.com"
        ]

        domain_leak = any(word in output for word in forbidden_keywords)

        return {
            "status": "PASS" if not invalid and not domain_leak else "FAIL",
            "invalidSelectors": invalid,
            "usedSelectors": list(used),
            "domainLeakDetected": domain_leak
        }
