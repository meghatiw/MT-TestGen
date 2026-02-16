import requests
import json
import logging
import time
import os
import re

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_HEALTH = "http://localhost:11434/api/tags"
MODEL = "deepseek-coder:1.3b"

FORCE_MOCK_MODE = os.getenv("FORCE_MOCK_MODE", "false").lower() == "true"

SYSTEM_PROMPT = (
    "You are a senior QA automation engineer. "
    "You generate Cucumber Gherkin scenarios and Selenium Java step definitions. "
    "You STRICTLY follow provided UI selectors and context. "
    "You NEVER invent selectors, messages, URLs, or logic."
)

# =========================================================
# ENTRY POINT
# =========================================================

def call_llm(prompt: str) -> str:

    ticket_key = extract_ticket_key(prompt)

    # 1️⃣ Force mock mode
    if FORCE_MOCK_MODE:
        logger.warning("FORCE_MOCK_MODE enabled")
        return mock_model(prompt, ticket_key)

    # 2️⃣ Try Ollama
    try:
        health = requests.get(OLLAMA_HEALTH, timeout=5)
        if health.status_code != 200:
            raise Exception("Ollama health failed")

        payload = {
            "model": MODEL,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": 0.2}
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=600)

        if response.status_code != 200:
            raise Exception("Ollama error")

        result = response.json().get("response", "").strip()

        if not result:
            raise Exception("Empty response")

        return result

    except Exception as e:
        logger.warning(f"Ollama failed → Using fallback. Reason: {e}")
        return mock_model(prompt, ticket_key)


# =========================================================
# MOCK MODEL
# =========================================================

def mock_model(prompt: str, ticket_key: str = None) -> str:

    logger.warning(f"Using deterministic fallback for ticket: {ticket_key}")

    is_step_generation = (
        "generate selenium" in prompt.lower()
        or "step definitions" in prompt.lower()
        or "output only java code" in prompt.lower()
    )

    if is_step_generation:
        return generate_steps(ticket_key)

    # Feature phase
    if ticket_key == "KAN-1":
        return BUY_FEATURE()

    if ticket_key == "KAN-3":
        return SELL_FEATURE()

    if ticket_key == "KAN-4":
        return CANCEL_FEATURE()

    if ticket_key == "KAN-5":
        return VIEW_LAST_5_FEATURE()

    return DEFAULT_FEATURE()


# =========================================================
# FEATURE MOCKS
# =========================================================

def BUY_FEATURE():
    return """
Feature: Create BUY transaction

  @buy
  Scenario: Create BUY transaction
    Given user is on Quick Trade screen
    When user enters quantity and price
    And user clicks Buy
    Then transaction response should be shown
""".strip()


def SELL_FEATURE():
    return """
Feature: Create SELL transaction

  @sell
  Scenario: Create SELL transaction
    Given user is on Quick Trade screen
    When user enters quantity and price
    And user clicks Sell
    Then transaction response should be shown
""".strip()


def CANCEL_FEATURE():
    return """
Feature: Cancel existing transaction

  @cancel
  Scenario: Cancel an existing trade
    Given user is on Quick Trade screen
    When I cancel the trade with reference "TR-E2E-2"
    Then transaction response should be shown
""".strip()


def VIEW_LAST_5_FEATURE():
    return """
Feature: View last 5 transactions

  @view
  Scenario: View last 5 transactions
    Given user is on Quick Trade screen
    When user clicks View Transactions
    Then last 5 transactions should be displayed
""".strip()


def DEFAULT_FEATURE():
    return """
Feature: Smoke Test

  Scenario: Basic health scenario
    Given user is on Quick Trade screen
    Then transaction response should be shown
""".strip()


# =========================================================
# STEP GENERATION
# =========================================================

def generate_steps(ticket_key: str):

    if ticket_key == "KAN-1":
        return BUY_STEPS()

    if ticket_key == "KAN-3":
        return SELL_STEPS()

    if ticket_key == "KAN-4":
        return CANCEL_STEPS()

    if ticket_key == "KAN-5":
        return VIEW_STEPS()

    return BUY_STEPS()


def BUY_STEPS():
    return """
package com.megha.bank.steps;

import io.cucumber.java.en.*;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import steps.Hooks;
import java.time.Duration;

public class BuySteps {

    @When("user enters quantity and price")
    public void user_enters_quantity_and_price() {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.visibilityOfElementLocated(
            By.cssSelector("[data-testid='quantity-input']")
        )).sendKeys("5");

        wait.until(ExpectedConditions.visibilityOfElementLocated(
            By.cssSelector("[data-testid='price-input']")
        )).sendKeys("50.0");
    }

    @When("user clicks Buy")
    public void user_clicks_buy() {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.elementToBeClickable(
            By.cssSelector("[data-testid='buy-btn']")
        )).click();
    }

    @Then("transaction response should be shown")
    public void transaction_response_should_be_shown() {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.visibilityOfElementLocated(
            By.cssSelector("[data-testid='response-body']")
        ));
    }
}
""".strip()


def SELL_STEPS():
    return BUY_STEPS().replace("Buy", "Sell").replace("buy-btn", "sell-btn")


def CANCEL_STEPS():
    return """
package com.megha.bank.steps;

import io.cucumber.java.en.*;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import steps.Hooks;
import java.time.Duration;

public class CancelSteps {

    @When("I cancel the trade with reference {string}")
    public void cancel_trade(String ref) {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.elementToBeClickable(
            By.cssSelector("[data-testid='cancel-btn']")
        )).click();
    }
}
""".strip()


def VIEW_STEPS():
    return """
package com.megha.bank.steps;

import io.cucumber.java.en.*;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import steps.Hooks;
import java.time.Duration;

public class ViewSteps {

    @When("user clicks View Transactions")
    public void view_transactions() {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.elementToBeClickable(
            By.cssSelector("[data-testid='view-transactions']")
        )).click();
    }

    @Then("last 5 transactions should be displayed")
    public void verify_last_5() {

        WebDriverWait wait = new WebDriverWait(Hooks.driver, Duration.ofSeconds(20));

        wait.until(ExpectedConditions.visibilityOfElementLocated(
            By.cssSelector("[data-testid='transaction-list']")
        ));
    }
}
""".strip()


# =========================================================
# UTIL
# =========================================================

def extract_ticket_key(prompt: str):
    match = re.search(r"/browse/([A-Z]+-\d+)", prompt)
    if match:
        return match.group(1)
    return None
