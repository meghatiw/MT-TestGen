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

            # Extract only relevant structured fields
            jira_summary = jira_ctx.get("summary", "")
            jira_description = jira_ctx.get("description", "")
            jira_ac = jira_ctx.get("acceptanceCriteria", "")

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

            logger.info(f"Loaded {len(ui_elements)} UI selectors")

            # --------------------------------------------------
            # STEP 1 – Generate Gherkin (Async)
            # --------------------------------------------------
            logger.info("Generating Gherkin (async)")

            gherkin = await asyncio.to_thread(
                call_llm,
                self._build_gherkin_prompt(
                    jira_summary,
                    jira_description,
                    jira_ac,
                    ui_elements
                )
            )

            # --------------------------------------------------
            # STEP 2 – Generate Selenium (Async)
            # --------------------------------------------------
            logger.info("Generating Selenium Step Definitions (async)")

            selenium = await asyncio.to_thread(
                call_llm,
                self._build_selenium_prompt(
                    gherkin,
                    ui_elements
                )
            )

            # --------------------------------------------------
            # Validate Selectors
            # --------------------------------------------------
            validation = self._validate_against_ui(
                selenium,
                ui_elements
            )

            critic = CriticAgent()
            review = critic.review(selenium, validation)

            # Retry if critic suggests improvement
            if review.get("can_retry"):
                logger.info("Retrying Selenium generation with critic feedback")

                selenium = await asyncio.to_thread(
                    call_llm,
                    self._build_selenium_prompt(
                        gherkin,
                        ui_elements
                    ) + "\n\nFix selector issues strictly. Do not invent any new selectors."
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
        resp = requests.get(url, params=params, timeout=120)
        if resp.status_code != 200:
            raise Exception(resp.text)
        return resp.json()

    # ======================================================
    # STRICT PROMPT BUILDERS (ANTI-HALLUCINATION)
    # ======================================================
    def _build_gherkin_prompt(
        self,
        summary,
        description,
        acceptance_criteria,
        selectors
    ):

        return f"""
STRICT INSTRUCTIONS:

You are generating automation ONLY for the provided UI repository.

DO NOT invent:
- Business domains
- Page names
- URLs
- Buttons
- Workflows

Use ONLY the selectors provided.

JIRA SUMMARY:
{summary}

JIRA DESCRIPTION:
{description}

ACCEPTANCE CRITERIA:
{acceptance_criteria}

AVAILABLE UI SELECTORS (MANDATORY):
{selectors}

Generate:
- One Feature
- Scenarios strictly derived from acceptance criteria
- Valid Gherkin syntax only
- No explanation
"""

    def _build_selenium_prompt(
        self,
        gherkin,
        selectors
    ):

        return f"""
Generate Selenium Java step definitions.

STRICT RULES:
- Use ONLY By.cssSelector
- Use ONLY selectors from allowed list
- Do NOT invent selectors
- Do NOT invent URLs
- Do NOT invent IDs
- Output ONLY valid Java code
- No explanation text

Gherkin:
{gherkin}

ALLOWED SELECTORS:
{selectors}
"""

    # ======================================================
    # VALIDATION (STRICT SELECTOR ENFORCEMENT)
    # ======================================================
    def _validate_against_ui(self, output, selectors_dict):

        allowed = set(selectors_dict.values())

        used = set(
            re.findall(r'By\.cssSelector\("([^"]+)"\)', output)
        )

        invalid = list(used - allowed)

        hallucinated_keywords = [
            "Test Generator",
            "Buy Test",
            "Sample App",
            "Demo App"
        ]

        domain_leak = any(word in output for word in hallucinated_keywords)

        return {
            "status": "PASS" if not invalid and not domain_leak else "FAIL",
            "invalidSelectors": invalid,
            "usedSelectors": list(used),
            "domainLeakDetected": domain_leak
        }
