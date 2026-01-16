"""使用真实的 sessionId 测试 OneStop"""
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
from src.onestop import OneStopBooking


def test_onestop_with_real_session():
    """使用从 rank 获取的真实 sessionId 测试 OneStop"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 使用真实 sessionId 调用 OneStop APIs")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 快速登录和初始化
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(member_info['signature'], member_info['secureData'], '88889', '25018223')
    key = waiting.line_up(secure_result['key'])

    # Rank 两次获取 sessionId
    url = 'https://ent-waiting-api.interpark.com/waiting/api/rank'
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}

    logger.info("\n第一次 rank (初始状态)...")
    client.get(url, params=params)
    time.sleep(2)

    logger.info("第二次 rank (获取 sessionId)...")
    response = client.get(url, params=params)
    rank_data = response.json()

    session_id = rank_data.get('sessionId')
    one_stop_url = rank_data.get('oneStopUrl')
    onestop_key = rank_data.get('key')

    logger.info(f"\n✅ 获取到 sessionId: {session_id}")
    logger.info(f"✅ OneStop URL: {one_stop_url}")
    logger.info(f"✅ OneStop Key: {onestop_key}")

    # 访问 oneStopUrl (可能设置必要的 cookies)
    if one_stop_url:
        logger.info("\n访问 OneStop URL...")
        redirect_response = client.get(one_stop_url, allow_redirects=True)
        logger.info(f"Status: {redirect_response.status_code}")
        logger.info(f"Final URL: {redirect_response.url}")

    # 测试 OneStop APIs
    logger.info("\n" + "=" * 70)
    logger.info("测试 OneStop APIs")
    logger.info("=" * 70)

    onestop = OneStopBooking(client, config, logger)

    # 测试 1: 获取演出日期
    logger.info("\n[测试 1] 获取演出日期列表")
    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info['encMemberCode']
    )

    if play_dates:
        logger.info("✅ 演出日期获取成功！")
        logger.info(f"响应:\n{json.dumps(play_dates, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 演出日期获取失败")

    # 测试 2: Session Check
    logger.info("\n[测试 2] Session Check")
    session_check = onestop.check_session(
        goods_code='25018223',
        play_seq=None,
        biz_code='88889'
    )

    if session_check:
        logger.info("✅ Session check 成功")
        logger.info(f"响应:\n{json.dumps(session_check, indent=2, ensure_ascii=False)}")
    else:
        logger.warning("⚠️ Session check 失败")

    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_onestop_with_real_session()
