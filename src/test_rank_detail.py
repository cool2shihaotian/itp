"""详细测试 rank API 并尝试获取 sessionId"""
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


def test_rank_and_session():
    """详细测试 rank API 响应"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("详细测试: Rank API 和 sessionId 获取")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 快速登录
    logger.info("\n[步骤 1] 登录...")
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    # 桥接鉴权
    logger.info("\n[步骤 2] 桥接鉴权...")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth("25018223", "25001698", "10965", auth_manager.user_id)

    # 获取会员信息
    logger.info("\n[步骤 3] 获取会员信息...")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info("25018223")

    # 获取 secure-url 和 key
    logger.info("\n[步骤 4] 获取 key...")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        member_info["signature"],
        member_info["secureData"],
        "88889",
        "25018223"
    )

    key = secure_result["key"]
    logger.info(f"✅ Key: {key[:50]}...")

    # line-up
    logger.info("\n[步骤 5] Line-up...")
    line_up_result = waiting.line_up(key)
    logger.info(f"✅ Line-up 成功")
    logger.info(f"Waiting ID: {line_up_result.get('waitingId', 'N/A')}")
    logger.info(f"完整响应: {json.dumps(line_up_result, indent=2)}")

    # rank API 调用
    logger.info("\n[步骤 6] 调用 Rank API...")
    url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {
        "bizCode": "88889",
        "waitingId": line_up_result["waitingId"]
    }

    response = client.get(url, params=params)

    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers:")
    for key, value in response.headers.items():
        logger.info(f"  {key}: {value}")

    if response.text:
        rank_data = response.json()
        logger.info(f"\nRank Response Body:")
        logger.info(json.dumps(rank_data, indent=2, ensure_ascii=False))

        # 检查是否有 sessionId 相关字段
        logger.info("\n" + "=" * 70)
        logger.info("检查 sessionId 相关信息...")
        logger.info("=" * 70)

        if 'sessionId' in rank_data:
            logger.info(f"✅ 找到 sessionId: {rank_data['sessionId']}")

        if 'redirectUrl' in rank_data:
            logger.info(f"✅ 找到 redirectUrl: {rank_data['redirectUrl']}")

        # 检查所有字段
        logger.info(f"\n所有字段: {list(rank_data.keys())}")

        # 检查状态
        status = rank_data.get('status', '')
        logger.info(f"\n当前状态: '{status}'")

        if status in ['ENTER', 'READY', 'SUCCESS', 'OK']:
            logger.info("✅ 状态显示可以进入！")

            # 尝试访问 redirectUrl 或获取 sessionId
            if 'redirectUrl' in rank_data:
                redirect_url = rank_data['redirectUrl']
                logger.info(f"\n尝试访问 redirectUrl: {redirect_url}")

                # 访问重定向 URL
                redirect_response = client.get(redirect_url, allow_redirects=True)
                logger.info(f"Redirect Status: {redirect_response.status_code}")
                logger.info(f"Final URL: {redirect_response.url}")

                # 检查 cookies
                if redirect_response.cookies:
                    logger.info(f"\n收到的 Cookies:")
                    for cookie in redirect_response.cookies:
                        logger.info(f"  {cookie.name}: {cookie.value[:100] if len(cookie.value) > 100 else cookie.value}")
    else:
        logger.warning("⚠️ Rank 响应为空")

    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_rank_and_session()
