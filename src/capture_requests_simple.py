"""
简化版：抓取登录后的 API 请求
重点关注 NOL token 的获取
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
import yaml


async def capture_after_login():
    """在浏览器打开后等待用户手动登录，然后捕获所有请求"""

    # 读取配置
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    print("=" * 70)
    print("🔍 NOL Token 获取接口抓取工具")
    print("=" * 70)
    print(f"\n账号: {config['account']['username']}")
    print("\n使用说明:")
    print("1. 浏览器会自动打开并访问登录页面")
    print("2. 请手动完成登录（包括 Cloudflare 验证）")
    print("3. 登录成功后，按 Ctrl+C 继续捕获后续请求")
    print("4. 脚本会自动保存所有 API 请求到文件")
    print("\n" + "=" * 70)

    captured_requests = []
    responses_with_tokens = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN'
        )

        page = await context.new_page()

        # 保存请求和响应
        async def handle_request(request):
            url = request.url

            # 只捕获 API 请求
            if any(keyword in url for keyword in ['/api/', 'firebase', 'identitytoolkit']):
                req_info = {
                    'url': url,
                    'method': request.method,
                    'timestamp': datetime.now().isoformat(),
                    'headers': dict(request.headers)
                }

                # 获取请求体
                post_data = request.post_data
                if post_data:
                    try:
                        req_info['body'] = json.loads(post_data)
                    except:
                        req_info['body'] = post_data

                captured_requests.append(req_info)
                print(f"📤 [{request.method}] {url[:80]}")

        async def handle_response(response):
            url = response.url
            status = response.status

            # 只处理 API 响应
            if any(keyword in url for keyword in ['/api/', 'firebase', 'identitytoolkit']):
                print(f"📥 [{status}] {url[:80]}")

                # 检查响应中是否包含 token
                try:
                    text = await response.text()
                    if any(keyword in text for keyword in ['access_token', 'idToken', 'token']):
                        print(f"   ⭐⭐⭐ 发现 Token！⭐⭐⭐")

                        resp_info = {
                            'url': url,
                            'status': status,
                            'timestamp': datetime.now().isoformat(),
                            'response': text[:1000]  # 限制长度
                        }

                        # 尝试解析 JSON
                        try:
                            resp_info['json'] = json.loads(text)
                        except:
                            pass

                        responses_with_tokens.append(resp_info)

                        # 打印重要信息
                        try:
                            data = json.loads(text)
                            print(f"   内容: {json.dumps(data, indent=10)[:200]}...")
                        except:
                            print(f"   内容: {text[:200]}...")
                except:
                    pass

        # 注册监听器
        page.on('request', handle_request)
        page.on('response', handle_response)

        # 访问登录页面
        print("\n🌐 正在打开登录页面...")
        await page.goto('https://world.nol.com/zh-CN/login', wait_until='networkidle')

        print("\n✅ 页面已加载")
        print("\n" + "=" * 70)
        print("⏳ 请在浏览器中完成登录...")
        print("   登录成功后，等待页面跳转完成，然后按 Ctrl+C 继续捕获")
        print("=" * 70 + "\n")

        # 等待用户登录（60秒）
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n\n⏹️ 检测到中断，继续捕获后续请求...")

        print("\n⏳ 继续捕获 30 秒...")
        await asyncio.sleep(30)

        await browser.close()

    # 保存结果
    captures_dir = Path(__file__).parent.parent / "captures"
    captures_dir.mkdir(exist_ok=True)

    # 保存所有请求
    requests_file = captures_dir / "all_requests.json"
    with open(requests_file, 'w', encoding='utf-8') as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 所有请求已保存: {requests_file}")
    print(f"   共捕获 {len(captured_requests)} 个请求")

    # 保存包含 token 的响应
    if responses_with_tokens:
        tokens_file = captures_dir / "token_responses.json"
        with open(tokens_file, 'w', encoding='utf-8') as f:
            json.dump(responses_with_tokens, f, indent=2, ensure_ascii=False)

        print(f"\n✨ Token 响应已保存: {tokens_file}")
        print(f"   共发现 {len(responses_with_tokens)} 个包含 token 的响应")

        print("\n" + "=" * 70)
        print("🔑 包含 Token 的响应:")
        print("=" * 70)

        for i, resp in enumerate(responses_with_tokens, 1):
            print(f"\n{i}. {resp['url']}")
            print(f"   状态: {resp['status']}")
            if 'json' in resp:
                print(f"   内容: {json.dumps(resp['json'], indent=6)[:300]}...")
    else:
        print("\n⚠️ 未发现包含 token 的响应")

    # 分析可能的关键接口
    print("\n" + "=" * 70)
    print("🔍 可能的关键接口:")
    print("=" * 70)

    keywords = ['auth', 'login', 'token', 'signin', 'enter']
    for keyword in keywords:
        matching = [req for req in captured_requests if keyword in req['url'].lower()]
        if matching:
            print(f"\n关键词 '{keyword}':")
            for req in matching[:3]:  # 只显示前3个
                print(f"  - {req['url']}")
                if 'body' in req and req['body']:
                    print(f"    Body: {str(req['body'])[:150]}...")

    print("\n" + "=" * 70)
    print("✅ 抓取完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(capture_after_login())
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序被用户中断")
