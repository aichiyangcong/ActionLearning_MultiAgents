#!/usr/bin/env python3
"""详细测试 Anthropic API"""

import anthropic
import httpx

api_key = "cr_4ecddb1343efd9ac49c7be9865b183f039f1632b7269e74a0ad7cc13b2eff952"
base_url = "https://aicode.life/api"

print("=" * 70)
print("详细测试 Anthropic API")
print("=" * 70)
print(f"\nAPI Key: {api_key[:20]}...")
print(f"Base URL: {base_url}")
print(f"Model: claude-sonnet-4-5-20250929")

try:
    # 创建客户端
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        timeout=30.0,
    )

    print("\n发送测试请求...")

    # 尝试发送请求
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Hello"}
        ]
    )

    print(f"✅ 请求成功!")
    print(f"响应: {message.content[0].text}")

except anthropic.PermissionDeniedError as e:
    print(f"\n❌ 权限被拒绝: {e}")
    print(f"状态码: {e.status_code if hasattr(e, 'status_code') else 'N/A'}")
    print(f"响应体: {e.response if hasattr(e, 'response') else 'N/A'}")

except anthropic.AuthenticationError as e:
    print(f"\n❌ 认证失败: {e}")

except anthropic.APIError as e:
    print(f"\n❌ API 错误: {e}")
    print(f"状态码: {e.status_code if hasattr(e, 'status_code') else 'N/A'}")

except Exception as e:
    print(f"\n❌ 未知错误: {e}")
    print(f"错误类型: {type(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
