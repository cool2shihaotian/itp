"""完整轮询到付款测试 - 从登录到生成付款链接"""
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
from src.polling_seat_selector import PollingSeatSelector
from src.onestop_with_fix import OneStopBookingFixed
from src.payment_flow import InterparkPaymentFlow
import time


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("完整轮询到付款测试")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 步骤 1: 登录
    logger.info("\n【步骤 1/10】NOL 登录")
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')
    logger.info(f"✅ User ID: {user_id}")

    # 步骤 2: 桥接鉴权
    logger.info("\n【步骤 2/10】桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    # 步骤 3: 获取会员信息
    logger.info("\n【步骤 3/10】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    # 步骤 4: Waiting 排队
    logger.info("\n【步骤 4/10】Waiting 排队")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # 步骤 5: Rank 获取 Session ID
    logger.info("\n【步骤 5/10】Rank 获取 Session ID")
    time.sleep(4)
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}
    response = client.get(rank_url, params=params)

    if response.status_code != 200:
        logger.error(f"❌ Rank 失败: {response.status_code}")
        return False

    rank_data = response.json()
    session_id = rank_data.get('sessionId', '')
    logger.info(f"✅ Session ID: {session_id}")

    # 步骤 6: Middleware set-cookie
    logger.info("\n【步骤 6/10】Middleware set-cookie")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 步骤 7: 初始化 OneStop 和选座器
    logger.info("\n【步骤 7/10】初始化 OneStop 和选座器")
    onestop = OneStopBookingFixed(client, config, logger)
    selector = PollingSeatSelector(client, config, logger)
    payment_flow = InterparkPaymentFlow(client, config, logger)
    logger.info("✅ 初始化完成")

    # 步骤 8: 轮询选座（短时间测试）
    logger.info("\n【步骤 8/10】轮询选座（最多 30 秒）")
    logger.info("=" * 70)

    play_date = "20260212"

    selected_seat = selector.poll_and_select(
        onestop=onestop,
        play_date=play_date,
        session_id=session_id,
        member_info=member_info,
        poll_interval=2,  # 2秒轮询间隔
        timeout=30,       # 30秒超时（测试用）
        max_price=None,
        user_id=user_id   # ⚠️ 传递 user_id
    )

    if not selected_seat:
        logger.warning("\n⚠️ 30秒内未找到可售座位")
        logger.info("这很正常，可以尝试：")
        logger.info("  1. 增加超时时间（timeout=300 表示 5 分钟）")
        logger.info("  2. 尝试其他日期（play_date='20260215'）")
        logger.info("  3. 持续轮询等待退票")
        return False

    logger.info("\n" + "🎉" * 35)
    logger.info("✅ 轮询成功！找到可售座位！")
    logger.info("🎉" * 35)

    # 步骤 9: 执行完整付款流程
    logger.info("\n【步骤 9/10】执行完整付款流程")
    logger.info("=" * 70)

    payment_url = payment_flow.execute_full_flow(
        selected_seat=selected_seat,
        session_id=session_id,
        member_info=member_info
    )

    if not payment_url:
        logger.error("❌ 付款流程失败")
        return False

    logger.info("\n" + "=" * 70)
    logger.info("🎉 付款流程成功！")
    logger.info("=" * 70)

    # 步骤 10: 保存付款链接
    logger.info("\n【步骤 10/10】保存付款链接")

    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"/Users/shihaotian/Desktop/edison/itp/payment_success_{timestamp}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("🎉 ITP 轮询购票成功！\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"演出: Sing Again 4 全国巡回演唱会 – 首尔\n")
        f.write(f"日期: {selected_seat['play_date']}\n")
        f.write(f"场次: {selected_seat['play_seq']}\n")
        f.write(f"座位ID: {selected_seat['seat_info_id']}\n")
        f.write(f"价位: {selected_seat['seat_grade_name']}\n")
        f.write(f"位置: {selected_seat['floor']} - {selected_seat['row_no']} - {selected_seat['seat_no']}\n")
        f.write(f"价格: {selected_seat['price']:,} 韩元\n\n")
        f.write(f"轮询统计:\n")
        f.write(f"  轮询次数: {selected_seat['poll_count']}\n")
        f.write(f"  用时: {selected_seat['elapsed_time']} 秒\n")
        f.write(f"  检测方式: seatMeta 真实座位状态\n\n")
        f.write(f"Session ID: {session_id}\n")
        f.write(f"User ID: {user_id}\n\n")
        f.write("付款流程:\n")
        f.write("  ✅ 1. 预选座位 (preselect)\n")
        f.write("  ✅ 2. 确认选座 (select)\n")
        f.write("  ✅ 3. 准备付款 (payment/ready)\n")
        f.write("  ✅ 4. 请求支付 (eximbay/request)\n")
        f.write("  ✅ 5. 生成支付链接\n\n")
        f.write("付款链接:\n")
        f.write("-" * 70 + "\n")
        f.write(f"{payment_url}\n")
        f.write("-" * 70 + "\n\n")
        f.write("🎉 重要提示:\n")
        f.write("1. ✅ 座位已通过完整流程锁定\n")
        f.write("2. ✅ 支付网关已准备就绪\n")
        f.write("3. ⚠️ 请尽快完成支付（座位已预留）\n")
        f.write("4. 💡 支付链接可能有时效性，建议在 10 分钟内完成支付\n\n")
        f.write("=" * 70 + "\n")
        f.write("🎉 恭喜！轮询购票系统运行成功！\n")
        f.write("=" * 70 + "\n")

    logger.info(f"\n✅ 付款链接已保存到: {output_file}")

    # 显示最终结果
    logger.info("\n" + "=" * 70)
    logger.info("🎉 最终结果")
    logger.info("=" * 70)
    logger.info(f"演出日期: {selected_seat['play_date']}")
    logger.info(f"座位信息: {selected_seat['seat_grade_name']} - {selected_seat['floor']} {selected_seat['row_no']} {selected_seat['seat_no']}")
    logger.info(f"价格: {selected_seat['price']:,} 韩元")
    logger.info(f"轮询次数: {selected_seat['poll_count']} 次")
    logger.info(f"轮询用时: {selected_seat['elapsed_time']} 秒")
    logger.info(f"\n💳 付款链接:\n{payment_url}")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "🎉" * 35)
            print("✅ 完整测试成功！从登录到付款链接生成！")
            print("🎉" * 35)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
