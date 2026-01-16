"""测试 OneStop Middleware V3 - 64 字节二进制格式"""
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
from src.onestop_middleware_v3 import OneStopMiddlewareV3


def test_middleware_v3():
    """测试 64 字节二进制格式的 middleware"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: OneStop Middleware V3 (64字节二进制)")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 快速流程
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result['key'])

    # Rank 轮询
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}

    response1 = client.get(rank_url, params=params)
    time.sleep(2)

    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error("❌ Rank 失败")
        return False

    rank_data = response2.json()

    if 'sessionId' not in rank_data:
        logger.error("❌ 无 sessionId")
        return False

    logger.info(f"\n✅ SessionId: {rank_data['sessionId']}")
    logger.info(f"✅ Key: {rank_data.get('key', '')[:50]}...")
    logger.info(f"✅ Signature (k): {rank_data.get('k', '')[:50]}...")

    # Middleware V3
    logger.info("\n" + "=" * 70)
    logger.info("Middleware V3（64字节二进制）")
    logger.info("=" * 70)

    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_success = middleware_v3.call_middleware_set_cookie(rank_data)

    # 测试 OneStop API
    logger.info("\n" + "=" * 70)
    logger.info("测试 OneStop play-date API")
    logger.info("=" * 70)

    onestop_url = f"https://tickets.interpark.com/onestop/api/play/play-date/25018223"
    onestop_params = {
        'placeCode': '25001698',
        'bizCode': '88889',
        'sessionId': rank_data['sessionId'],
        'entMemberCode': member_info['encMemberCode']
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': rank_data.get('oneStopUrl', ''),
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    client.update_headers(headers)

    onestop_response = client.get(onestop_url, params=onestop_params)
    logger.info(f"响应状态码: {onestop_response.status_code}")

    if onestop_response.status_code == 200:
        logger.info("✅ 成功！OneStop API 调用成功！")
        result = onestop_response.json()
        logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        logger.info("\n" + "=" * 70)
        logger.info("🎉 完全成功！纯 requests 实现了 OneStop！")
        logger.info("=" * 70)
        return True
    else:
        logger.warning(f"⚠️ 失败: {onestop_response.status_code}")
        logger.info(f"响应: {onestop_response.text[:500]}")

        logger.info("\n" + "=" * 70)
        logger.info("ℹ️ 需要进一步调试 payload 格式")
        logger.info("=" * 70)
        return False


if __name__ == "__main__":
    try:
        success = test_middleware_v3()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 完全成功！")
        else:
            logger.info("ℹ️ 测试完成，payload 格式需要进一步调整")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
