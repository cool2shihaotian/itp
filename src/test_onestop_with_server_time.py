"""测试使用 server 时间同步后调用 OneStop API"""
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


def get_server_time(client):
    """获取 server 时间"""
    url = "https://api-ticketfront.interpark.com/v1/getServerTime"
    params = {
        'type': '1',
        'nc': str(int(time.time() * 1000))
    }
    response = client.get(url, params=params)
    if response.status_code == 200 and response.text:
        return int(response.text)
    return None


def test_onestop_with_time_sync():
    """测试时间同步后的 OneStop API"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 时间同步后调用 OneStop API")
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
    waiting.line_up(secure_result['key'])

    # 获取 sessionId
    url = 'https://ent-waiting-api.interpark.com/waiting/api/rank'
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}
    client.get(url, params=params)
    time.sleep(2)

    response = client.get(url, params=params)
    rank_data = response.json()

    session_id = rank_data['sessionId']
    one_stop_url = rank_data['oneStopUrl']

    logger.info(f"\n✅ 获取到 sessionId: {session_id}")
    logger.info(f"✅ OneStop URL: {one_stop_url}")

    # ⚠️ 关键步骤：同步 server 时间
    logger.info("\n" + "="*70)
    logger.info("同步 Server 时间")
    logger.info("="*70)

    server_time_ms = get_server_time(client)
    server_time_sec = server_time_ms / 1000

    from datetime import datetime
    logger.info(f"Server 时间: {datetime.fromtimestamp(server_time_sec).strftime('%Y-%m-%d %H:%M:%S.%f')}")
    logger.info(f"Server 时间戳(毫秒): {server_time_ms}")
    logger.info(f"Server 时间戳(秒): {int(server_time_sec)}")

    # 提取 sessionId 中的时间戳
    # sessionId 格式: {goodsCode}_M00000{member_id}{timestamp_sec}
    session_timestamp = int(session_id.split('_')[-1][8:])  # 获取最后 10 位（秒级时间戳）
    logger.info(f"\nsessionId 时间戳(秒): {session_timestamp}")
    logger.info(f"sessionId 时间: {datetime.fromtimestamp(session_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

    # 计算时间差
    time_diff = abs(server_time_sec - session_timestamp)
    logger.info(f"\n时间差: {time_diff:.2f} 秒")

    # 访问 oneStopUrl
    logger.info(f"\n访问 OneStop URL...")
    client.get(one_stop_url, allow_redirects=True)

    # 测试 OneStop API
    logger.info("\n" + "="*70)
    logger.info("调用 OneStop play-date API")
    logger.info("="*70)

    onestop_url = f"https://tickets.interpark.com/onestop/api/play/play-date/25018223"
    onestop_params = {
        'placeCode': '25001698',
        'bizCode': '88889',
        'sessionId': session_id,
        'entMemberCode': member_info['encMemberCode']
    }

    client.update_headers({
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://tickets.interpark.com/onestop/schedule',
    })

    onestop_response = client.get(onestop_url, params=onestop_params)
    logger.info(f"Status: {onestop_response.status_code}")

    if onestop_response.status_code == 200:
        logger.info("✅ 成功！")
        logger.info(f"Response: {onestop_response.text}")
    else:
        logger.warning(f"⚠️ 失败: {onestop_response.status_code}")
        logger.info(f"Response: {onestop_response.text}")

    logger.info("\n" + "="*70)
    logger.info("测试完成")
    logger.info("="*70)


if __name__ == "__main__":
    test_onestop_with_time_sync()
