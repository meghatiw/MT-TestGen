from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<html>
<head>
  <title>Agentic AI UI</title>
  <style>
    body { font-family: Arial; padding: 25px; }
    textarea { width:100%; height:170px; }
    input { width:100%; padding:8px; margin-bottom:10px; }
    button { padding:10px 14px; }
  </style>
</head>
<body>

<h2>Agentic AI – Test Generator</h2>

<label>JIRA Story</label>
<input id="jira">

<label>UI Repo</label>
<input id="ui">

<label>E2E Repo</label>
<input id="e2e">

<button onclick="generate()">Generate</button>
<pre id="output" style="display:none;"></pre>


<pre id="output" style="display:none;"></pre>

<div id="block" style="display:none;">
  <h3>Feature</h3>
  <textarea id="feature"></textarea>

  <h3>Steps</h3>
  <textarea id="steps"></textarea>

  <h3>Validation</h3>
  <textarea id="validation"></textarea>
</div>

<script>
async function generate() {
  const out = document.getElementById("output");
  out.style.display = "block";
  out.textContent = "Generating...";

  const payload = {
    jiraUrl: document.getElementById("jira").value,
    uiRepo: document.getElementById("ui").value,
    e2eRepo: document.getElementById("e2e").value
  };

const res = await fetch("http://localhost:8000/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
});


  const data = await res.json();
  out.style.display = "none";

  document.getElementById("block").style.display = "block";

  if (data.generatedArtifacts) {
    document.getElementById("feature").value = data.generatedArtifacts.feature || "";
    document.getElementById("steps").value   = data.generatedArtifacts.steps || "";
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
