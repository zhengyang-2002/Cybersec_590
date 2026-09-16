"""Smoke-test any OpenAI-compatible gateway (DeepSeek or Duke) with the openai SDK.

This mirrors how the assignment app reads its configuration: from environment
variables only, never from source code.

Usage:
    cp .env.example .env        # fill in your key
    set -a; source .env; set +a
    python3 test_gateway.py
"""

import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
)
model = os.environ.get("LLM_MODEL", "deepseek-flash")

print("== Available models ==")
for m in sorted(m.id for m in client.models.list().data):
    print("  ", m)

print(f"\n== Chat test ({model}) ==")
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Introduce yourself in one sentence."}],
    max_tokens=100,
    extra_body={"thinking": {"type": "disabled"}},  # DeepSeek: skip chain-of-thought
)
print(resp.choices[0].message.content)
