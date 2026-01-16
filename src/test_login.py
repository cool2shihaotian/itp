"""测试登录功能"""
import sys
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager


def test_login():
    """测试登录功能"""
    # 加载配置
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 50)
    logger.info("开始测试登录功能")
    logger.info("=" * 50)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 初始化认证管理器
    auth_manager = AuthManager(client, config, logger)

    # 从配置获取账号信息
    username = config['account']['username']
    password = config['account']['password']

    if not username or not password:
        logger.error("请在 config.yaml 中配置账号信息")
        return

    # 检查是否启用 Capsolver
    use_cloudflare = config.get('capsolver', {}).get('enabled', False)

    # 测试登录
    skip_cloudflare = not use_cloudflare
    if skip_cloudflare:
        logger.info("将跳过 Cloudflare 验证（需在 config.yaml 中配置 Capsolver）")

    success = auth_manager.login(username, password, skip_cloudflare=skip_cloudflare)

    if success:
        logger.info("\n✅ 登录测试成功！")
        logger.info(f"User ID: {auth_manager.user_id}")
        logger.info(f"已登录: {auth_manager.is_logged_in()}")

        # 保存 cookies 以供后续使用
        auth_manager.client.save_cookies()
    else:
        logger.error("\n❌ 登录测试失败")

    logger.info("=" * 50)


if __name__ == "__main__":
    test_login()
