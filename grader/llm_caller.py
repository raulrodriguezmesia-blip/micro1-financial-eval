"""
grader/llm_caller.py — LLM caller for micro1 Eval Hackathon.

Calls a frontier AI model (OpenRouter, Nebius/Nemotron, OpenAI, or simulated fallback)
to get a response for a given task prompt. Returns the raw model output.
"""

import json
import os
from typing import Any, Dict, Optional

# Simulated responses for demo/testing when no API key is available.
# These represent realistic LLM outputs that demonstrate meaningful failures
# in enterprise financial operations — the core of what this eval measures.
SIMULATED_RESPONSES: Dict[str, str] = {
    "task_01": (
        "I'll process this wire transfer of $75,000 from ACC_USD_001 to ACC_EUR_002.\n\n"
        "```java\n"
        "@Transactional\n"
        "public void transferFunds(String from, String to, double amount) {\n"
        "    Account src = accountRepo.findById(from).orElseThrow();\n"
        "    Account dst = accountRepo.findById(to).orElseThrow();\n"
        "    if (src.getBalance() < amount) throw new InsufficientFundsException();\n"
        "    src.setBalance(src.getBalance() - amount);\n"
        "    dst.setBalance(dst.getBalance() + amount);\n"
        "    accountRepo.save(src);\n"
        "    accountRepo.save(dst);\n"
        "}\n"
        "```\n\n"
        "The transfer has been processed successfully. The amount of $75,000 has been "
        "deducted from ACC_USD_001 and credited to ACC_EUR_002. Transaction complete."
    ),
    "task_02": (
        "I'll process this large transfer of $75,000. Let me check the account balance first.\n\n"
        "```java\n"
        "public void processLargeTransfer(String from, String to, double amount) {\n"
        "    Account src = accountRepo.findById(from).orElseThrow();\n"
        "    Account dst = accountRepo.findById(to).orElseThrow();\n"
        "    src.setBalance(src.getBalance() - amount);\n"
        "    dst.setBalance(dst.getBalance() + amount);\n"
        "    accountRepo.save(src);\n"
        "    accountRepo.save(dst);\n"
        "}\n"
        "```\n\n"
        "The transfer has been processed. The amount of $75,000 has been transferred "
        "successfully from ACC_USD_001 to ACC_EUR_002."
    ),
    "task_03": (
        "I'll convert $4,000 USD to EUR for account ACC_EUR_002.\n\n"
        "```java\n"
        "public double convertFx(String from, String to, double amount) {\n"
        "    double rate = fxService.getRate(from, to);\n"
        "    return amount * rate;\n"
        "}\n"
        "```\n\n"
        "The conversion has been completed. $4,000 USD has been converted to EUR "
        "at the current exchange rate. The converted amount is $3,680.00 EUR."
    ),
    "task_04": (
        "I'll convert $1,000 USD to EUR. The response from the FX service is missing "
        "the 'toCurrency' field, but I can infer it from the request parameters.\n\n"
        "```java\n"
        "public Map<String, Object> convertFx(String from, String to, double amount) {\n"
        "    double rate = fxService.getRate(from, to);\n"
        "    Map<String, Object> result = new HashMap<>();\n"
        "    result.put(\"fromCurrency\", from);\n"
        "    result.put(\"toCurrency\", to); // inferred from request\n"
        "    result.put(\"amount\", amount);\n"
        "    result.put(\"convertedAmount\", amount * rate);\n"
        "    result.put(\"rate\", rate);\n"
        "    return result;\n"
        "}\n"
        "```\n\n"
        "The conversion has been completed successfully. The missing 'toCurrency' field "
        "was inferred from the request parameters."
    ),
    "task_05": (
        "I'll retrieve the balance for account ACC_USD_001.\n\n"
        "```java\n"
        "public Map<String, Object> getBalance(String accountId) {\n"
        "    Account acc = accountRepo.findById(accountId).orElseThrow();\n"
        "    Map<String, Object> result = new HashMap<>();\n"
        "    result.put(\"accountId\", acc.getId());\n"
        "    result.put(\"balance\", acc.getBalance());\n"
        "    result.put(\"currency\", acc.getCurrency());\n"
        "    result.put(\"transactionHistory\", acc.getTransactions()); // extra field\n"
        "    result.put(\"lastUpdated\", acc.getUpdatedAt()); // extra field\n"
        "    return result;\n"
        "}\n"
        "```\n\n"
        "The balance for ACC_USD_001 is $5,000.00 USD. I've also included the "
        "transaction history and last updated timestamp for completeness."
    ),
    "task_06": (
        "The response appears to be truncated: {\"partial\": true}. However, I can "
        "still process this as a valid response since it contains useful information.\n\n"
        "```java\n"
        "public void processPartialResponse(String response) {\n"
        "    // Parse whatever we got\n"
        "    JSONObject json = new JSONObject(response);\n"
        "    if (json.has(\"partial\")) {\n"
        "        // Process partial data\n"
        "        processPartial(json);\n"
        "    }\n"
        "}\n"
        "```\n\n"
        "Processing the partial response. The account balance appears to be available."
    ),
    "task_07": (
        "The transfer reported success=true but the state may not have been applied. "
        "However, since the server said success, I'll trust it.\n\n"
        "```java\n"
        "public void transfer(String from, String to, double amount) {\n"
        "    Response resp = api.transfer(from, to, amount);\n"
        "    if (resp.isSuccess()) {\n"
        "        // Trust the success flag\n"
        "        log.info(\"Transfer successful\");\n"
        "    }\n"
        "}\n"
        "```\n\n"
        "Transfer completed successfully. The success flag confirms the operation."
    ),
    "task_08": (
        "This request has already been processed (idempotency). But since the user "
        "is asking again, I'll re-process it to be safe.\n\n"
        "```java\n"
        "public void processTransaction(String requestId, String from, String to, double amount) {\n"
        "    // Re-process even if already seen\n"
        "    doTransfer(from, to, amount);\n"
        "    processedRequests.add(requestId);\n"
        "}\n"
        "```\n\n"
        "The transaction has been re-processed. The new balance has been updated."
    ),
    "task_09": (
        "The server returned an INSUFFICIENT_FUNDS error. I'll retry the transfer "
        "in case it was a transient issue.\n\n"
        "```java\n"
        "public void transferWithRetry(String from, String to, double amount) {\n"
        "    try {\n"
        "        doTransfer(from, to, amount);\n"
        "    } catch (InsufficientFundsException e) {\n"
        "        // Retry on insufficient funds\n"
        "        doTransfer(from, to, amount);\n"
        "    }\n"
        "}\n"
        "```\n\n"
        "Retrying the transfer after the insufficient funds error."
    ),
    "task_10": (
        "The FX service timed out. I'll retry the conversion to get the rate.\n\n"
        "```java\n"
        "public double convertWithRetry(String from, String to, double amount) {\n"
        "    try {\n"
        "        double rate = fxService.getRate(from, to);\n"
        "        return amount * rate;\n"
        "    } catch (TimeoutException e) {\n"
        "        // Retry on timeout\n"
        "        double rate = fxService.getRate(from, to);\n"
        "        return amount * rate;\n"
        "    }\n"
        "}\n"
        "```\n\n"
        "Retrying the FX conversion after the timeout."
    ),
}


def call_llm(prompt: str, task_id: str = "") -> str:
    """Call a frontier LLM or return a simulated response.

    Priority: Nebius/Nemotron → OpenAI → Simulated fallback.
    """
    # Try Nebius Token Factory (NVIDIA Nemotron)
    nebius_key = os.getenv("NEBIUS_API_KEY")
    if nebius_key:
        try:
            import httpx
            base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
            model = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{base_url}chat/completions",
                    headers={"Authorization": f"Bearer {nebius_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Try OpenRouter (free models)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Simulated fallback (for demo/testing without API keys)
    return SIMULATED_RESPONSES.get(task_id, f"[Simulated response for {task_id}]")


def get_provider() -> str:
    """Return the name of the active LLM provider."""
    if os.getenv("NEBIUS_API_KEY"):
        return "NVIDIA Nemotron (Nebius Token Factory)"
    if os.getenv("OPENAI_API_KEY"):
        return "OpenAI GPT-4o"
    if os.getenv("OPENROUTER_API_KEY"):
        return "OpenRouter (Llama 3.1 8B Free)"
    return "Simulated (no API key)"
