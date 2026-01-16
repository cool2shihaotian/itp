"""测试 block-data API - 先访问选座页面"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.waiting import WaitingQueue
from src.onestop_middleware_v3 import OneStopMiddlewareV3
import time


def test_blockdata_with_page_visit():
    """测试 block-data API - 先访问选座页面"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试 block-data API（先访问选座页面）")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 登录
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])

    # Bridge Auth
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1'))

    # 获取会员信息
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    # Waiting
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # Rank
    time.sleep(4)
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}
    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error(f"❌ Rank 失败: {response2.status_code}")
        return False

    rank_data = response2.json()
    session_id = rank_data.get('sessionId', '')
    logger.info(f"✅ Session ID: {session_id}")

    # Middleware
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 关键步骤：先访问选座页面！
    logger.info("\n" + "=" * 70)
    logger.info("【关键步骤】访问选座页面（/onestop/seat）")
    logger.info("=" * 70)

    seat_page_url = "https://tickets.interpark.com/onestop/seat"
    seat_page_params = {
        'goodsCode': '25018223',
        'placeCode': '25001698',
        'playSeq': '001'
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://tickets.interpark.com/onestop',
    }
    client.update_headers(headers)

    logger.info(f"访问选座页面: {seat_page_url}")
    response = client.get(seat_page_url, params=seat_page_params, allow_redirects=True)
    logger.info(f"选座页面状态: {response.status_code}")

    # 检查 cookies
    logger.info(f"\n当前 Cookies: {len(client.session.cookies)}")
    for cookie in client.session.cookies:
        value_preview = cookie.value[:50] if len(cookie.value) > 50 else cookie.value
        logger.info(f"  🍪 {cookie.name} = {value_preview}")

    # 现在测试 block-data
    logger.info("\n" + "=" * 70)
    logger.info("测试 block-data API")
    logger.info("=" * 70)

    block_url = "https://tickets.interpark.com/onestop/api/seats/block-data"
    block_params = {
        'goodsCode': '25018223',
        'placeCode': '25001698',
        'playSeq': '001'
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not/A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'ZH'
    }
    client.update_headers(headers)

    logger.info(f"请求参数: {block_params}")
    response = client.get(block_url, params=block_params)
    logger.info(f"block-data 响应状态: {response.status_code}")

    if response.status_code == 200:
        blocks = response.json()
        logger.info(f"✅ 成功！获取到 {len(blocks)} 个区域")
        for i, block in enumerate(blocks[:5], 1):
            logger.info(f"  {i}. {block.get('blockKey')} - {block.get('blockName')}")
        return True
    else:
        logger.warning(f"❌ 失败！")
        logger.warning(f"响应内容: {response.text[:500]}")
        return False


if __name__ == "__main__":
    try:
        success = test_blockdata_with_page_visit()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
