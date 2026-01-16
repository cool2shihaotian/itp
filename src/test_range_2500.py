"""测试 2500 附近的座位"""
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
import time


def main():
    config = load_config()
    logger = setup_logging(config)

    client = ITPClient(config, logger)

    # 快速登录和获取session
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

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

    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 测试 2500 附近的座位
    logger.info("\n【测试 2500 附近的座位】")

    for seat_num in range(2500, 2550):
        seat_info_id = f"25018223:25001698:001:{seat_num}"

        # 测试 preselect
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
                logger.info(f"\n✅✅✅ 找到可用座位: {seat_info_id} ✅✅✅")
                logger.info(f"响应: {result}")
                return True

        error = response.json()
        error_code = error.get('data', {}).get('backendErrorCode', '')

        if error_code == 'P40054':
            # 座位已占用，继续
            continue
        else:
            # 其他错误，打印出来
            logger.warning(f"座位 {seat_num}: {error_code} - {error.get('data', {}).get('message', '')}")

    logger.error("\n❌ 2500 附近没有找到可用座位")
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
