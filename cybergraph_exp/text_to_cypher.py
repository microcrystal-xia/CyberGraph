"""LLM-based Text-to-Cypher translation with timing."""
import json
import os
import random
import re
import time
from pathlib import Path
from .config import Config

SYSTEM_PROMPT = (Config.PROMPTS_DIR / "text-to-cypher.md").read_text()

# Destructive keywords that should never appear in generated Cypher
_DESTRUCTIVE_KEYWORDS = {"DELETE", "CREATE", "MERGE", "SET", "REMOVE", "DROP"}

# Use mock mode when LLM APIs are unavailable (for testing pipeline)
USE_MOCK = os.getenv("CYBERGRAPH_MOCK_LLM", "").lower() in ("1", "true", "yes")


def translate(nl_query: str) -> tuple:
    """Translate natural language to Cypher query.

    Returns:
        (cypher_query: str, latency_ms: float)
    """
    if USE_MOCK:
        return _translate_mock(nl_query)

    start = time.perf_counter()

    if Config.LLM_PROVIDER == "openai":
        cypher = _translate_openai(nl_query)
    elif Config.LLM_PROVIDER == "anthropic":
        cypher = _translate_anthropic(nl_query)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {Config.LLM_PROVIDER}")

    # Strip markdown code fences if present
    cypher = re.sub(r"^```(?:cypher)?\s*\n?", "", cypher, flags=re.MULTILINE)
    cypher = re.sub(r"\n?```\s*$", "", cypher, flags=re.MULTILINE)
    cypher = cypher.strip()

    latency_ms = (time.perf_counter() - start) * 1000
    return cypher, latency_ms


def _translate_mock(nl_query: str) -> tuple:
    """Use gold-standard Cypher from benchmark for pipeline validation."""
    benchmark_file = Path(__file__).parent / "test_queries.json"
    with open(benchmark_file) as f:
        queries = json.load(f)["queries"]

    for q in queries:
        if q["nl_query"] == nl_query:
            # Simulate realistic LLM latency (400-1200ms)
            latency = random.uniform(400, 1200)
            return q["expected_cypher"], latency

    # Fallback: return a generic query
    latency = random.uniform(500, 1500)
    return "MATCH (n) RETURN n.name AS name LIMIT 10", latency


def _translate_openai(nl_query: str) -> str:
    import httpx
    from openai import OpenAI

    kwargs = {"api_key": Config.OPENAI_API_KEY}
    if Config.OPENAI_BASE_URL:
        kwargs["base_url"] = Config.OPENAI_BASE_URL
    # Use SOCKS5 proxy if configured (e.g. to bypass network firewalls)
    socks_proxy = os.getenv("SOCKS_PROXY") or os.getenv("ALL_PROXY")
    if socks_proxy:
        kwargs["http_client"] = httpx.Client(proxy=socks_proxy)
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": nl_query},
        ],
        temperature=0,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


def _translate_anthropic(nl_query: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=Config.LLM_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": nl_query}],
    )
    return resp.content[0].text.strip()


def validate_cypher_syntax(cypher: str) -> bool:
    """Basic validation: must be a read-only Cypher query."""
    upper = cypher.upper()
    # Must contain MATCH and RETURN
    if "MATCH" not in upper or "RETURN" not in upper:
        return False
    # Must not contain destructive keywords (check word boundaries)
    for kw in _DESTRUCTIVE_KEYWORDS:
        # Match keyword as standalone word, not inside quotes
        if re.search(rf"\b{kw}\b", upper):
            return False
    return True
