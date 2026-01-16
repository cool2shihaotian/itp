"""测试购买指定座位"""
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
from src.payment_flow import InterparkPaymentFlow
import time


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试购买指定座位")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # ===== 步骤 1: 登录 =====
    logger.info("\n【步骤 1/8】登录")
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')
    logger.info(f"✅ User ID: {user_id}")

    # ===== 步骤 2: 桥接鉴权 =====
    logger.info("\n【步骤 2/8】桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    # ===== 步骤 3: 获取会员信息 =====
    logger.info("\n【步骤 3/8】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    # ===== 步骤 4: Waiting 排队 =====
    logger.info("\n【步骤 4/8】Waiting 排队")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # ===== 步骤 5: Rank 获取 Session ID =====
    logger.info("\n【步骤 5/8】Rank 获取 Session ID")
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

    # ===== 步骤 6: Middleware set-cookie =====
    logger.info("\n【步骤 6/8】Middleware set-cookie")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # ===== 步骤 7: 准备座位信息 =====
    logger.info("\n【步骤 7/8】准备座位信息")
    selected_seat = {
        'play_date': '20260212',
        'play_seq': '001',
        'seat_info_id': '25018223:25001698:001:2569',  # ✅ 可用座位
        'seat_grade': '1',
        'seat_grade_name': 'R석',
        'floor': '1층',
        'row_no': '가구역',
        'seat_no': '2569',
        'price': 143000,
        'block_key': '001:401',  # ✅ blockKey
        'poll_count': 1,
        'elapsed_time': 0
    }

    logger.info(f"\n座位信息:")
    logger.info(f"  座位ID: {selected_seat['seat_info_id']}")
    logger.info(f"  blockKey: {selected_seat['block_key']}")
    logger.info(f"  Session ID: {session_id}")

    # ===== 步骤 8: 执行完整付款流程 =====
    logger.info("\n【步骤 8/8】执行完整付款流程")
    logger.info("=" * 70)

    payment_flow = InterparkPaymentFlow(client, config, logger)

    payment_url = payment_flow.execute_full_flow(
        selected_seat=selected_seat,
        session_id=session_id,
        member_info=member_info
    )

    if payment_url:
        logger.info("\n" + "=" * 70)
        logger.info("🎉 购买流程成功！")
        logger.info("=" * 70)

        # 保存付款链接
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"/Users/shihaotian/Desktop/edison/itp/purchase_success_{timestamp}.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("🎉 ITP 购票成功！\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"演出: Sing Again 4 全国巡回演唱会 – 首尔\n")
            f.write(f"日期: {selected_seat['play_date']}\n")
            f.write(f"场次: {selected_seat['play_seq']}\n")
            f.write(f"座位ID: {selected_seat['seat_info_id']}\n")
            f.write(f"价位: {selected_seat['seat_grade_name']}\n")
            f.write(f"位置: {selected_seat['floor']} - {selected_seat['row_no']} - {selected_seat['seat_no']}\n")
            f.write(f"价格: {selected_seat['price']:,} 韩元\n\n")
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
            f.write("4. 💡 建议在 10 分钟内完成支付\n\n")
            f.write("=" * 70 + "\n")
            f.write("🎉 恭喜！购票成功！\n")
            f.write("=" * 70 + "\n")

        logger.info(f"\n✅ 付款链接已保存到: {output_file}")
        logger.info(f"\n💳 付款链接:\n{payment_url}")
        logger.info("\n" + "=" * 70)

        return True
    else:
        logger.error("\n❌ 购买流程失败")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
