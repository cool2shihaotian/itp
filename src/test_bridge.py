"""测试桥接鉴权"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth


def test_bridge_auth():
    """测试桥接鉴权流程"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试 NOL → Interpark 桥接鉴权")
    logger.info("=" * 70)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 登录
    logger.info("\n[步骤 1/3] NOL 登录...")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    use_cloudflare = config.get('capsolver', {}).get('enabled', False)
    skip_cloudflare = not use_cloudflare

    if not auth_manager.login(username, password, skip_cloudflare=skip_cloudflare):
        logger.error("登录失败")
        return

    logger.info("✅ NOL 登录成功")

    # 桥接鉴权
    logger.info("\n[步骤 2/3] 桥接鉴权...")
    bridge = BridgeAuth(client, config, logger)

    goods_code = "25018223"
    place_code = "25001698"
    biz_code = "10965"

    success = bridge.full_bridge_auth(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code,
        user_id=auth_manager.user_id
    )

    if not success:
        logger.error("桥接鉴权失败")
        return

    # 测试 Gates 接口
    logger.info("\n[步骤 3/3] 测试 Gates 接口...")
    from src.booking import BookingManager
    booking = BookingManager(client, config, logger)

    # 现在应该可以成功调用这些接口了
    goods_info = booking.get_goods_info(goods_code, place_code, biz_code)
    member_info = booking.get_member_info(goods_code)

    if goods_info:
        logger.info("✅ goods-info 成功")
    if member_info:
        logger.info("✅ member-info 成功")

    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_bridge_auth()
