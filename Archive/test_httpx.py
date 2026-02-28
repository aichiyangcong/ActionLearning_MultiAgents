#!/usr/bin/env python3
"""使用自定义 headers 测试 API"""

import httpx
import json

api_key = "cr_4ecddb1343efd9ac49c7be9865b183f039f1632b7269e74a0ad7cc13b2eff952"
base_url = "https://aicode.life/api"

print("=" * 70)
print("使用 httpx 直接测试 API")
print("=" * 70)

try:
    # 使用 httpx 直接发送请求
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "你好，请用一句话介绍你自己。"}]
            },
            timeout=30.0,
        )

        print(f"\n状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 请求成功!")
            print(f"响应: {result['content'][0]['text']}")
        else:
            print(f"❌ 请求失败")
            print(f"响应: {response.text}")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
