"""测试 Capmonster AWS WAF 配置"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging


def test_capmonster_config():
    """测试 Capmonster 配置是否正确"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试 Capmonster 配置")
    logger.info("=" * 70)

    # 检查 Capmonster 配置
    capmonster_config = config.get('capmonster', {})
    enabled = capmonster_config.get('enabled', False)
    api_key = capmonster_config.get('api_key', '')
    use_proxy = capmonster_config.get('use_proxy', False)

    logger.info(f"\n📋 Capmonster 配置:")
    logger.info(f"  启用状态: {'✅ 已启用' if enabled else '❌ 未启用'}")
    logger.info(f"  API Key: {'✅ 已配置' if api_key else '❌ 未配置'}")
    logger.info(f"  使用代理: {'✅ 是' if use_proxy else '❌ 否'}")

    if enabled:
        if not api_key:
            logger.error("\n❌ Capmonster 已启用但未配置 API Key")
            logger.error("请在 config.yaml 中设置 capmonster.api_key")
            return False

        logger.info("\n✅ Capmonster 配置正确")
        logger.info("\n📖 详细配置指南请查看: docs/CAPMONSTER_SETUP.md")

        # 尝试导入模块验证
        try:
            from src.aws_waf import CapmonsterClient
            logger.info("✅ Capmonster 模块导入成功")

            # 可选：测试 API 连接
            logger.info("\n💡 提示: 如需测试 API 连接，请确保账户有余额")
            logger.info("   可以在售票期间运行 test_waiting.py 进行完整测试")

        except ImportError as e:
            logger.error(f"❌ Capmonster 模块导入失败: {e}")
            return False

        return True
    else:
        logger.info("\nℹ️ Capmonster 未启用")
        logger.info("   如需启用，请在 config.yaml 中设置:")
        logger.info("   capmonster:")
        logger.info("     enabled: true")
        logger.info("     api_key: 'YOUR_API_KEY'")
        return True


def test_capmonster_api():
    """测试 Capmonster API 连接（需要 API Key 和余额）"""
    import requests

    config = load_config()
    logger = setup_logging(config)

    capmonster_config = config.get('capmonster', {})
    api_key = capmonster_config.get('api_key')

    if not api_key:
        logger.error("❌ 未配置 API Key，无法测试")
        return False

    logger.info("\n" + "=" * 70)
    logger.info("测试 Capmonster API 连接")
    logger.info("=" * 70)

    try:
        # 测试获取余额
        response = requests.post(
            "https://api.capmonster.cloud/getBalance",
            json={"clientKey": api_key},
            timeout=10
        )

        result = response.json()

        if result.get("errorId") == 0:
            balance = result.get("balance", 0)
            currency = result.get("currency", "USD")
            logger.info(f"✅ API 连接成功")
            logger.info(f"💰 账户余额: {balance} {currency}")
            return True
        else:
            error_msg = result.get("errorDescription", "Unknown error")
            logger.error(f"❌ API 错误: {error_msg}")
            return False

    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试 Capmonster 配置")
    parser.add_argument("--test-api", action="store_true",
                       help="测试 API 连接（需要余额）")
    args = parser.parse_args()

    # 测试配置
    config_ok = test_capmonster_config()

    # 如果需要测试 API
    if args.test_api and config_ok:
        print()
        test_capmonster_api()

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
