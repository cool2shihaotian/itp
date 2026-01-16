"""
简化版：不使用 stealth，直接监听请求
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime


async def capture_simple():
    """最简单的捕获方式"""

    print("=" * 70)
    print("🔍 NOL Token 抓取工具（简化版）")
    print("=" * 70)
    print("\n使用说明:")
    print("1. 浏览器会自动打开")
    print("2. 访问 world.nol.com")
    print("3. 手动完成登录（包括 Cloudflare）")
    print("4. 登录成功后按 Ctrl+C")
    print("5. 查看生成的 JSON 文件")
    print("\n" + "=" * 70)

    captured_data = {
        'requests': [],
        'token_responses': [],
        'cookies': []
    }

    async with async_playwright() as p:
        # 使用持久化上下文
        user_data_dir = Path('/tmp/playwright_simple_profile')
        user_data_dir.mkdir(exist_ok=True)

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )

        # 获取或创建页面
        if len(browser.pages) > 0:
            page = browser.pages[0]
        else:
            page = await browser.new_page()

        # 监听请求
        def log_request(request):
            url = request.url

            # 只记录 API 请求
            if any(keyword in url for keyword in ['/api/', 'identitytoolkit', 'firebase']):
                req_data = {
                    'url': url,
                    'method': request.method,
                    'time': datetime.now().strftime('%H:%M:%S')
                }

                # 获取请求体
                try:
                    post_data = request.post_data
                    if post_data:
                        req_data['body'] = post_data[:800]
                except:
                    pass

                captured_data['requests'].append(req_data)

                marker = "🔑" if any(k in url.lower() for k in ['auth', 'login', 'token', 'signin']) else "📤"
                print(f"{marker} [{req_data['method']}] {url[:70]}")

                if 'body' in req_data:
                    print(f"   → {req_data['body'][:80]}...")

        # 监听响应
        async def log_response(response):
            url = response.url

            # 只处理 API 响应
            if any(keyword in url for keyword in ['/api/', 'identitytoolkit', 'firebase']):
                status = response.status
                print(f"📥 [{status}] {url[:70]}")

                # 检查是否包含 token
                try:
                    text = await response.text()

                    # 检查 token 关键字
                    if any(kw in text for kw in ['access_token', 'idToken', '"token"', 'accessToken']):
                        print(f"   ⭐⭐⭐ 发现 TOKEN！⭐⭐⭐")
                        print(f"   内容预览: {text[:300]}...")

                        token_data = {
                            'url': url,
                            'status': status,
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'response': text[:2000]
                        }

                        # 尝试解析 JSON
                        try:
                            json_data = json.loads(text)
                            token_data['json'] = json_data
                        except:
                            pass

                        captured_data['token_responses'].append(token_data)

                except:
                    pass

        # 注册监听器
        page.on('request', log_request)
        page.on('response', log_response)

        # 访问首页
        print("\n🌐 正在打开浏览器...")
        try:
            await page.goto('https://world.nol.com/zh-CN', timeout=60000)
            print("✅ 页面加载成功\n")
        except Exception as e:
            print(f"⚠️ 页面加载问题: {e}")
            print("   浏览器仍然打开，请继续操作\n")

        print("=" * 70)
        print("⏳ 请在浏览器中手动完成登录...")
        print("   如果出现 Cloudflare 验证，请手动完成")
        print("   所有 API 请求会被自动捕获")
        print("   登录成功后，按 Ctrl+C 停止抓取")
        print("=" * 70 + "\n")

        # 等待用户操作
        try:
            await asyncio.sleep(300)
        except KeyboardInterrupt:
            print("\n\n⏹️ 抓取已停止")

        # 获取 cookies
        print("\n🍪 获取 Cookies...")
        cookies = await browser.cookies()
        captured_data['cookies'] = cookies

        # 查找 access_token
        for cookie in cookies:
            if cookie['name'] == 'access_token':
                print(f"✅ 找到 access_token: {cookie['value'][:60]}...")
                captured_data['nol_access_token'] = cookie['value']

        await browser.close()

    # 保存结果
    output_dir = Path(__file__).parent.parent / "captures"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"capture_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(captured_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("📊 抓取统计:")
    print("=" * 70)
    print(f"总请求数: {len(captured_data['requests'])}")
    print(f"包含 token 的响应: {len(captured_data['token_responses'])}")
    print(f"Cookies: {len(captured_data['cookies'])}")
    print(f"\n✅ 已保存到: {output_file}")

    if 'nol_access_token' in captured_data:
        print(f"\n✅ 成功获取 NOL Token:")
        print(f"   {captured_data['nol_access_token']}")

    if captured_data['token_responses']:
        print("\n🔑 包含 Token 的响应:")
        for i, resp in enumerate(captured_data['token_responses'], 1):
            print(f"{i}. {resp['url']}")

    print("\n" + "=" * 70)
    print("✅ 完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(capture_simple())
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序被中断")
