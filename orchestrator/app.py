import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from orchestrator.agent import TestGenerationAgent

# ======================================================
# LOGGING
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================================================
# APP
# ======================================================
app = FastAPI(title="Agentic AI Test Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# MODELS
# ======================================================
class GenerateRequest(BaseModel):
    jiraUrl: str
    uiRepo: str = ""
    e2eRepo: str = ""


class PushExecuteRequest(BaseModel):
    feature: str
    selenium: str


# ======================================================
# GENERATE (STEP 1)
# ======================================================
@app.post("/generate")
async def generate(req: GenerateRequest):

    result = await TestGenerationAgent().run(req.dict())

    return JSONResponse(content=result)

# ======================================================
# PUSH ONLY (STEP 2)
# ======================================================
@app.post("/push-and-execute")
def push_and_execute(req: PushExecuteRequest):

    response = requests.post(
        "http://localhost:8004/push-e2e",
        json={
            "feature_content": req.feature,
            "selenium_code": req.selenium
        }
    )

    return response.json()


# ======================================================
# POLL STATUS
# ======================================================
@app.get("/execution-status")
def execution_status(branch: str):

    resp = requests.get(
        "http://localhost:8004/ci-status",
        params={"branch": branch}
    )

    return resp.json()


# ======================================================
# SIMPLE UI
# ======================================================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Agentic AI Test Generator</title>
</head>
<body>

<h2>Agentic AI – Autonomous E2E Execution</h2>

<label>JIRA URL</label>
<input id="jiraUrl" style="width:100%">

<label>UI Repo</label>
<input id="uiRepo" style="width:100%">

<button onclick="generate()">Generate</button>
<button onclick="execute()">Execute</button>

<h3>Feature</h3>
<textarea id="feature" style="width:100%;height:150px"></textarea>

<h3>Selenium</h3>
<textarea id="steps" style="width:100%;height:150px"></textarea>

<h3>Status</h3>
<div id="status"></div>

<script>
let feature = "";
let steps = "";
let branch = "";

async function generate() {
  const res = await fetch("/generate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      jiraUrl: document.getElementById("jiraUrl").value,
      uiRepo: document.getElementById("uiRepo").value
    })
  });

  const data = await res.json();

  if (data.generatedArtifacts) {
    feature = data.generatedArtifacts.feature;
    steps = data.generatedArtifacts.steps;
    document.getElementById("feature").value = feature;
    document.getElementById("steps").value = steps;
  }
}

async function execute() {

  const res = await fetch("/push-and-execute", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      feature: feature,
      selenium: steps
    })
  });

  const data = await res.json();
  branch = data.branch;

  document.getElementById("status").innerHTML =
    "PR Created: <a target='_blank' href='" +
    data.pull_request + "'>View PR</a><br>Running CI...";

  poll();
}

async function poll() {
  const interval = setInterval(async () => {
    const res = await fetch("/execution-status?branch=" + branch);
    const data = await res.json();

    if (data.conclusion === "success") {
      clearInterval(interval);
      document.getElementById("status").innerHTML += "<br><b style='color:green'>PASSED</b>";
    }

    if (data.conclusion === "failure") {
      clearInterval(interval);
      document.getElementById("status").innerHTML += "<br><b style='color:red'>FAILED</b>";
    }

  }, 10000);
}
</script>

</body>
</html>
"""
