"""测试轮询选座策略 - 持续监控余票，有票立即购买"""
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
from src.polling_seat_selector import PollingSeatSelector


def test_polling_seat_selection():
    """测试轮询选座：持续监控，有票立即购买"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试：轮询选座（持续监控余票）")
    logger.info("=" * 70)

    # ===== 初始化 =====
    client = ITPClient(config, logger)

    # ===== 步骤 1: 登录和初始化 =====
    logger.info("\n【步骤 1/5】登录和初始化")

    auth_manager = AuthManager(client, config, logger)
    login_success = auth_manager.login(
        config['account']['username'],
        config['account']['password'],
        skip_cloudflare=False
    )

    if not login_success:
        logger.error("❌ 登录失败")
        return False

    logger.info(f"✅ User ID: {auth_manager.user_id}")

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    logger.info(f"✅ Member Code: {member_info['memberCode']}")

    # ===== 步骤 2: Waiting 流程 =====
    logger.info("\n【步骤 2/5】Waiting 排队")

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )

    waiting.line_up(secure_result['key'])
    logger.info(f"✅ Waiting ID: {waiting.waiting_id}")

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
    session_id = rank_data['sessionId']

    logger.info(f"✅ SessionId: {session_id}")

    # ===== 步骤 3: Middleware =====
    logger.info("\n【步骤 3/5】Middleware")

    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # ===== 步骤 4: 获取演出日期 =====
    logger.info("\n【步骤 4/5】获取演出日期")

    onestop = OneStopBookingFixed(client, config, logger)

    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info['encMemberCode']
    )

    if not play_dates:
        logger.error("❌ 获取演出日期失败")
        return False

    available_dates = play_dates.get('playDate', [])
    logger.info(f"✅ 可用日期: {available_dates}")

    # 选择最后一个日期（可能有更多余票）
    selected_date = available_dates[-1]
    logger.info(f"\n选择日期: {selected_date}")

    # ===== 步骤 5: 轮询选座 =====
    logger.info("\n【步骤 5/5】轮询选座（持续监控余票）")

    polling_selector = PollingSeatSelector(client, config, logger)

    # 配置轮询参数
    poll_interval = 3  # 每 3 秒轮询一次
    timeout = 300      # 最多轮询 5 分钟
    max_price = None   # 不限价格（可以设置，如 150000）

    logger.info(f"\n轮询配置:")
    logger.info(f"  轮询间隔: {poll_interval} 秒")
    logger.info(f"  超时时间: {timeout} 秒 ({timeout//60} 分钟)")
    if max_price:
        logger.info(f"  最高价格: {max_price:,} 韩元")
    else:
        logger.info(f"  最高价格: 不限")

    # 开始轮询
    selected_seat = polling_selector.poll_and_select(
        onestop=onestop,
        play_date=selected_date,
        session_id=session_id,
        member_info=member_info,
        poll_interval=poll_interval,
        timeout=timeout,
        max_price=max_price
    )

    if not selected_seat:
        logger.error("\n❌ 轮询超时，未找到有余票的座位")
        logger.info("建议:")
        logger.info("  1. 增加轮询超时时间（如 10 分钟）")
        logger.info("  2. 缩短轮询间隔（如 1 秒）")
        logger.info("  3. 选择其他日期")
        return False

    # 找到有票的座位！立即购买
    logger.info("\n" + "=" * 70)
    logger.info("🎊 成功找到余票！立即生成付款链接")
    logger.info("=" * 70)

    payment_url = polling_selector.quick_purchase(
        selected_seat=selected_seat,
        session_id=session_id,
        member_info=member_info
    )

    if payment_url:
        logger.info("\n" + "=" * 70)
        logger.info("✅ 完全成功！轮询选座完成！")
        logger.info("=" * 70)
        logger.info(f"\n付款链接: {payment_url}")
        return True
    else:
        logger.error("\n❌ 生成付款链接失败")
        return False


if __name__ == "__main__":
    try:
        success = test_polling_seat_selection()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 测试成功！轮询选座完成！")
        else:
            logger.info("ℹ️ 测试完成（可能因超时或售罄）")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断轮询")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
