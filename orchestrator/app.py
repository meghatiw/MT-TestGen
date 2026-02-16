import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from orchestrator.agent import TestGenerationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic AI Test Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    jiraUrl: str
    uiRepo: str
    e2eRepo: str

class PushExecuteRequest(BaseModel):
    feature: str
    selenium: str


# ================= GENERATE =================
@app.post("/generate")
async def generate(req: GenerateRequest):
    logger.info(f"Received payload: {req.dict()}")
    result = await TestGenerationAgent().run(req.dict())
    return JSONResponse(content=result)


# ================= PUSH =================
@app.post("/push")
def push(req: PushExecuteRequest):
    response = requests.post(
        "http://localhost:8004/push-e2e",
        json={
            "feature_content": req.feature,
            "selenium_code": req.selenium
        }
    )
    return response.json()


# ================= UI =================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Agentic AI – Two Step Execution</title>
  <style>
    body { font-family: Arial; margin: 40px; }
    textarea { width: 100%; height: 160px; }
    input { width: 100%; margin-bottom: 10px; }
    button { padding: 8px 16px; margin-right: 10px; }
    .disabled { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>

<h2>Agentic AI – Two Step E2E Execution</h2>

<label>JIRA URL</label>
<input id="jiraUrl">

<label>UI Repo</label>
<input id="uiRepo">

<label>E2E Repo</label>
<input id="e2eRepo">

<br><br>

<button onclick="generate()">Generate Test Cases</button>
<button id="pushBtn" disabled class="disabled" onclick="push()">Push to E2E</button>

<h3>Feature</h3>
<textarea id="feature"></textarea>

<h3>Java</h3>
<textarea id="steps"></textarea>

<h3>Validation</h3>
<textarea id="validation"></textarea>

<h3>Status</h3>
<div id="status"></div>

<script>

let featureContent = "";
let seleniumContent = "";

function enablePush() {
  const btn = document.getElementById("pushBtn");
  btn.disabled = false;
  btn.classList.remove("disabled");
}

function disablePush() {
  const btn = document.getElementById("pushBtn");
  btn.disabled = true;
  btn.classList.add("disabled");
}

async function generate() {

  disablePush();

  document.getElementById("feature").value = "Generating...";
  document.getElementById("steps").value = "";
  document.getElementById("validation").value = "";
  document.getElementById("status").innerHTML = "";

  const res = await fetch("/generate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      jiraUrl: document.getElementById("jiraUrl").value,
      uiRepo: document.getElementById("uiRepo").value,
      e2eRepo: document.getElementById("e2eRepo").value
    })
  });

  const data = await res.json();

  if (data.status === "SUCCESS") {

    featureContent = data.generatedArtifacts.feature || "";
    seleniumContent = data.generatedArtifacts.steps || "";

    document.getElementById("feature").value = featureContent;
    document.getElementById("steps").value = seleniumContent;

    if (featureContent.length > 10 && seleniumContent.length > 10) {
        enablePush();
    }

  } else {
    alert("Generation failed: " + data.message);
  }

  if (data.validationReport) {
    document.getElementById("validation").value =
      JSON.stringify(data.validationReport, null, 2);
  }
}

async function push() {

  if (!featureContent || !seleniumContent) {
    alert("Generate tests first!");
    return;
  }

  document.getElementById("status").innerHTML = "Pushing to E2E repo...";

  const res = await fetch("/push", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      feature: featureContent,
      selenium: seleniumContent
    })
  });

  const data = await res.json();

  document.getElementById("status").innerHTML =
    "PR Created: <a target='_blank' href='" +
    data.pull_request + "'>View PR</a>";
}

</script>

</body>
</html>
"""
