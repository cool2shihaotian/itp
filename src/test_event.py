"""测试活动信息接口"""
import sys
import json
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.event import EventManager


def test_event_apis():
    """测试活动信息 API"""
    # 加载配置
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 50)
    logger.info("开始测试活动信息接口")
    logger.info("=" * 50)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 登录
    logger.info("\n[1/2] 登录...")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    use_cloudflare = config.get('capsolver', {}).get('enabled', False)
    skip_cloudflare = not use_cloudflare

    if not auth_manager.login(username, password, skip_cloudflare=skip_cloudflare):
        logger.error("登录失败，无法继续测试")
        return

    logger.info("✅ 登录成功\n")

    # 初始化活动管理器
    event_manager = EventManager(client, config, logger)

    # 测试商品代码和场馆代码
    # 从你提供的抓包数据中提取
    goods_code = "25018689"
    place_code = "25001749"
    biz_code = "10965"

    logger.info(f"[2/2] 测试商品: {goods_code}, 场馆: {place_code}")
    logger.info("-" * 50)

    # 测试 1: 获取发售信息
    logger.info("\n📋 测试 1: 获取发售信息")
    sales_info = event_manager.get_sales_info(goods_code, place_code, biz_code)
    if sales_info:
        logger.info("✅ 发售信息获取成功")
        logger.info(f"响应数据: {json.dumps(sales_info, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 发售信息获取失败")

    # 测试 2: 用户进入活动
    logger.info("\n🎫 测试 2: 用户进入活动")
    enter_info = event_manager.enter_event(goods_code, place_code)
    if enter_info:
        logger.info("✅ 进入活动成功")
        logger.info(f"响应数据: {json.dumps(enter_info, indent=2, ensure_ascii=False)}")
    else:
        logger.error("❌ 进入活动失败")

    # 测试 3: 获取完整活动信息
    logger.info("\n📦 测试 3: 获取完整活动信息")
    event_detail = event_manager.get_event_detail(goods_code, place_code)
    if event_detail:
        logger.info("✅ 活动详细信息获取成功")

        # 分析返回的数据
        if event_detail.get("sales_info"):
            logger.info("\n📊 发售信息分析:")
            sales = event_detail["sales_info"]
            # 打印关键信息
            if isinstance(sales, dict):
                for key in sales.keys():
                    logger.info(f"  - {key}: {sales[key]}")

        if event_detail.get("enter_info"):
            logger.info("\n👤 用户进入信息分析:")
            enter = event_detail["enter_info"]
            if isinstance(enter, dict):
                for key in enter.keys():
                    logger.info(f"  - {key}: {enter[key]}")

    logger.info("\n" + "=" * 50)
    logger.info("活动信息接口测试完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    test_event_apis()
