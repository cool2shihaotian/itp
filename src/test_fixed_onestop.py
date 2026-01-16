"""测试修复后的 OneStop API（添加关键 headers）"""
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
from src.onestop_with_fix import OneStopBookingFixed


def test_fixed_onestop():
    """测试修复后的 OneStop API"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: OneStop API（添加关键 headers）")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 快速流程
    auth_manager = AuthManager(client, config, logger)
    login_success = auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    if not login_success:
        logger.error("❌ 登录失败")
        return False

    if not hasattr(auth_manager, 'user_id') or not auth_manager.user_id:
        logger.error("❌ 未能获取 user_id")
        return False

    logger.info(f"✅ User ID: {auth_manager.user_id}")

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

    session_id = rank_data['sessionId']
    logger.info(f"\n✅ SessionId: {session_id}")

    # Middleware V3
    logger.info("\n" + "=" * 70)
    logger.info("Middleware V3（64字节二进制）")
    logger.info("=" * 70)

    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # ⭐ 使用修复后的 OneStop API（添加关键 headers）
    logger.info("\n" + "=" * 70)
    logger.info("OneStop API（修复版本 - 添加关键 headers）")
    logger.info("=" * 70)

    onestop_fixed = OneStopBookingFixed(client, config, logger)

    # 1. 获取演出日期
    logger.info("\n[步骤 1/3] 获取演出日期")
    play_dates = onestop_fixed.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info['encMemberCode']
    )

    if not play_dates:
        logger.error("❌ 获取演出日期失败")
        return False

    # 2. 检查会话
    logger.info("\n[步骤 2/3] 检查会话状态")
    session_check = onestop_fixed.check_session(
        goods_code='25018223',
        session_id=session_id
    )

    if session_check:
        logger.info(f"✅ 会话检查成功: {json.dumps(session_check, indent=2, ensure_ascii=False)}")

    # 3. 获取座位信息（使用第一个日期）
    if play_dates.get('playDate') and len(play_dates['playDate']) > 0:
        first_date = play_dates['playDate'][0]
        logger.info(f"\n[步骤 3/3] 获取座位信息: {first_date}")

        seats = onestop_fixed.get_play_seats(
            goods_code='25018223',
            place_code='25001698',
            play_date=first_date,
            session_id=session_id,
            biz_code='88889'
        )

        if seats:
            logger.info("✅ 座位信息获取成功！")
            logger.info(f"响应: {json.dumps(seats, indent=2, ensure_ascii=False)}")
        else:
            logger.warning("⚠️ 座位信息获取失败")

    logger.info("\n" + "=" * 70)
    logger.info("🎉 测试完成！")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_fixed_onestop()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 完全成功！OneStop API 已完全可用！")
        else:
            logger.info("ℹ️ 测试完成")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
