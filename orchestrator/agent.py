import requests
import re
from orchestrator.llm import call_llm
import textwrap


class TestGenerationAgent:
    """
    Agent Orchestrator

    Responsibilities:
    - Fetch context from MCP services
    - Build high-quality prompt
    - Call LLM
    - Validate selectors against actual UI
    """

    # ======================================================
    # Public entry point
    # ======================================================
    def run(self, payload: dict):
        try:
            # ------------------------------
            # 1. Fetch JIRA context
            # ------------------------------
            jira_ctx = self._safe_get(
                "http://localhost:8002/context",
                {"jira_url": payload["jiraUrl"]}
            )

            # ------------------------------
            # 2. Fetch UI selector context
            # ------------------------------
            ui_ctx = self._safe_get(
                "http://localhost:8001/context",
                {"repo_url": payload["uiRepo"]}
            )

            # ------------------------------
            # SAFE GUARD RAIL
            # If no selectors → stop immediately
            # ------------------------------
            ui_elements = ui_ctx.get("elements") or {}

            if not ui_elements:
                return {
                    "status": "ERROR",
                    "message": (
                        "UI selectors unavailable. "
                        "Cannot safely generate test automation."
                    )
                }

            # ------------------------------
            # 3. Fetch existing E2E repo context
            # ------------------------------
            git_ctx = self._safe_get(
                "http://localhost:8004/context",
                {"repo_url": payload["e2eRepo"]}
            )

            # ------------------------------
            # 4. Build LLM prompt
            # ------------------------------
            prompt = self._build_prompt(jira_ctx, ui_ctx, git_ctx)

            # ------------------------------
            # 5. Generate artifacts
            # ------------------------------
            llm_output = call_llm(prompt)

            # ------------------------------
            # 6. Validate output
            # ------------------------------
            validation = self._validate_against_ui(llm_output, ui_ctx)

            return {
                "status": "SUCCESS",
                "story": jira_ctx.get("storyId"),
                "generatedArtifacts": llm_output,
                "validationReport": validation
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": str(e)
            }

    # ======================================================
    # MCP communication helper
    # ======================================================
    def _safe_get(self, url: str, params: dict):
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            raise Exception(
                f"MCP error at {url} | "
                f"Status: {response.status_code} | "
                f"Response: {response.text}"
            )

        if not response.text.strip():
            raise Exception(f"Empty response from MCP at {url}")

        try:
            return response.json()
        except Exception:
            raise Exception(
                f"Non-JSON response from MCP at {url}: {response.text}"
            )

    # ======================================================
    # Prompt construction
    # ======================================================
    def _build_prompt(self, jira: dict, ui: dict, git: dict) -> str:
        return textwrap.dedent(f"""
        You are generating UI automation that MUST run on the actual Megha Bank React UI.

        ==================================================
        CONTEXT: JIRA STORY
        ==================================================
        {jira}

        ==================================================
        REAL UI SELECTORS (GROUND TRUTH)
        ==================================================
        You may ONLY use selectors from this list:

        {ui.get("elements")}

        If you do NOT see a selector here, DO NOT invent it.

        ==================================================
        ABSOLUTE RESTRICTIONS
        ==================================================
        ==================================================
        DO NOT DO THESE
        ==================================================

        X Do NOT invent URLs
        X Do NOT open browsers
        X Do NOT add placeholders
        X Do NOT use xpath
        X Do NOT use UI_CONTEXT
        X Do NOT create fake messages
        X Do NOT use contains(), text(), aria assumptions
        X Do NOT assume error messages (like "Insufficient Balance")
        X Do NOT assert text unless UI context explicitly provides it


        ==================================================
        WHAT TO GENERATE
        ==================================================

        ### Feature File (Gherkin)

        Rules:
        - every step must reference a real UI element
        - UI navigation only (no backend rules)
        - no vague text like:
          "user logs in", "system processes", "generic success"

        GOOD:
            When I click the ".btn" button

        BAD:
            When user initiates transaction

        ==================================================
        ### Step Definitions (Java)

        Every locator MUST be in EXACT form:

        driver.findElement(
            By.cssSelector("<selector-from-ui-context>")
        );

        If selector unavailable, write:

        # Step skipped — selector not available

        Do NOT invent anything.

        ==================================================
        IF UI SELECTORS ARE EMPTY
        Return ONLY:

        "UI selectors unavailable. Cannot safely generate test automation."
        """)




    # ======================================================
    # Validation engine
    # ======================================================
    def _validate_against_ui(self, llm_output: str, ui_ctx: dict):
        """
        Validate ONLY selectors that are actually used in Selenium calls.

        We only consider selectors inside:

            By.cssSelector("<selector>")
        """
        allowed = set(ui_ctx.get("elements", {}).values())

        # Extract ONLY real selectors passed to cssSelector(...)
        used = set(
            re.findall(
                r'By\.cssSelector\("([^"]+)"\)',
                llm_output
            )
        )

        invalid = list(used - allowed)

        return {
            "allowedSelectors": list(allowed),
            "usedSelectors": list(used),
            "invalidSelectors": invalid,
            "status": "PASS" if not invalid else "FAIL"
        }
