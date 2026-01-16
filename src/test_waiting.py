"""测试排队系统"""
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


def test_waiting_queue():
    """测试完整的排队流程"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试 Interpark 排队系统")
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

    # 步骤 3: 获取会员信息（获取 signature 和 secureData）
    logger.info("\n[步骤 3/5] 获取会员信息...")
    booking = BookingManager(client, config, logger)

    member_info = booking.get_member_info(goods_code=goods_code)

    if not member_info:
        logger.error("获取会员信息失败")
        return

    logger.info("✅ 会员信息获取成功")
    logger.info(f"响应数据: {json.dumps(member_info, indent=2, ensure_ascii=False)}")

    # 提取关键参数
    signature = member_info.get('signature', '')
    secure_data = member_info.get('secureData', '')

    if not signature or not secure_data:
        logger.error("会员信息中缺少 signature 或 secureData")
        return

    logger.info(f"✅ 提取到 signature: {signature[:20]}...")
    logger.info(f"✅ 提取到 secureData: {secure_data[:20]}...")

    # 步骤 4: 排队系统
    logger.info("\n[步骤 4/5] 进入排队系统...")
    waiting_queue = WaitingQueue(client, config, logger)

    biz_code_waiting = "88889"  # waiting 阶段使用不同的 biz_code

    success = waiting_queue.full_waiting_queue(
        signature=signature,
        secure_data=secure_data,
        goods_code=goods_code,
        biz_code=biz_code_waiting,
        skip_waf=True  # 暂时跳过 AWS WAF
    )

    if not success:
        logger.error("排队失败")
        return

    logger.info("✅ 排队成功！")

    # 步骤 5: 检查结果
    logger.info("\n[步骤 5/5] 检查排队结果...")
    logger.info(f"waiting_id: {waiting_queue.waiting_id}")
    logger.info(f"session_id: {waiting_queue.session_id}")
    logger.info(f"secure_url: {waiting_queue.secure_url}")

    logger.info("\n" + "=" * 70)
    logger.info("排队系统测试完成！")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_waiting_queue()
