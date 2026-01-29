import requests
import re
import logging
import time
from mcp_critic.app import CriticAgent
from orchestrator.llm import call_llm

logger = logging.getLogger(__name__)


class TestGenerationAgent:

    # ======================================================
    # MAIN ENTRY
    # ======================================================
    def run(self, payload: dict):
        try:
            logger.info("Starting test generation pipeline")
            logger.debug(f"Payload: {payload}")
            
            # ------------------------------
            # JIRA context
            # ------------------------------
            logger.info(f"Fetching JIRA context for: {payload['jiraUrl']}")
            jira_ctx = self._safe_get(
                "http://localhost:8002/context",
                {"jira_url": payload["jiraUrl"]}
            )
            logger.info(f"JIRA context retrieved successfully. Story ID: {jira_ctx.get('storyId')}")
            logger.debug(f"JIRA Context: {jira_ctx}")

            # ------------------------------
            # UI selectors context
            # ------------------------------
            logger.info(f"Fetching UI context from repo: {payload['uiRepo']}")
            ui_ctx = self._safe_get(
                "http://localhost:8001/context",
                {"repo_url": payload["uiRepo"]}
            )
            logger.info(f"UI context retrieved successfully")
            logger.debug(f"UI Context: {ui_ctx}")

            ui_elements = ui_ctx.get("elements") or {}
            logger.info(f"Total UI elements found: {len(ui_elements)}")

            # HARD STOP if no selectors
            if not ui_elements:
                logger.error("No UI elements/selectors available - cannot generate tests")
                return {
                    "status": "ERROR",
                    "message": "UI selectors unavailable. Cannot safely generate test automation."
                }

            # ------------------------------
            # (Optional) E2E repo context
            # ------------------------------
            if payload.get("e2eRepo"):
                logger.info(f"Fetching E2E context from repo: {payload['e2eRepo']}")
                _ = self._safe_get(
                    "http://localhost:8004/context",
                    {"repo_url": payload["e2eRepo"]}
                )
                logger.info("E2E context retrieved successfully")
            else:
                logger.info("No E2E repo provided - skipping")

            # ==================================================
            # STEP 1: GHERKIN GENERATION (LLM)
            # ==================================================
            logger.info("STEP 1: Generating Gherkin feature file")
            gherkin_prompt = self._build_gherkin_prompt(jira_ctx, ui_ctx)
            logger.debug(f"Gherkin prompt length: {len(gherkin_prompt)} characters")
            
            logger.info("  >>> Calling LLM for Gherkin generation...")
            gherkin_start = time.time()
            gherkin = call_llm(gherkin_prompt)
            gherkin_elapsed = time.time() - gherkin_start
            logger.info(f"✓ Gherkin generated in {gherkin_elapsed:.2f}s ({len(gherkin)} characters)")
            logger.debug(f"Gherkin output:\n{gherkin}")
            print("\n===== GHERKIN OUTPUT =====\n", gherkin)

            # ==================================================
            # STEP 2: SELENIUM GENERATION (LLM)
            # ==================================================
            logger.info("STEP 2: Generating Selenium step definitions")
            selenium_prompt = self._build_selenium_prompt(gherkin, ui_ctx)
            logger.debug(f"Selenium prompt length: {len(selenium_prompt)} characters")
            
            logger.info("  >>> Calling LLM for Selenium generation (this may take 1-5 minutes)...")
            logger.info("  >>> Please wait, LLM is processing complex code generation...")
            selenium_start = time.time()
            selenium = call_llm(selenium_prompt)
            selenium_elapsed = time.time() - selenium_start
            logger.info(f"✓ Selenium generated in {selenium_elapsed:.2f}s ({len(selenium)} characters)")
            logger.debug(f"Selenium output:\n{selenium}")
            print("\n===== SELENIUM OUTPUT =====\n", selenium)

            # ==================================================
            # VALIDATION (Selectors)
            # ==================================================
            logger.info("STEP 3: Validating selectors against UI context")
            validation = self._validate_against_ui(selenium, ui_ctx)
            logger.info(f"Validation result: {validation['status']}")
            logger.debug(f"Validation details: {validation}")

            if validation['status'] == 'FAIL':
                logger.warning(f"Invalid selectors found: {validation['invalidSelectors']}")

            logger.info("STEP 4: Running critic review")
            critic = CriticAgent()
            review = critic.review(selenium, validation)
            logger.info(f"Critic review: can_retry={review.get('can_retry')}")
            logger.debug(f"Critic review details: {review}")

            # Retry once if critic allows
            if review.get("can_retry"):
                logger.info("Retrying Selenium generation with critic feedback")
                refined_prompt = selenium_prompt + (
                    "\n\nIMPORTANT: Fix selector issues and regenerate. "
                    "Do NOT invent selectors."
                )
                selenium = call_llm(refined_prompt)
                logger.info(f"Refined Selenium generated ({len(selenium)} characters)")
                logger.debug(f"Refined Selenium output:\n{selenium}")

                validation = self._validate_against_ui(selenium, ui_ctx)
                logger.info(f"Validation after retry: {validation['status']}")
                logger.debug(f"Validation details after retry: {validation}")

            logger.info("Test generation pipeline completed successfully")
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
            elapsed = time.time() - time.time()  # This will show total pipeline time
            logger.exception(f"Exception occurred in test generation pipeline: {str(e)}")
            logger.error(f"Pipeline failed after attempting all steps")
            return {
                "status": "ERROR",
                "message": str(e),
                "details": f"Check orchestrator.log for detailed error traceback"
            }

    # ======================================================
    # SAFE HTTP GET
    # ======================================================
    def _safe_get(self, url: str, params: dict):
        logger.debug(f"Making HTTP GET request to {url} with params: {params}")
        try:
            resp = requests.get(url, params=params, timeout=30)
            logger.debug(f"Response status code: {resp.status_code}")

            if resp.status_code != 200:
                error_msg = f"MCP error at {url} | Status {resp.status_code} | {resp.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            if not resp.text.strip():
                error_msg = f"Empty response from MCP at {url}"
                logger.error(error_msg)
                raise Exception(error_msg)

            logger.debug(f"Successfully retrieved response from {url}")
            return resp.json()
        except requests.exceptions.Timeout:
            error_msg = f"Timeout error connecting to {url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error connecting to {url}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

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
        logger.debug("Starting selector validation")
        allowed = set(ui_ctx.get("elements", {}).values())
        logger.debug(f"Allowed selectors count: {len(allowed)}")

        used = set(
            re.findall(r'By\.cssSelector\("([^"]+)"\)', llm_output)
        )
        logger.debug(f"Used selectors count: {len(used)}")
        logger.debug(f"Used selectors: {used}")

        invalid = list(used - allowed)
        
        if invalid:
            logger.warning(f"Invalid selectors detected: {invalid}")
        else:
            logger.info("All selectors validated successfully")

        return {
            "allowedSelectors": list(allowed),
            "usedSelectors": list(used),
            "invalidSelectors": invalid,
            "status": "PASS" if not invalid else "FAIL"
        }
