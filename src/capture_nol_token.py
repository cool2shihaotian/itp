"""
更简单的版本：让用户在浏览器中手动操作并捕获所有请求
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
import yaml


async def capture_interactive():
    """交互式捕获：让用户完全手动操作"""

    # 读取配置
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    print("=" * 70)
    print("🔍 NOL Token 请求抓取工具（交互式）")
    print("=" * 70)
    print(f"\n账号: {config['account']['username']}")
    print("\n使用说明:")
    print("1. 浏览器会自动打开并访问 world.nol.com")
    print("2. 请你手动:")
    print("   - 点击登录按钮")
    print("   - 完成 Cloudflare 验证")
    print("   - 填写账号密码并登录")
    print("   - 等待登录成功，页面跳转")
    print("3. 观察终端输出的请求")
    print("4. 登录成功后，按 Ctrl+C 停止抓取")
    print("5. 查看生成的 JSON 文件")
    print("\n" + "=" * 70)

    captured_data = {
        'requests': [],
        'token_responses': [],
        'session_info': {}
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False  # 显示浏览器
        )

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )

        page = await context.new_page()

        # 请求监听
        async def handle_request(request):
            url = request.url

            # 捕获 API 请求
            if any(keyword in url for keyword in ['/api/', 'identitytoolkit', 'firebase']):
                req_data = {
                    'url': url,
                    'method': request.method,
                    'time': datetime.now().strftime('%H:%M:%S.%f')[:-3]
                }

                # 获取请求头
                headers = dict(request.headers)
                if 'authorization' in headers:
                    req_data['has_auth'] = True
                    req_data['auth_header'] = headers['authorization'][:50] + '...'

                # 获取请求体
                try:
                    post_data = request.post_data
                    if post_data:
                        req_data['body'] = post_data[:500]
                except:
                    pass

                captured_data['requests'].append(req_data)

                # 打印关键信息
                marker = "🔑" if any(k in url for k in ['auth', 'login', 'token']) else "📤"
                print(f"{marker} [{req_data['method']}] {url[:70]}")

                if 'body' in req_data:
                    print(f"   → {req_data['body'][:100]}...")

        # 响应监听
        async def handle_response(response):
            url = response.url

            # 捕获 API 响应
            if any(keyword in url for keyword in ['/api/', 'identitytoolkit', 'firebase']):
                status = response.status
                print(f"📥 [{status}] {url[:70]}")

                # 检查是否包含 token
                try:
                    text = await response.text()

                    # 检查 token 关键字
                    if any(kw in text for kw in ['access_token', 'idToken', '"token"', 'accessToken']):
                        print(f"   ⭐⭐⭐ 包含 TOKEN！⭐⭐⭐")

                        token_data = {
                            'url': url,
                            'status': status,
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'response_preview': text[:800]
                        }

                        # 尝试解析 JSON
                        try:
                            json_data = json.loads(text)
                            token_data['json'] = json_data

                            # 打印关键内容
                            print(f"   内容: {json.dumps(json_data, indent=10)[:200]}...")

                            # 检查特定字段
                            if 'access_token' in json_data:
                                print(f"   ✅ access_token: {json_data['access_token'][:50]}...")
                            if 'idToken' in json_data:
                                print(f"   ✅ idToken: {json_data['idToken'][:50]}...")

                        except:
                            print(f"   内容: {text[:200]}...")

                        captured_data['token_responses'].append(token_data)

                except Exception as e:
                    pass

        # 注册监听
        page.on('request', handle_request)
        page.on('response', handle_response)

        # 访问首页
        print("\n🌐 正在打开浏览器...")
        await page.goto('https://world.nol.com/zh-CN', timeout=60000)

        print("\n✅ 浏览器已就绪")
        print("\n" + "=" * 70)
        print("⏳ 请在浏览器中手动完成登录...")
        print("   所有 API 请求会被自动捕获")
        print("   登录成功后，按 Ctrl+C 停止抓取")
        print("=" * 70 + "\n")

        # 等待用户操作（最多5分钟）
        try:
            await asyncio.sleep(300)
        except KeyboardInterrupt:
            print("\n\n⏹️ 抓取已停止")

        # 获取最终的 cookies
        print("\n🍪 获取 Cookies...")
        cookies = await context.cookies()
        captured_data['session_info']['cookies'] = cookies

        # 查找 access_token
        for cookie in cookies:
            if cookie['name'] == 'access_token':
                captured_data['session_info']['access_token'] = cookie['value']
                print(f"✅ 找到 access_token: {cookie['value'][:50]}...")

        await browser.close()

    # 保存结果
    output_dir = Path(__file__).parent.parent / "captures"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"login_capture_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(captured_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("📊 抓取统计:")
    print("=" * 70)
    print(f"总请求数: {len(captured_data['requests'])}")
    print(f"包含 token 的响应: {len(captured_data['token_responses'])}")
    print(f"Cookies 数量: {len(captured_data['session_info'].get('cookies', []))}")
    print(f"\n✅ 数据已保存到: {output_file}")

    # 分析可能的 NOL token 获取接口
    print("\n" + "=" * 70)
    print("🔍 可能的关键请求:")
    print("=" * 70)

    if captured_data['token_responses']:
        print("\n包含 Token 的响应:")
        for i, resp in enumerate(captured_data['token_responses'], 1):
            print(f"\n{i}. {resp['url']}")
            print(f"   状态: {resp['status']}")
            if 'json' in resp:
                data = resp['json']
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"   字段: {', '.join(keys)}")

    print("\n" + "=" * 70)
    print("✅ 完成！请查看生成的 JSON 文件")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(capture_interactive())
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序被中断")
