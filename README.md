# Agentic Test Generation Framework

## Local Setup
1. python -m venv venv
2. activate venv
3. pip install -r requirements.txt

## Run Services
uvicorn orchestrator.app:app --port 8000
uvicorn mcp_ui.app:app --port 8001
uvicorn mcp_jira.app:app --port 8002
uvicorn mcp_bdd.app:app --port 8003
