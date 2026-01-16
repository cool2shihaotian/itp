"""
最终版：最简单直接的方式
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime


async def main():
    print("=" * 70)
    print("🔍 NOL Token 抓取工具")
    print("=" * 70)
    print("\n浏览器即将打开，请手动登录 world.nol.com")
    print("登录成功后按 Ctrl+C\n")

    captured_data = {
        'requests': [],
        'responses_with_tokens': [],
        'final_cookies': []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN',
        )
        page = await context.new_page()

        # 收集请求
        page.on('request', lambda request: captured_data['requests'].append({
            'url': request.url,
            'method': request.method,
            'time': datetime.now().strftime('%H:%M:%S')
        }) if '/api/' in request.url or 'firebase' in request.url else None)

        # 收集包含 token 的响应
        async def handle_response(response):
            if '/api/' in response.url or 'firebase' in response.url:
                try:
                    text = await response.text()
                    if any(kw in text for kw in ['access_token', 'idToken']):
                        print(f"⭐ 发现 Token: {response.url[:60]}")
                        captured_data['responses_with_tokens'].append({
                            'url': response.url,
                            'status': response.status,
                            'response': text[:1000]
                        })
                except:
                    pass

        page.on('response', handle_response)

        print("🌐 浏览器已启动\n")
        await page.goto('https://world.nol.com/zh-CN')

        print("=" * 70)
        print("⏳ 请在浏览器中登录...")
        print("   登录成功后按 Ctrl+C")
        print("=" * 70 + "\n")

        try:
            await asyncio.sleep(300)
        except KeyboardInterrupt:
            pass

        # 获取 cookies
        cookies = await context.cookies()
        captured_data['final_cookies'] = cookies

        for cookie in cookies:
            if cookie['name'] == 'access_token':
                print(f"\n✅ 获取到 NOL Token: {cookie['value'][:80]}...")
                captured_data['nol_token'] = cookie['value']

        await browser.close()

    # 保存
    output_file = Path(__file__).parent.parent / "captures" / f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(captured_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 已保存到: {output_file}")
    print(f"   捕获 {len(captured_data['requests'])} 个请求")
    print(f"   发现 {len(captured_data['responses_with_tokens'])} 个 token 响应")


if __name__ == "__main__":
    asyncio.run(main())
