class CriticAgent:
    def review(self, llm_output: str, validation: dict):
        issues = []

        if "RULE VIOLATION" in llm_output:
            issues.append("Prompt rule violation")

        if validation.get("status") == "FAIL":
            issues.append("Invalid selectors used")

        return {
            "issues": issues,
            "can_retry": bool(issues)
        }
