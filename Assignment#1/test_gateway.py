"""用 openai 官方 SDK 调任意 OpenAI 兼容网关（DeepSeek 或 Duke）。
这也是作业里应用代码的标准写法：配置只从环境变量读。

用法：
    cp .env.example .env   # 填入自己的 key
    set -a; source .env; set +a
    python3 test_gateway.py
"""
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
)
model = os.environ.get("LLM_MODEL", "deepseek-chat")

print("== 可用模型 ==")
for m in sorted(m.id for m in client.models.list().data):
    print("  ", m)

print(f"\n== 对话测试 ({model}) ==")
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "用一句话介绍你自己"}],
    max_tokens=100,
)
print(resp.choices[0].message.content)
