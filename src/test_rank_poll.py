"""测试连续轮询 rank API"""
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


def test_rank_polling():
    """连续轮询 rank API 观察状态变化"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 连续轮询 Rank API")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 快速登录和初始化
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth("25018223", "25001698", "10965", auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info("25018223")

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        member_info["signature"],
        member_info["secureData"],
        "88889",
        "25018223"
    )

    key = secure_result["key"]
    line_up_result = waiting.line_up(key)
    waiting_id = line_up_result["waitingId"]

    logger.info(f"\n✅ Line-up 成功")
    logger.info(f"Waiting ID: {waiting_id}")
    logger.info(f"User Seq: {line_up_result.get('userSeq')}")
    logger.info(f"Exist: {line_up_result.get('exist')}")

    # 连续轮询 rank
    logger.info("\n" + "=" * 70)
    logger.info("开始连续轮询 Rank API (10次)")
    logger.info("=" * 70)

    url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {
        "bizCode": "88889",
        "waitingId": waiting_id
    }

    for i in range(10):
        logger.info(f"\n[轮询 #{i+1}/10]")

        response = client.get(url, params=params)

        if response.status_code == 200 and response.text:
            rank_data = response.json()

            logger.info(f"myRank: {rank_data.get('myRank', 'N/A')}")
            logger.info(f"totalRank: {rank_data.get('totalRank', 'N/A')}")
            logger.info(f"bookingRate: {rank_data.get('bookingRate', 'N/A')}%")
            logger.info(f"k: '{rank_data.get('k', '')}'")

            # 检查关键字段
            if 'redirectUrl' in rank_data and rank_data['redirectUrl']:
                logger.info(f"✅ 发现 redirectUrl: {rank_data['redirectUrl']}")
                break

            if 'sessionId' in rank_data and rank_data['sessionId']:
                logger.info(f"✅ 发现 sessionId: {rank_data['sessionId']}")
                break

            # 检查 k 字段是否有值（可能是放行标识）
            k_value = rank_data.get('k', '')
            if k_value:
                logger.info(f"✅ k 字段有值: {k_value}")
                logger.info("这可能表示可以进入下一步")

                # 打印完整响应
                logger.info(f"\n完整响应:")
                logger.info(json.dumps(rank_data, indent=2, ensure_ascii=False))

                # k 字段格式可能是：signature.timestamp
                # 让我们尝试用这个 k 值和 waitingId 生成 sessionId
                # sessionId 格式: {goodsCode}_M00000{member_id}{timestamp}

                # 从 k 中提取 timestamp
                if '.' in k_value:
                    timestamp = k_value.split('.')[-1]
                    logger.info(f"\n从 k 字段提取的 timestamp: {timestamp}")

                    # 从 waitingId 提取 member_id
                    # waitingId 格式: 25018223:xxx:seq
                    goods_code = "25018223"
                    member_id = "75241"  # 从 userSeq 或 waitingId 提取

                    # 生成 sessionId
                    session_id = f"{goods_code}_M00000{member_id}{timestamp}"
                    logger.info(f"生成的 sessionId: {session_id}")

                break

            # 打印所有字段（第一次）
            if i == 0:
                logger.info(f"所有字段: {list(rank_data.keys())}")

        else:
            logger.warning(f"Rank 请求失败: {response.status_code}")

        time.sleep(2)  # 等待 2 秒

    logger.info("\n" + "=" * 70)
    logger.info("轮询测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_rank_polling()
