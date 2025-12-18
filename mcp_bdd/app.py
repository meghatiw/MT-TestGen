from fastapi import FastAPI

app = FastAPI(title="MCP BDD Server")

@app.get("/context")
def context(repo_url: str):
    return {
        "framework": "Cucumber + Selenium",
        "existingSteps": [
            "user is logged in",
            "user navigates to buy page"
        ]
    }
