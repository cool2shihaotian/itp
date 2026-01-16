"""直接测试 payment/ready - 使用成功的参数但新鲜 session"""
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
    logger.info("直接测试 - 使用固定座位 + 新鲜 session")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 登录
    logger.info("\n【步骤 1】登录")
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')

    # 桥接
    logger.info("\n【步骤 2】桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    # 会员信息
    logger.info("\n【步骤 3】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    # Waiting
    logger.info("\n【步骤 4】Waiting")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # Rank
    logger.info("\n【步骤 5】Rank")
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

    # Middleware
    logger.info("\n【步骤 6】Middleware")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 使用你之前成功的座位，但是可能已被占用
    # 让我们尝试从前到后找到第一个真正可用的
    logger.info("\n【步骤 7】寻找真正可用的座位")

    payment_flow = InterparkPaymentFlow(client, config, logger)

    # 先尝试一个看起来不太可能被占用的座位（比较大的数字）
    test_seats = [5000, 6000, 7000, 8000, 9000, 10000]

    for seat_num in test_seats:
        seat_info_id = f"25018223:25001698:001:{seat_num}"
        logger.info(f"\n尝试座位: {seat_info_id}")

        selected_seat = {
            'play_date': '20260212',
            'play_seq': '001',
            'seat_info_id': seat_info_id,
            'seat_grade': '1',
            'seat_grade_name': 'R석',
            'floor': '1층',
            'row_no': 'Test',
            'seat_no': str(seat_num),
            'price': 143000,
            'block_key': '001:401',
        }

        # 直接执行完整流程（内部会刷新 session）
        payment_url = payment_flow.execute_full_flow(
            selected_seat=selected_seat,
            session_id=session_id,
            member_info=member_info
        )

        if payment_url:
            logger.info("\n" + "=" * 70)
            logger.info("🎉🎉🎉 完整流程成功！🎉🎉🎉")
            logger.info("=" * 70)
            logger.info(f"座位: {seat_info_id}")
            logger.info(f"支付链接: {payment_url}")
            return True
        else:
            logger.warning(f"座位 {seat_num} 失败，继续尝试...")

    logger.error("\n❌ 所有测试座位都失败")
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
