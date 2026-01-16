"""测试座位和预订接口"""
import sys
import json
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.booking import BookingManager


def test_booking_apis():
    """测试座位和预订 API"""
    # 加载配置
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("开始测试座位和预订接口")
    logger.info("=" * 70)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 登录
    logger.info("\n[1/4] 登录...")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    use_cloudflare = config.get('capsolver', {}).get('enabled', False)
    skip_cloudflare = not use_cloudflare

    if not auth_manager.login(username, password, skip_cloudflare=skip_cloudflare):
        logger.error("登录失败，无法继续测试")
        return

    logger.info("✅ 登录成功\n")

    # 初始化预订管理器
    booking_manager = BookingManager(client, config, logger)

    # 测试商品代码和场馆代码（从 HAR 中提取）
    goods_code = "25018223"
    place_code = "25001698"
    biz_code = "10965"

    logger.info(f"[2/4] 测试商品: {goods_code}, 场馆: {place_code}")
    logger.info("-" * 70)

    # 测试 1: 获取商品信息（座位图）
    logger.info("\n🎫 测试 1: 获取商品信息（座位图）")
    goods_info = booking_manager.get_goods_info(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code
    )

    if goods_info:
        logger.info("✅ 商品信息获取成功")
        logger.info(f"响应数据: {json.dumps(goods_info, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 商品信息获取失败")

    # 测试 2: 获取会员信息
    logger.info("\n👤 测试 2: 获取会员预订信息")
    member_info = booking_manager.get_member_info(goods_code=goods_code)

    if member_info:
        logger.info("✅ 会员信息获取成功")
        logger.info(f"响应数据: {json.dumps(member_info, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 会员信息获取失败")

    # 测试 3: 检查 eKYC 认证
    logger.info("\n🔐 测试 3: 检查 eKYC 认证状态")
    ekyc_auth = booking_manager.check_ekyc_auth(biz_code=biz_code)

    if ekyc_auth:
        logger.info("✅ eKYC 认证状态获取成功")
        logger.info(f"响应数据: {json.dumps(ekyc_auth, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ eKYC 认证状态获取失败")

    logger.info("\n" + "=" * 70)
    logger.info("座位和预订接口测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_booking_apis()
