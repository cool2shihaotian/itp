"""快速测试多个座位直到找到一个可用的"""
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


def test_seats(client, session_id, seats_to_try):
    """快速测试多个座位"""
    for seat_num in seats_to_try:
        seat_info_id = f"25018223:25001698:001:{seat_num}"

        # 快速测试 preselect
        url = "https://tickets.interpark.com/onestop/api/seats/preselect"
        data = {
            "blockKey": "001:401",
            "goodsCode": "25018223",
            "placeCode": "25001698",
            "playSeq": "001",
            "seatInfoId": seat_info_id,
            "sessionId": session_id
        }
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://tickets.interpark.com',
            'Referer': 'https://tickets.interpark.com/onestop/seat',
            'x-onestop-channel': 'TRIPLE_KOREA',
            'x-onestop-session': session_id,
            'x-onestop-trace-id': 'test',
            'x-requested-with': 'XMLHttpRequest',
            'x-ticket-bff-language': 'KO'
        }

        response = client.post(url, json=data, headers=headers)

        if response.status_code in [200, 201]:
            result = response.json()
            if result.get('isSuccess'):
                return seat_num, seat_info_id
        else:
            error = response.json()
            error_code = error.get('data', {}).get('backendErrorCode', '')
            # 如果不是"座位已占用"错误，也返回
            if error_code != 'P40059':
                return seat_num, seat_info_id

    return None, None


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("快速测试 - 找到可用座位并完成购买")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 快速登录
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

    # 快速测试多个座位
    logger.info("\n【步骤 7】快速测试多个座位")
    seats_to_try = range(1000, 3000)  # 测试 2000 个座位
    logger.info(f"测试座位范围: 1000-2999")

    seat_num, seat_info_id = test_seats(client, session_id, seats_to_try)

    if not seat_num:
        logger.error("❌ 没有找到可用座位")
        return False

    logger.info(f"\n✅✅✅ 找到可用座位: {seat_info_id} ✅✅✅")

    # 立即尝试 preselect（再次确认）
    logger.info("\n【步骤 7.5】立即再次确认座位...")
    url = "https://tickets.interpark.com/onestop/api/seats/preselect"
    data = {
        "blockKey": "001:401",
        "goodsCode": "25018223",
        "placeCode": "25001698",
        "playSeq": "001",
        "seatInfoId": seat_info_id,
        "sessionId": session_id
    }
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://tickets.interpark.com',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': 'final',
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'KO'
    }

    response = client.post(url, json=data, headers=headers)
    if response.status_code not in [200, 201]:
        logger.error(f"❌ 座位 {seat_info_id} 已被占用")
        return False

    result = response.json()
    if not result.get('isSuccess'):
        logger.error(f"❌ 座位 {seat_info_id} 预选失败")
        return False

    logger.info("✅ 座位确认成功！")

    # 准备座位信息
    selected_seat = {
        'play_date': '20260212',
        'play_seq': '001',
        'seat_info_id': seat_info_id,
        'seat_grade': '1',
        'seat_grade_name': 'R석',
        'floor': '1층',
        'row_no': 'Auto',
        'seat_no': str(seat_num),
        'price': 143000,
        'block_key': '001:401',
    }

    # 执行完整的付款流程
    logger.info("\n【步骤 8】执行完整付款流程")
    logger.info("=" * 70)

    payment_flow = InterparkPaymentFlow(client, config, logger)

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
