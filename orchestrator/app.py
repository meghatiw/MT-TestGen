from fastapi.responses import HTMLResponse
from fastapi import FastAPI
from pydantic import BaseModel
from orchestrator.agent import TestGenerationAgent

app = FastAPI(title="Agentic AI Test Generator")

class GenerateRequest(BaseModel):
    appUrl: str
    appRepo: str
    jiraUrl: str
    cucumberRepo: str

@app.get("/health")
def health():
    return {"status": "UP"}

@app.post("/generate")
def generate(req: GenerateRequest):
    return TestGenerationAgent().run(req.dict())

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Agentic AI Test Generator</title>
  <style>
    body { font-family: Arial; margin: 40px; }
    input, textarea, button { width: 100%; margin: 10px 0; padding: 8px; }
    pre { background: #f4f4f4; padding: 15px; white-space: pre-wrap; }
    .pass { color: green; font-weight: bold; }
    .fail { color: red; font-weight: bold; }
  </style>
</head>
<body>

<h2>Agentic AI – Automated Test Case Generator</h2>

<label>Application URL</label>
<input id="appUrl" placeholder="http://app-url" />

<label>JIRA Story URL</label>
<input id="jiraUrl" placeholder="http://jira-story" />

<label>Cucumber Repo URL</label>
<input id="cucumberRepo" placeholder="http://bdd-repo" />

<button onclick="generate()">Generate Test Cases</button>

<h3>Generated Artifacts</h3>
<pre id="output"></pre>

<h3>Validation Status</h3>
<div id="validation"></div>

<script>
async function generate() {
  document.getElementById("output").textContent = "Generating...";
  document.getElementById("validation").textContent = "";

  const payload = {
    appUrl: document.getElementById("appUrl").value,
    appRepo: "",
    jiraUrl: document.getElementById("jiraUrl").value,
    cucumberRepo: document.getElementById("cucumberRepo").value
  };

  const res = await fetch("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  document.getElementById("output").textContent =
    data.generatedArtifacts || JSON.stringify(data, null, 2);

  if (data.validationReport) {
    const status = data.validationReport.status;
    document.getElementById("validation").innerHTML =
      `<span class="${status === 'PASS' ? 'pass' : 'fail'}">${status}</span>`;
  }
}
</script>

</body>
</html>
"""

