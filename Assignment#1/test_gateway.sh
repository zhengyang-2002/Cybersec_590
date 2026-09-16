#!/usr/bin/env bash
# 测试任意 OpenAI 兼容网关。
# 用法：./test_gateway.sh [DeepseekAPI.txt|DukeAiGateway.txt] [模型名]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
CFG="$DIR/${1:-DeepseekAPI.txt}"
MODEL="${2:-deepseek-chat}"
BASE_URL=$(grep '^baseURL:' "$CFG" | cut -d: -f2- | tr -d '[:space:]' | sed 's#/v1$##')
KEY=$(grep '^key:' "$CFG" | cut -d: -f2- | tr -d '[:space:]')

echo "== 1. 列出可用模型 ($BASE_URL) =="
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
echo "== 2. 对话请求 ($MODEL) =="
curl -s --max-time 60 "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"用一句话介绍你自己\"}], \"max_tokens\": 100}" \
  | python3 -c '
import sys, json
d = json.load(sys.stdin)
if "choices" in d:
    print("model:", d.get("model"))
    print("reply:", d["choices"][0]["message"]["content"])
else:
    print(json.dumps(d, indent=2, ensure_ascii=False)[:800])
'
