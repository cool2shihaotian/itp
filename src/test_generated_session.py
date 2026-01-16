"""测试使用生成的 sessionId"""
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
from src.onestop import OneStopBooking


def test_with_generated_session():
    """测试使用生成的 sessionId 调用 OneStop APIs"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: 使用生成的 sessionId 调用 OneStop")
    logger.info("=" * 70)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 步骤 1: 登录
    logger.info("\n[步骤 1/4] NOL 登录...")
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
    logger.info("\n[步骤 2/4] 桥接鉴权...")
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
    logger.info("\n[步骤 3/4] 获取会员信息...")
    booking = BookingManager(client, config, logger)

    member_info = booking.get_member_info(goods_code=goods_code)

    if not member_info:
        logger.error("获取会员信息失败")
        return

    signature = member_info.get('signature', '')
    secure_data = member_info.get('secureData', '')
    enc_member_code = member_info.get('encMemberCode', '')

    logger.info(f"encMemberCode: {enc_member_code}")

    # 步骤 4: 生成 sessionId
    logger.info("\n[步骤 4/4] 生成 sessionId 并测试 OneStop...")
    waiting_queue = WaitingQueue(client, config, logger)

    # 从 user_id 提取数字部分作为 member_id
    # user_id 格式类似: aJvwoXxpYvaYhzwXGv3KLRYW0Aq1
    # 我们使用数字哈希作为 member_id
    import hashlib
    user_id_hash = hashlib.md5(auth_manager.user_id.encode()).hexdigest()
    numeric_member_id = int(user_id_hash[:8], 16)  # 取前8位转数字

    logger.info(f"从 user_id 生成 member_id: {numeric_member_id}")

    # 生成 sessionId
    session_id = waiting_queue.generate_session_id(
        goods_code=goods_code,
        member_id=numeric_member_id
    )

    logger.info(f"✅ 生成 sessionId: {session_id}")

    # 测试 OneStop APIs
    logger.info("\n" + "=" * 70)
    logger.info("测试 OneStop APIs")
    logger.info("=" * 70)

    onestop = OneStopBooking(client, config, logger)
    biz_code_onestop = "88889"

    # 测试 1: 获取演出日期
    logger.info("\n测试 1: 获取演出日期列表")
    play_dates = onestop.get_play_dates(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code_onestop,
        session_id=session_id,
        ent_member_code=enc_member_code
    )

    if play_dates:
        logger.info("✅ 演出日期获取成功！")
        logger.info(f"响应: {json.dumps(play_dates, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 演出日期获取失败")

    # 测试 2: Session Check
    logger.info("\n测试 2: Session Check")
    session_check = onestop.check_session(
        goods_code=goods_code,
        play_seq=None,
        biz_code=biz_code_onestop
    )
    if session_check:
        logger.info("✅ Session check 成功")
        logger.info(f"响应: {json.dumps(session_check, indent=2, ensure_ascii=False)}")
    else:
        logger.warning("⚠️ Session check 失败")

    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_with_generated_session()
