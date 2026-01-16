"""
使用 Playwright 抓取登录流程中的所有 HTTP 请求
用于找到 NOL access_token 的获取接口
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime


async def capture_login_requests():
    """捕获登录过程中的所有请求"""

    # 从配置文件读取账号信息
    config_path = Path(__file__).parent.parent / "config.yaml"
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)

    username = config['account']['username']
    password = config['account']['password']

    print("=" * 60)
    print("开始抓取登录流程请求...")
    print(f"账号: {username}")
    print("=" * 60)

    captured_requests = []

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器窗口
            slow_mo=500  # 放慢操作，方便观察
        )

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-CN'
        )

        page = await context.new_page()

        # 监听所有网络请求
        def log_request(request):
            url = request.url
            method = request.method
            headers = request.headers

            # 只记录 API 请求
            if 'api' in url or 'firebase' in url or 'identitytoolkit' in url:
                req_data = {
                    'url': url,
                    'method': method,
                    'headers': dict(headers),
                    'timestamp': datetime.now().isoformat()
                }

                # 尝试获取请求体
                try:
                    if request.post_data:
                        req_data['body'] = request.post_data
                except:
                    pass

                captured_requests.append(req_data)
                print(f"\n📤 请求: [{method}] {url}")

                # 如果有请求体，打印关键信息
                if 'body' in req_data and req_data['body']:
                    try:
                        body = json.loads(req_data['body'])
                        print(f"   Body: {json.dumps(body, indent=6)[:200]}...")
                    except:
                        print(f"   Body: {req_data['body'][:100]}...")

        # 监听所有响应
        def log_response(response):
            url = response.url
            status = response.status

            # 只记录 API 响应
            if 'api' in url or 'firebase' in url or 'identitytoolkit' in url:
                print(f"📥 响应: [{status}] {url}")

                # 查找包含 access_token 的响应
                try:
                    if 'access_token' in response.text or 'idToken' in response.text:
                        print("   ⭐ 检测到 token 相关响应！")

                        # 解析响应体
                        try:
                            resp_json = response.json()
                            print(f"   响应体: {json.dumps(resp_json, indent=6)[:300]}...")
                        except:
                            print(f"   响应体: {response.text[:200]}...")
                except:
                    pass

        # 注册监听器
        page.on('request', log_request)
        page.on('response', log_response)

        # 访问登录页面
        print("\n🌐 访问登录页面...")
        await page.goto('https://world.nol.com/zh-CN/login')

        # 等待页面加载
        await page.wait_for_load_state('networkidle')
        print("✅ 页面加载完成")

        # 等待用户手动登录或自动填写
        print("\n" + "=" * 60)
        print("请选择:")
        print("1. 手动在浏览器中登录")
        print("2. 等待自动填写（如果页面元素可以定位）")
        print("3. 登录完成后，按 Ctrl+C 退出")
        print("=" * 60)

        # 尝试自动填写登录信息（需要根据实际页面调整）
        try:
            # 等待邮箱输入框
            print("\n⏳ 等待登录表单...")
            await page.wait_for_selector('input[type="email"], input[name="email"]', timeout=5000)

            print("📝 填写登录信息...")
            await page.fill('input[type="email"], input[name="email"]', username)
            await page.fill('input[type="password"], input[name="password"]', password)

            print("⏳ 点击登录按钮...")
            await page.click('button[type="submit"], button:has-text("登录"), button:has-text("Login")')

            print("⏳ 等待登录完成（15秒）...")
            await asyncio.sleep(15)

        except Exception as e:
            print(f"⚠️ 自动登录失败: {e}")
            print("📝 请手动在浏览器中完成登录...")
            print("   登录完成后按 Ctrl+C 继续")

        # 等待捕获请求
        try:
            await asyncio.sleep(30)  # 等待30秒捕获登录后的请求
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断")

        # 关闭浏览器
        await browser.close()

    # 保存抓取的请求
    output_file = Path(__file__).parent.parent / "captures" / "login_requests.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ 抓取完成！共捕获 {len(captured_requests)} 个请求")
    print(f"📁 已保存到: {output_file}")
    print("=" * 60)

    # 分析关键请求
    print("\n🔍 分析关键请求:")
    print("-" * 60)

    for i, req in enumerate(captured_requests, 1):
        print(f"\n{i}. [{req['method']}] {req['url']}")

        if 'body' in req:
            print(f"   请求体: {req['body'][:200] if len(req['body']) > 200 else req['body']}")

    # 查找可能返回 access_token 的请求
    print("\n\n🔑 可能返回 access_token 的请求:")
    print("-" * 60)

    token_requests = [
        req for req in captured_requests
        if any(keyword in req['url'].lower() for keyword in ['auth', 'login', 'token', 'signin'])
        and req['method'] in ['POST', 'PUT']
    ]

    if token_requests:
        for req in token_requests:
            print(f"\n🎯 {req['url']}")
            if 'body' in req:
                print(f"   Body: {req['body'][:300]}")
    else:
        print("⚠️ 未找到明显的 token 请求")


if __name__ == "__main__":
    asyncio.run(capture_login_requests())
