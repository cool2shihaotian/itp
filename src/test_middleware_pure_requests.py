"""测试纯 requests 实现 OneStop Middleware（基于时间同步）"""
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
from src.onestop import OneStopBooking


def test_middleware_with_time_sync():
    """测试基于时间同步的 middleware 实现"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: OneStop Middleware (纯 requests + 时间同步)")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 1. NOL 登录
    logger.info("\n" + "=" * 70)
    logger.info("步骤 1: NOL 登录")
    logger.info("=" * 70)

    auth_manager = AuthManager(client, config, logger)
    login_success = auth_manager.login(
        config['account']['username'],
        config['account']['password'],
        skip_cloudflare=False
    )

    if not login_success:
        logger.error("❌ 登录失败")
        return False

    # 2. 桥接鉴权
    logger.info("\n" + "=" * 70)
    logger.info("步骤 2: 桥接鉴权")
    logger.info("=" * 70)

    bridge = BridgeAuth(client, config, logger)
    bridge_success = bridge.full_bridge_auth(
        goods_code='25018223',
        place_code='25001698',
        biz_code='10965',
        user_id=auth_manager.user_id
    )

    if not bridge_success:
        logger.error("❌ 桥接鉴权失败")
        return False

    # 3. 获取会员信息
    logger.info("\n" + "=" * 70)
    logger.info("步骤 3: 获取会员信息")
    logger.info("=" * 70)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    if not member_info:
        logger.error("❌ 获取会员信息失败")
        return False

    logger.info(f"✅ Member Code: {member_info['memberCode']}")
    logger.info(f"✅ Signature: {member_info['signature'][:50]}...")
    logger.info(f"✅ SecureData: {member_info['secureData'][:50]}...")
    logger.info(f"✅ EncMemberCode: {member_info['encMemberCode'][:50]}...")

    # 4. Waiting 流程 - 获取 sessionId 和 oneStopUrl
    logger.info("\n" + "=" * 70)
    logger.info("步骤 4: Waiting 排队流程")
    logger.info("=" * 70)

    waiting = WaitingQueue(client, config, logger)

    # 4.1 获取 secure-url
    logger.info("\n[4.1] 获取 secure-url")
    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )

    if not secure_result or 'key' not in secure_result:
        logger.error("❌ 获取 secure-url 失败")
        return False

    key = secure_result['key']
    logger.info(f"✅ 获取 key: {key[:50]}...")

    # 4.2 Line-up
    logger.info("\n[4.2] Line-up")
    line_up_result = waiting.line_up(key=key)

    if not line_up_result:
        logger.error("❌ Line-up 失败")
        return False

    waiting_id = waiting.waiting_id
    logger.info(f"✅ Waiting ID: {waiting_id}")

    # 4.3 轮询 rank 获取 sessionId
    logger.info("\n[4.3] 轮询 rank 获取 sessionId")
    logger.info("提示: 可能需要多次轮询才能获取 sessionId")

    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting_id}

    # 轮询最多 10 次
    max_polls = 10
    session_id = None
    one_stop_url = None

    for i in range(1, max_polls + 1):
        logger.info(f"\n第 {i} 次 rank 调用...")

        response = client.get(rank_url, params=params)
        logger.info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                rank_data = response.json()
                logger.info(f"响应: {json.dumps(rank_data, indent=2, ensure_ascii=False)}")

                # 检查是否有 sessionId
                if 'sessionId' in rank_data:
                    session_id = rank_data['sessionId']
                    one_stop_url = rank_data.get('oneStopUrl', '')
                    logger.info(f"\n✅ 获取到 sessionId: {session_id}")
                    logger.info(f"✅ OneStop URL: {one_stop_url[:150] if one_stop_url else '(无)'}...")
                    break
                else:
                    logger.info("ℹ️ 响应中无 sessionId，继续轮询...")
                    # 检查 totalRank 或其他状态
                    if 'totalRank' in rank_data:
                        logger.info(f"totalRank: {rank_data['totalRank']}")
                    if 'redirectChannel' in rank_data:
                        logger.info(f"redirectChannel: {rank_data['redirectChannel']}")

            except json.JSONDecodeError:
                logger.warning(f"响应不是有效的 JSON: {response.text[:200]}")
        else:
            logger.warning(f"rank 失败: {response.status_code}")
            logger.info(f"响应: {response.text[:200]}")

        # 如果不是最后一次，等待 2 秒后继续
        if i < max_polls:
            logger.info("等待 2 秒后重试...")
            time.sleep(2)

    if not session_id:
        logger.error("❌ 未能获取 sessionId")
        logger.info("可能原因:")
        logger.info("  1. 排队未完成（需要更多轮询或更长时间）")
        logger.info("  2. 非售票期间")
        logger.info("  3. sessionId 尚未生成")
        logger.info("\n尝试使用模拟的 sessionId 继续...")
        # 生成一个模拟的 sessionId（基于格式）
        session_id = waiting.generate_session_id('25018223', '075260')
        one_stop_url = f"https://tickets.interpark.com/onestop?key=test-{int(time.time())}"

    # 5. OneStop Middleware（纯 requests 实现）
    logger.info("\n" + "=" * 70)
    logger.info("步骤 5: OneStop Middleware (纯 requests)")
    logger.info("=" * 70)

    onestop = OneStopBooking(client, config, logger)

    # 调用 middleware（使用新的基于时间的实现）
    middleware_result = onestop.set_middleware_cookie(
        goods_code='25018223',
        biz_code='88889',
        session_id=session_id,
        one_stop_url=one_stop_url
    )

    if middleware_result:
        logger.info(f"Middleware 结果: {middleware_result}")

    # 6. 测试 OneStop API
    logger.info("\n" + "=" * 70)
    logger.info("步骤 6: 测试 OneStop play-date API")
    logger.info("=" * 70)

    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info['encMemberCode']
    )

    if play_dates:
        logger.info("✅ 成功获取演出日期!")
        logger.info(f"响应: {json.dumps(play_dates, indent=2, ensure_ascii=False)}")
        return True
    else:
        logger.warning("⚠️ 获取演出日期失败")
        logger.info("可能原因:")
        logger.info("  1. Middleware 未正确设置 cookies")
        logger.info("  2. sessionId 时效性已过")
        logger.info("  3. 非售票期间")
        return False


if __name__ == "__main__":
    try:
        success = test_middleware_with_time_sync()

        # 重新创建 logger 用于输出最终结果
        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 测试成功!")
        else:
            logger.info("ℹ️ 测试未完全成功，但这是预期的（非售票期间）")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
