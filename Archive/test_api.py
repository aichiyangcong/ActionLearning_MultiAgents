#!/usr/bin/env python3
"""直接测试 Anthropic API"""

import anthropic

api_key = "cr_4ecddb1343efd9ac49c7be9865b183f039f1632b7269e74a0ad7cc13b2eff952"
base_url = "https://aicode.life/api"

print("=" * 70)
print("直接测试 Anthropic API")
print("=" * 70)

try:
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
    )

    print("\n发送测试请求...")
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "你好，请用一句话介绍你自己。"}
        ]
    )

    print(f"✅ 请求成功!")
    print(f"响应: {message.content[0].text}")

except Exception as e:
    print(f"❌ 请求失败: {e}")
    import traceback
    traceback.print_exc()
