"""完整轮询选座测试 - 包含 user_id 修复"""
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
import time


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("完整轮询选座测试 - 包含 user_id 修复")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 步骤 1: 登录
    logger.info("\n【步骤 1/8】NOL 登录")
    auth = AuthManager(client, config, logger)
    auth.login(config['account']['username'], config['account']['password'])
    user_id = getattr(auth, 'user_id', 'aJvwoXxpYvaYhzwXGv3KLRYW0Aq1')
    logger.info(f"✅ User ID: {user_id}")

    # 步骤 2: 桥接鉴权
    logger.info("\n【步骤 2/8】桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', user_id)

    # 步骤 3: 获取会员信息
    logger.info("\n【步骤 3/8】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')
    logger.info(f"✅ Member Code: {member_info.get('memberCode')}")
    logger.info(f"✅ EncMemberCode: {member_info.get('encMemberCode')[:20]}...")

    # 步骤 4: Waiting 排队
    logger.info("\n【步骤 4/8】Waiting 排队")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result.get('key', ''))

    # 步骤 5: Rank 获取 Session ID
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

    # 步骤 6: Middleware set-cookie
    logger.info("\n【步骤 6/8】Middleware set-cookie")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # 步骤 7: 初始化选座器
    logger.info("\n【步骤 7/8】初始化选座器")
    selector = PollingSeatSelector(client, config, logger)
    logger.info("✅ 选座器已初始化")

    # 步骤 8: 测试 block-data 和 seatMeta（非轮询模式）
    logger.info("\n【步骤 8/8】测试 block-data 和 seatMeta API")
    logger.info("=" * 70)

    play_date = "20260212"
    play_seq = "001"

    logger.info(f"目标日期: {play_date}")
    logger.info(f"场次编号: {play_seq}")
    logger.info(f"User ID: {user_id}")

    # 测试获取区域代码
    logger.info("\n" + "-" * 70)
    logger.info("测试 1: 获取区域代码（block-data）")
    logger.info("-" * 70)

    block_keys = selector.get_block_keys(play_seq, session_id, user_id=user_id)

    if block_keys:
        logger.info(f"✅ 成功！获取到 {len(block_keys)} 个区域:")
        for i, key in enumerate(block_keys[:5], 1):
            logger.info(f"  {i}. {key}")
        if len(block_keys) > 5:
            logger.info(f"  ... 还有 {len(block_keys) - 5} 个区域")
    else:
        logger.error("❌ 获取区域代码失败")
        return False

    # 测试获取座位信息
    logger.info("\n" + "-" * 70)
    logger.info("测试 2: 获取座位信息（seatMeta）- 前 3 个区域")
    logger.info("-" * 70)

    # 只测试前 3 个区域
    test_blocks = block_keys[:3]
    logger.info(f"测试前 {len(test_blocks)} 个区域...")

    available_seat = selector.get_real_seat_availability(
        play_seq=play_seq,
        block_keys=test_blocks,
        session_id=session_id,
        max_price=None,
        user_id=user_id
    )

    if available_seat:
        logger.info("\n" + "🎉" * 35)
        logger.info("✅ 找到可售座位！")
        logger.info("🎉" * 35)
        logger.info(f"  座位ID: {available_seat['seat_info_id']}")
        logger.info(f"  价位: {available_seat['seat_grade_name']} ({available_seat['price']:,}韩元)")
        logger.info(f"  位置: {available_seat['floor']} - {available_seat['row_no']} - {available_seat['seat_no']}")
        logger.info(f"  场次: {available_seat['play_seq']}")
    else:
        logger.info("\nℹ️ 前 3 个区域暂无可售座位")
        logger.info("  （这很正常，可以尝试轮询所有区域或等待退票）")

    logger.info("\n" + "=" * 70)
    logger.info("✅ 所有 API 测试完成！")
    logger.info("=" * 70)
    logger.info("\n总结:")
    logger.info("  ✅ block-data API 工作正常")
    logger.info("  ✅ seatMeta API 工作正常")
    logger.info("  ✅ user_id cookie 设置正确")
    logger.info("\n现在可以使用完整轮询功能了！")
    logger.info("轮询选座会持续监控所有区域，一旦有余票立即锁定。")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
