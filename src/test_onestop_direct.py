"""测试 OneStop - 直接使用 Waiting key"""
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


def test_onestop_direct():
    """直接使用 Waiting key 测试 OneStop"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试 OneStop - 直接使用 Waiting key")
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

    # 获取 key
    key = secure_result.get('key', '')
    if not key:
        logger.error("未找到 key")
        return

    logger.info(f"✅ 获取到 key: {key[:50]}...")

    # 从 redirectUrl 中提取 sessionId（如果有）
    redirect_url = secure_result.get('redirectUrl', '')
    session_id = None

    logger.info(f"redirect_url: {redirect_url[:200] if redirect_url else 'None'}...")

    if redirect_url:
        # 尝试从 URL 中提取 sessionId
        if 'sessionId=' in redirect_url:
            session_id = redirect_url.split('sessionId=')[-1].split('&')[0]
            logger.info(f"✅ 提取到 sessionId: {session_id}")
        elif 'M00000' in redirect_url:  # sessionId 的特征
            # 尝试匹配模式：25018223_M0000000751971768530066
            import re
            match = re.search(r'(\d+_M\d+_\d+)', redirect_url)
            if match:
                session_id = match.group(1)
                logger.info(f"✅ 通过正则提取到 sessionId: {session_id}")

    if not session_id:
        logger.warning("⚠️ 未能提取到 sessionId，可能会影响 OneStop API 调用")

    # 步骤 5: 测试 OneStop APIs
    logger.info("\n[步骤 5/5] 测试 OneStop APIs...")
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

        # 获取第一个日期
        if play_dates and 'playDate' in play_dates and len(play_dates['playDate']) > 0:
            first_date = play_dates['playDate'][0]
            logger.info(f"第一个演出日期: {first_date}")
    else:
        logger.error("❌ 演出日期获取失败")

    # 测试 2: Session Check
    if session_id:
        logger.info("\n测试 2: Session Check")
        session_check = onestop.check_session(
            goods_code=goods_code,
            play_seq=None,
            biz_code=biz_code_onestop
        )
        if session_check:
            logger.info("✅ Session check 成功")
        else:
            logger.warning("⚠️ Session check 失败")

    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_onestop_direct()
