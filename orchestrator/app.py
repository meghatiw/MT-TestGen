from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from orchestrator.agent import TestGenerationAgent


# ======================================================
# FASTAPI APP
# ======================================================
app = FastAPI(title="Agentic AI Test Generator")


# ======================================================
# CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# REQUEST MODEL
# ======================================================
class GenerateRequest(BaseModel):
    jiraUrl: str
    uiRepo: str = ""
    e2eRepo: str = ""


# ======================================================
# HEALTH CHECK
# ======================================================
@app.get("/health")
def health():
    return {"status": "UP"}


# ======================================================
# GENERATE TEST CASES
# ======================================================
@app.post("/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    """
    End-to-end generation pipeline:
    Jira → Gherkin (LLM) → Selenium (LLM) → Validation
    """
    result = TestGenerationAgent().run(req.dict())
    return result


# ======================================================
# SIMPLE UI (FOR DEMO)
# ======================================================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Agentic AI Test Generator</title>
  <style>
    body { font-family: Arial; margin: 40px; }
    input, textarea, button {
        width: 100%;
        margin: 10px 0;
        padding: 8px;
    }
    textarea {
        height: 160px;
        white-space: pre;
    }
    .pass { color: green; font-weight: bold; }
    .fail { color: red; font-weight: bold; }
  </style>
</head>
<body>

<h2>Agentic AI – Automated Test Case Generator</h2>

<label>JIRA Story URL</label>
<input id="jiraUrl" placeholder="https://megha-tiwari.atlassian.net/browse/KAN-1">

<label>UI Repo (optional)</label>
<input id="uiRepo" placeholder="https://github.com/.../ui.git">

<label>E2E Repo (optional)</label>
<input id="e2eRepo" placeholder="https://github.com/.../tests.git">

<button onclick="generate()">Generate Test Cases</button>

<h3>Feature File (Gherkin)</h3>
<textarea id="feature"></textarea>

<h3>Step Definitions (Selenium)</h3>
<textarea id="steps"></textarea>

<h3>Validation</h3>
<textarea id="validation"></textarea>

<script>
async function generate() {
  document.getElementById("feature").value = "Generating...";
  document.getElementById("steps").value = "";
  document.getElementById("validation").value = "";

  const payload = {
    jiraUrl: document.getElementById("jiraUrl").value,
    uiRepo: document.getElementById("uiRepo").value,
    e2eRepo: document.getElementById("e2eRepo").value
  };

  const res = await fetch("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if (data.generatedArtifacts) {
    document.getElementById("feature").value =
      data.generatedArtifacts.feature || "";

    document.getElementById("steps").value =
      data.generatedArtifacts.steps || "";
  }

  if (data.validationReport) {
    document.getElementById("validation").value =
      JSON.stringify(data.validationReport, null, 2);
  }
}
</script>

</body>
</html>
"""
