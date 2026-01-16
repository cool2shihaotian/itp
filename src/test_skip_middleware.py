"""测试跳过 middleware，直接访问 OneStop"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.waiting import WaitingQueue


def test_skip_middleware():
    """测试跳过 middleware，直接访问 OneStop"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 跳过 Middleware 直接访问 OneStop")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 快速流程：登录 -> 桥接 -> waiting
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(member_info['signature'], member_info['secureData'], '88889', '25018223')
    waiting.line_up(secure_result['key'])

    # 轮询获取 sessionId
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}

    # 第一次调用
    response1 = client.get(rank_url, params=params)
    logger.info(f"第 1 次 rank: {response1.status_code}")

    # 等待 2 秒
    time.sleep(2)

    # 第二次调用
    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error("❌ 无法获取 sessionId")
        return False

    rank_data = response2.json()

    if 'sessionId' not in rank_data:
        logger.error("❌ rank 响应中无 sessionId")
        return False

    session_id = rank_data['sessionId']
    one_stop_url = rank_data.get('oneStopUrl', '')
    one_stop_key = rank_data.get('key', '')

    logger.info(f"✅ SessionId: {session_id}")
    logger.info(f"✅ OneStop URL: {one_stop_url[:100]}...")
    logger.info(f"✅ Key: {one_stop_key}")

    # 关键步骤：访问 oneStopUrl（不调用 middleware）
    logger.info("\n" + "=" * 70)
    logger.info("访问 OneStop URL（建立 session）")
    logger.info("=" * 70)

    visit_response = client.get(one_stop_url, allow_redirects=True)
    logger.info(f"访问状态: {visit_response.status_code}")
    logger.info(f"收到的 cookies: {len(visit_response.cookies)}")

    # 打印所有 cookies
    for cookie in visit_response.cookies:
        logger.info(f"  🍪 {cookie.name} = {cookie.value[:80] if len(cookie.value) > 80 else cookie.value}")

    # 直接调用 OneStop API（不使用 middleware）
    logger.info("\n" + "=" * 70)
    logger.info("直接调用 OneStop play-date API")
    logger.info("=" * 70)

    onestop_url = f"https://tickets.interpark.com/onestop/api/play/play-date/25018223"
    onestop_params = {
        'placeCode': '25001698',
        'bizCode': '88889',
        'sessionId': session_id,
        'entMemberCode': member_info['encMemberCode']
    }

    # 设置完整的 headers
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://tickets.interpark.com/onestop/schedule',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    client.update_headers(headers)

    logger.info(f"请求 URL: {onestop_url}")
    logger.info(f"请求参数: {json.dumps(onestop_params, indent=2)}")

    onestop_response = client.get(onestop_url, params=onestop_params)
    logger.info(f"\n响应状态码: {onestop_response.status_code}")

    if onestop_response.status_code == 200:
        logger.info("✅ 成功！")
        result = onestop_response.json()
        logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
    else:
        logger.warning(f"⚠️ 失败: {onestop_response.status_code}")
        logger.info(f"响应: {onestop_response.text[:500]}")

        # 尝试不同的 referer
        logger.info("\n尝试使用不同的 Referer...")

        headers['Referer'] = one_stop_url
        client.update_headers(headers)

        onestop_response2 = client.get(onestop_url, params=onestop_params)
        logger.info(f"响应状态码: {onestop_response2.status_code}")

        if onestop_response2.status_code == 200:
            logger.info("✅ 使用 oneStopUrl 作为 Referer 成功！")
            result = onestop_response2.json()
            logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True

        return False


if __name__ == "__main__":
    try:
        success = test_skip_middleware()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 测试成功!")
        else:
            logger.info("ℹ️ 测试结果: 中间步骤成功，OneStop API 失败")
            logger.info("可能原因: 非售票期间，API 不可用")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
