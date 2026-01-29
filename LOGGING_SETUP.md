# Detailed Logging Setup

## Overview
Comprehensive logging has been added to track the entire test generation pipeline with detailed DEBUG, INFO, WARNING, and ERROR level logs.

## Log Output
- **Console**: Real-time logs printed to terminal
- **File**: All logs saved to `orchestrator.log` in the project root

## Log Format
```
[timestamp] - [module_name] - [LOG_LEVEL] - [filename:line_number] - [message]
```

Example:
```
2026-01-29 10:15:23,456 - orchestrator.app - INFO - [app.py:43] - NEW TEST GENERATION REQUEST | Timestamp: 2026-01-29T10:15:23.456789
```

## Modules with Logging

### 1. orchestrator/app.py
Logs API requests and responses:
- Health check requests
- Test generation request details (Jira URL, repos)
- Generation completion status
- Error messages

### 2. orchestrator/agent.py
Detailed logs for the entire pipeline:
- **Context Retrieval**: JIRA story, UI selectors, E2E repo
- **Gherkin Generation**: Prompt size, output size
- **Selenium Generation**: Prompt size, output size
- **Validation**: Selector counts, validation results
- **Critic Review**: Review decisions, can_retry flag
- **Retry Logic**: Refined prompt generation, validation retry
- **Error Handling**: Exception details with full stack trace

### 3. orchestrator/llm.py
LLM interactions:
- LLM model name and request initiation
- Prompt size and request payload
- Response status and size
- Full response content
- Timeout and network errors
- JSON parsing errors

## Log Levels Used

| Level | Purpose | Examples |
|-------|---------|----------|
| **DEBUG** | Detailed diagnostic info | Prompts, full outputs, request/response details |
| **INFO** | General informational | Pipeline steps, context retrieval, success messages |
| **WARNING** | Warning conditions | Invalid selectors found, retries triggered |
| **ERROR** | Error conditions | Network failures, validation failures, exceptions |

## Key Information Logged

### Pipeline Execution
- Request parameters (Jira URL, repo URLs)
- Each major step (Gherkin generation, Selenium generation, validation)
- Time to completion for each step
- Final status (SUCCESS/ERROR)

### Context Data
- JIRA story details
- UI element count and details
- E2E repo availability

### Generated Artifacts
- Gherkin feature file (full content at DEBUG level)
- Selenium code (full content at DEBUG level)
- Validation results (selectors used, invalid selectors)

### Error Information
- Exception messages with context
- HTTP status codes and responses
- Network timeouts
- Missing or invalid data

## Example Log Output

```
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:46] - ================================================================================
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:47] - NEW TEST GENERATION REQUEST | Timestamp: 2026-01-29T10:15:23.123456
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:48] -   JIRA URL: https://megha-tiwari.atlassian.net/browse/KAN-3
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:49] -   UI Repo: https://github.com/meghatiw/megha-bank-ui.git
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:50] -   E2E Repo: https://github.com/meghatiw/megha-e2e-tests.git
2026-01-29 10:15:23 - orchestrator.app - INFO - [app.py:51] - ================================================================================
2026-01-29 10:15:23 - orchestrator.agent - INFO - [agent.py:32] - Starting test generation pipeline
2026-01-29 10:15:23 - orchestrator.agent - INFO - [agent.py:35] - Fetching JIRA context for: https://megha-tiwari.atlassian.net/browse/KAN-3
2026-01-29 10:15:24 - orchestrator.agent - INFO - [agent.py:41] - JIRA context retrieved successfully. Story ID: KAN-3
2026-01-29 10:15:24 - orchestrator.agent - INFO - [agent.py:45] - Fetching UI context from repo: https://github.com/meghatiw/megha-bank-ui.git
2026-01-29 10:15:25 - orchestrator.agent - INFO - [agent.py:51] - UI context retrieved successfully
2026-01-29 10:15:25 - orchestrator.agent - INFO - [agent.py:54] - Total UI elements found: 12
2026-01-29 10:15:25 - orchestrator.agent - INFO - [agent.py:61] - Fetching E2E context from repo: https://github.com/meghatiw/megha-e2e-tests.git
2026-01-29 10:15:26 - orchestrator.agent - INFO - [agent.py:67] - STEP 1: Generating Gherkin feature file
2026-01-29 10:15:26 - orchestrator.llm - INFO - [llm.py:20] - Calling LLM (Model: deepseek-coder:6.7b)
2026-01-29 10:15:45 - orchestrator.llm - INFO - [llm.py:47] - LLM response received successfully (1245 characters)
2026-01-29 10:15:45 - orchestrator.agent - INFO - [agent.py:73] - Gherkin generated successfully (1245 characters)
2026-01-29 10:15:45 - orchestrator.agent - INFO - [agent.py:79] - STEP 2: Generating Selenium step definitions
...
```

## Monitoring Logs

To monitor logs in real-time:
```bash
# Linux/Mac
tail -f orchestrator.log

# PowerShell
Get-Content -Path orchestrator.log -Wait -Tail 0
```

To search logs:
```bash
# Find all errors
grep ERROR orchestrator.log

# Find specific request
grep "KAN-3" orchestrator.log

# Get last 50 lines
tail -50 orchestrator.log
```

## Configuration

To adjust logging level, modify [orchestrator/app.py](orchestrator/app.py#L15):
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO, WARNING, ERROR as needed
    ...
)
```

Log levels from most verbose to least:
- `logging.DEBUG` - All details
- `logging.INFO` - Informational messages (default)
- `logging.WARNING` - Warning and error messages only
- `logging.ERROR` - Error messages only
