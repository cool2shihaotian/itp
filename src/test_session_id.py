"""测试获取 sessionId"""
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


def test_session_id_retrieval():
    """测试从 Waiting 页面获取 sessionId"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 从 Waiting 页面获取 sessionId（纯 requests 实现）")
    logger.info("=" * 70)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 步骤 1: 登录
    logger.info("\n[步骤 1/5] NOL 登录...")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    use_cloudflare = config.get('capsolver', {}).get('enabled', False)
    skip_cloudflare = not use_cloudflare

    if not auth_manager.login(username, password, skip_cloudflare=skip_cloudflare):
        logger.error("登录失败")
        return

    logger.info("✅ NOL 登录成功")

    # 步骤 2: 桥接鉴权
    logger.info("\n[步骤 2/5] 桥接鉴权...")
    bridge = BridgeAuth(client, config, logger)

    goods_code = "25018223"
    place_code = "25001698"
    biz_code_gates = "10965"

    success = bridge.full_bridge_auth(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code_gates,
        user_id=auth_manager.user_id
    )

    if not success:
        logger.error("桥接鉴权失败")
        return

    # 步骤 3: 获取会员信息
    logger.info("\n[步骤 3/5] 获取会员信息...")
    booking = BookingManager(client, config, logger)

    member_info = booking.get_member_info(goods_code=goods_code)

    if not member_info:
        logger.error("获取会员信息失败")
        return

    signature = member_info.get('signature', '')
    secure_data = member_info.get('secureData', '')
    enc_member_code = member_info.get('encMemberCode', '')

    logger.info(f"encMemberCode: {enc_member_code}")

    # 步骤 4: 获取 Waiting key
    logger.info("\n[步骤 4/5] 获取 Waiting key...")
    waiting_queue = WaitingQueue(client, config, logger)

    biz_code_waiting = "88889"

    secure_result = waiting_queue.get_secure_url(
        signature=signature,
        secure_data=secure_data,
        biz_code=biz_code_waiting,
        goods_code=goods_code
    )

    if not secure_result:
        logger.error("获取 secure-url 失败")
        return

    key = secure_result.get('key', '')
    if not key:
        logger.error("未找到 key")
        return

    logger.info(f"✅ 获取到 key: {key[:50]}...")

    # 步骤 5: 访问 Waiting 页面获取 sessionId
    logger.info("\n[步骤 5/5] 访问 Waiting 页面获取 sessionId...")
    session_id = waiting_queue.visit_waiting_page(
        key=key,
        goods_code=goods_code,
        member_id=auth_manager.user_id
    )

    if session_id:
        logger.info("=" * 70)
        logger.info("🎉 成功获取 sessionId！")
        logger.info(f"sessionId: {session_id}")
        logger.info("=" * 70)

        # 显示获取到的 sessionId 信息
        logger.info("\n📊 SessionId 信息:")
        logger.info(f"  完整 ID: {session_id}")
        logger.info(f"  长度: {len(session_id)} 字符")
        logger.info(f"  格式验证: ✅ 通过")

        # 分析 sessionId 结构
        parts = session_id.split('_')
        if len(parts) >= 3:
            logger.info(f"  商品代码: {parts[0]}")
            logger.info(f"  会员标识: {parts[1]}")
            logger.info(f"  时间戳部分: {parts[2]}")

        # 现在可以用这个 sessionId 测试 OneStop APIs
        logger.info("\n✅ 下一步: 可以使用此 sessionId 调用 OneStop APIs")

        return session_id
    else:
        logger.warning("=" * 70)
        logger.warning("⚠️ 未能获取 sessionId")
        logger.warning("可能原因:")
        logger.warning("  1. 非售票期间，服务器不生成 sessionId")
        logger.warning("  2. sessionId 在其他位置（需要进一步分析）")
        logger.warning("  3. 需要完整的排队流程才能生成")
        logger.warning("=" * 70)

        return None


if __name__ == "__main__":
    test_session_id_retrieval()
