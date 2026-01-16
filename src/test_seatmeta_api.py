"""测试 seatMeta 接口

验证获取座位元数据的接口参数
"""

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


def test_seatmeta_api():
    """测试 seatMeta API 参数"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试 seatMeta API")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 登录
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])

    # Bridge Auth
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1'))

    # 获取会员信息
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    # Waiting
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # Rank
    time.sleep(4)
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}
    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error(f"❌ Rank 失败: {response2.status_code}")
        return False

    rank_data = response2.json()
    session_id = rank_data.get('sessionId', '')
    logger.info(f"✅ Session ID: {session_id}")

    # Middleware
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 测试不同的 playSeq 格式
    logger.info("\n" + "=" * 70)
    logger.info("测试不同的 playSeq 格式")
    logger.info("=" * 70)

    play_seq_variants = [
        "001",           # 简单格式
        "202602120001",  # 日期 + 序号
        "2501822300001", # goodsCode + 序号
    ]

    seatmeta_url = "https://tickets.interpark.com/onestop/api/seatMeta"

    for play_seq in play_seq_variants:
        logger.info(f"\n测试 playSeq: {play_seq}")

        # 先测试获取 block-data
        block_url = "https://tickets.interpark.com/onestop/api/seats/block-data"
        block_params = {
            'goodsCode': '25018223',
            'placeCode': '25001698',
            'playSeq': play_seq
        }

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://tickets.interpark.com/onestop/seat',
            'x-onestop-channel': 'TRIPLE_KOREA',
            'x-onestop-session': session_id,
            'x-requested-with': 'XMLHttpRequest'
        }

        # 测试 block-data
        response = client.get(block_url, params=block_params, headers=headers)
        logger.info(f"  block-data 响应: {response.status_code}")

        if response.status_code == 200:
            blocks = response.json()
            logger.info(f"  ✅ 获取到 {len(blocks)} 个区域")

            if len(blocks) > 0:
                block_key = blocks[0].get('blockKey')
                logger.info(f"  第一个区域: {block_key}")

                # 测试 seatMeta
                logger.info(f"  测试 seatMeta...")
                seatmeta_params = [
                    ('goodsCode', '25018223'),
                    ('placeCode', '25001698'),
                    ('playSeq', play_seq),
                    ('blockKeys', block_key)
                ]

                response2 = client.get(seatmeta_url, params=seatmeta_params, headers=headers)
                logger.info(f"  seatMeta 响应: {response2.status_code}")

                if response2.status_code == 200:
                    seat_data = response2.json()
                    if len(seat_data) > 0 and len(seat_data[0].get('seats', [])) > 0:
                        logger.info(f"  ✅ 成功！获取到座位数据")
                        logger.info(f"  座位数量: {len(seat_data[0]['seats'])}")

                        # 显示第一个座位
                        first_seat = seat_data[0]['seats'][0]
                        logger.info(f"  第一个座位示例:")
                        logger.info(f"    seatInfoId: {first_seat.get('seatInfoId')}")
                        logger.info(f"    seatGrade: {first_seat.get('seatGrade')}")
                        logger.info(f"    isExposable: {first_seat.get('isExposable')}")
                        logger.info(f"    salesPrice: {first_seat.get('salesPrice')}")

                        return True
                else:
                    logger.warning(f"  ❌ seatMeta 失败: {response2.text[:200]}")
        else:
            logger.warning(f"  ❌ block-data 失败: {response.text[:200]}")

        time.sleep(1)

    logger.error("\n❌ 所有 playSeq 格式都失败了")
    return False


if __name__ == "__main__":
    try:
        success = test_seatmeta_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
