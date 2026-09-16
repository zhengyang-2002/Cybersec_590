#!/usr/bin/env bash
# Smoke-test any OpenAI-compatible gateway with curl.
# Usage: ./test_gateway.sh [DeepseekAPI.txt|DukeAiGateway.txt] [model-name]
# The config file must contain two lines: "baseURL:<url>" and "key:<api-key>".
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
CFG="$DIR/${1:-DeepseekAPI.txt}"
MODEL="${2:-deepseek-flash}"
BASE_URL=$(grep '^baseURL:' "$CFG" | cut -d: -f2- | tr -d '[:space:]' | sed 's#/v1$##')
KEY=$(grep '^key:' "$CFG" | cut -d: -f2- | tr -d '[:space:]')

echo "== 1. List available models ($BASE_URL) =="
curl -s --max-time 30 -w "\nHTTP_STATUS:%{http_code}\n" "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $KEY" \
  | python3 -c '
import sys, json
raw = sys.stdin.read()
body, _, status = raw.rpartition("HTTP_STATUS:")
print("HTTP", status.strip())
try:
    d = json.loads(body)
    for m in sorted(x["id"] for x in d.get("data", [])): print("  ", m)
    if "data" not in d: print(json.dumps(d, indent=2)[:500])
except Exception:
    print(body[:500])
'

echo
echo "== 2. Chat completion ($MODEL) =="
curl -s --max-time 60 "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Introduce yourself in one sentence.\"}], \"max_tokens\": 100, \"thinking\": {\"type\": \"disabled\"}}" \
  | python3 -c '
import sys, json
d = json.load(sys.stdin)
if "choices" in d:
    print("model:", d.get("model"))
    print("reply:", d["choices"][0]["message"]["content"])
else:
    print(json.dumps(d, indent=2)[:800])
'
