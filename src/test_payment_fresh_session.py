"""快速测试 - 获取新 session 并立即测试 payment/ready"""
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
    logger.info("快速测试 - Fresh session + payment/ready")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 快速登录（复用之前的 access token 可能更快）
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

    # 准备座位信息（使用一个不太可能被占用的座位）
    logger.info("\n【步骤 7】准备座位")
    selected_seat = {
        'play_date': '20260212',
        'play_seq': '001',
        'seat_info_id': '25018223:25001698:001:3000',  # 尝试不同的座位
        'seat_grade': '1',
        'seat_grade_name': 'R석',
        'floor': '1층',
        'row_no': 'Test',
        'seat_no': '3000',
        'price': 143000,
        'block_key': '001:401',
    }

    # 执行完整的付款流程（包括 preselect 和 select）
    logger.info("\n【步骤 8】执行完整付款流程")
    logger.info("=" * 70)

    payment_flow = InterparkPaymentFlow(client, config, logger)

    # 执行完整流程
    payment_url = payment_flow.execute_full_flow(
        selected_seat=selected_seat,
        session_id=session_id,
        member_info=member_info
    )

    if payment_url:
        logger.info("\n" + "=" * 70)
        logger.info("🎉🎉🎉 完整流程成功！🎉🎉🎉")
        logger.info("=" * 70)
        logger.info(f"支付链接: {payment_url}")
        return True
    else:
        logger.error("\n❌ 完整流程失败")
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
