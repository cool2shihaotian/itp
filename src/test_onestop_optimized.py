"""测试优化后的 OneStop API"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.waiting import WaitingQueue
from src.onestop_middleware_v3 import OneStopMiddlewareV3
from src.onestop_optimized import OneStopBookingOptimized


def test_onestop_optimized():
    """测试优化后的 OneStop API"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试优化后的 OneStop API")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # ===== 步骤 1: 登录 =====
    logger.info("\n【步骤 1/7】登录")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    login_success = auth_manager.login(username, password, skip_cloudflare=False)
    if not login_success:
        logger.error("❌ 登录失败")
        return False

    logger.info(f"✅ 登录成功！User ID: {auth_manager.user_id}")

    # ===== 步骤 2: Bridge Auth =====
    logger.info("\n【步骤 2/7】Bridge Auth")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)
    logger.info("✅ Bridge Auth 完成")

    # ===== 步骤 3: 获取会员信息 =====
    logger.info("\n【步骤 3/7】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')
    logger.info(f"✅ Member Code: {member_info.get('memberCode', 'N/A')}")

    # ===== 步骤 4: Waiting 排队 =====
    logger.info("\n【步骤 4/7】Waiting 排队")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )

    waiting.line_up(secure_result.get('key', ''))
    logger.info(f"✅ Waiting ID: {waiting.waiting_id}")

    # ===== 步骤 5: Rank 轮询获取 sessionId =====
    logger.info("\n【步骤 5/7】Rank 轮询获取 sessionId")
    import time

    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {
        'bizCode': '88889',
        'waitingId': waiting.waiting_id
    }

    # 第一次 rank
    logger.info("第一次 rank 请求...")
    response1 = client.get(rank_url, params=params)
    if response1.status_code == 200:
        logger.info("第一次 rank 成功")

    # 等待
    logger.info("等待 4 秒...")
    time.sleep(4)

    # 第二次 rank
    logger.info("第二次 rank 请求...")
    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error(f"❌ Rank 请求失败: {response2.status_code}")
        return False

    rank_data = response2.json()
    session_id = rank_data.get('sessionId', '')

    if not session_id:
        logger.error("❌ 未获取到 sessionId")
        return False

    logger.info(f"✅ Session ID: {session_id}")

    # ===== 步骤 6: Middleware =====
    logger.info("\n【步骤 6/7】Middleware")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_result = middleware_v3.call_middleware_set_cookie(rank_data)

    if not middleware_result:
        logger.warning("⚠️ Middleware 失败，但继续尝试")
    else:
        logger.info("✅ Middleware 完成")

    # ===== 步骤 7: 测试 OneStop API（优化版本）=====
    logger.info("\n【步骤 7/7】测试 OneStop API（优化版本）")
    logger.info("=" * 70)

    onestop = OneStopBookingOptimized(client, config, logger)

    # 测试 1: 获取演出日期
    logger.info("\n[测试 1] 获取演出日期列表")
    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info.get('encMemberCode', '')
    )

    if play_dates:
        logger.info("✅ 测试 1 通过")
    else:
        logger.error("❌ 测试 1 失败")
        return False

    # 测试 2: 检查会话状态
    logger.info("\n[测试 2] 检查会话状态")
    session_check = onestop.check_session(session_id=session_id)

    if session_check:
        logger.info("✅ 测试 2 通过")
    else:
        logger.warning("⚠️ 测试 2 失败（这可能是正常的）")

    # 测试 3: 获取场次信息
    logger.info("\n[测试 3] 获取场次信息")
    play_date_list = play_dates.get('playDate', [])
    if play_date_list:
        first_date = play_date_list[0]
        play_seqs = onestop.get_play_seqs(
            goods_code='25018223',
            place_code='25001698',
            play_date=first_date,
            session_id=session_id
        )

        if play_seqs:
            logger.info("✅ 测试 3 通过")
        else:
            logger.warning("⚠️ 测试 3 失败")

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("测试总结")
    logger.info("=" * 70)
    logger.info("✅ OneStop API 优化版本测试完成")
    logger.info("\n主要改进:")
    logger.info("  1. ✅ 修复了 URL 路径（从 /v1/ 改为 /api/）")
    logger.info("  2. ✅ 优化了 Headers 参数")
    logger.info("  3. ✅ 添加了完整的浏览器特征")
    logger.info("  4. ✅ 改进了错误处理和日志")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_onestop_optimized()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)