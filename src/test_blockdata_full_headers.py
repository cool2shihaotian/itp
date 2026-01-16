"""测试 block-data - 完全模拟用户的 curl 命令"""
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
import uuid


def test_with_exact_curl_headers():
    """使用完全匹配的 curl headers"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试 block-data - 完全匹配 curl headers")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 登录
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')

    # Bridge Auth
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

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

    # 设置额外的 cookies（从用户的 curl 中）
    logger.info("\n设置额外的 cookies...")
    client.session.cookies.set('ent_onestop_channel', 'TRIPLE_KOREA')
    client.session.cookies.set('userId', user_id)
    logger.info(f"✅ 设置 userId: {user_id}")

    # 现在测试 block-data，使用完全匹配的 headers
    logger.info("\n" + "=" * 70)
    logger.info("测试 block-data API（完全匹配 curl）")
    logger.info("=" * 70)

    block_url = "https://tickets.interpark.com/onestop/api/seats/block-data"
    block_params = {
        'goodsCode': '25018223',
        'placeCode': '25001698',
        'playSeq': '001'
    }

    # 完全匹配用户的 curl headers
    trace_id = str(uuid.uuid4())[:16]
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6,ru;q=0.5,la;q=0.4,th;q=0.3',
        'priority': 'u=1, i',
        'referer': 'https://tickets.interpark.com/onestop/seat',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not/A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': trace_id,
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'ZH'
    }
    client.update_headers(headers)

    logger.info(f"请求 URL: {block_url}")
    logger.info(f"请求参数: {block_params}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Trace ID: {trace_id}")

    # 打印所有 cookies
    logger.info(f"\n当前 Cookies ({len(client.session.cookies)} 个):")
    for cookie in client.session.cookies:
        value_preview = cookie.value[:80] if len(cookie.value) > 80 else cookie.value
        logger.info(f"  🍪 {cookie.name} = {value_preview}")

    response = client.get(block_url, params=block_params)
    logger.info(f"\n响应状态: {response.status_code}")

    if response.status_code == 200:
        blocks = response.json()
        logger.info(f"✅ 成功！获取到 {len(blocks)} 个区域")
        for i, block in enumerate(blocks[:5], 1):
            logger.info(f"  {i}. {block.get('blockKey')} - {block.get('blockName')}")

        # 测试 seatMeta
        if len(blocks) > 0:
            logger.info("\n" + "=" * 70)
            logger.info("测试 seatMeta API")
            logger.info("=" * 70)

            seatmeta_url = "https://tickets.interpark.com/onestop/api/seatMeta"
            block_key = blocks[0]['blockKey']

            seatmeta_params = {
                'goodsCode': '25018223',
                'placeCode': '25001698',
                'playSeq': '001',
                'blockKeys': block_key
            }

            logger.info(f"测试区域: {block_key}")
            response2 = client.get(seatmeta_url, params=seatmeta_params)
            logger.info(f"seatMeta 响应状态: {response2.status_code}")

            if response2.status_code == 200:
                seat_data = response2.json()
                logger.info(f"✅ seatMeta 成功！")
                if isinstance(seat_data, list) and len(seat_data) > 0:
                    seats = seat_data[0].get('seats', [])
                    logger.info(f"  座位数量: {len(seats)}")
                    if seats:
                        logger.info(f"  第一个座位: {seats[0].get('seatInfoId')}")

        return True
    else:
        logger.warning(f"❌ 失败！")
        logger.warning(f"响应内容: {response.text[:500]}")
        logger.warning(f"响应头: {dict(response.headers)}")

        # 尝试访问选座页面后再试
        logger.info("\n尝试先访问选座页面...")

        seat_page_url = "https://tickets.interpark.com/onestop/seat"
        seat_page_params = {
            'goodsCode': '25018223',
            'placeCode': '25001698',
            'playSeq': '001'
        }

        page_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'priority': 'u=1, i',
            'referer': 'https://tickets.interpark.com/onestop',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not(A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }
        client.update_headers(page_headers)

        page_response = client.get(seat_page_url, params=seat_page_params, allow_redirects=True)
        logger.info(f"选座页面状态: {page_response.status_code}")

        # 再次尝试 block-data
        logger.info("\n再次尝试 block-data...")
        response3 = client.get(block_url, params=block_params, headers=headers)
        logger.info(f"第二次尝试状态: {response3.status_code}")

        if response3.status_code == 200:
            logger.info(f"✅ 第二次尝试成功！")
            return True
        else:
            logger.warning(f"❌ 第二次尝试也失败: {response3.text[:300]}")
            return False


if __name__ == "__main__":
    try:
        success = test_with_exact_curl_headers()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
