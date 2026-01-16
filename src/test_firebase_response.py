"""测试 Firebase 登录返回值"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient


def test_firebase_login_response():
    """测试 Firebase 登录并详细打印返回值"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 50)
    logger.info("测试 Firebase 登录返回值")
    logger.info("=" * 50)

    client = ITPClient(config, logger)

    # Firebase 登录
    from src import api_config

    firebase_url = f"{api_config.FIREBASE_CONFIG['signin_url']}?key={api_config.FIREBASE_CONFIG['api_key']}"

    headers = {
        'Content-Type': 'application/json',
        'Origin': 'https://world.nol.com',
        'Referer': 'https://world.nol.com/',
        'x-browser-channel': 'stable',
        'x-browser-year': api_config.FIREBASE_CONFIG['browser_year'],
        'x-client-version': api_config.FIREBASE_CONFIG['client_version'],
        'x-firebase-gmpid': api_config.FIREBASE_CONFIG['gmp_id'],
        'x-client-data': 'CI+2yQEIprbJAQipncoBCJ3hygEIlaHLAQiGoM0BGO+izwE=',
    }

    client.update_headers(headers)

    login_data = {
        "email": config['account']['username'],
        "password": config['account']['password'],
        "returnSecureToken": True,
        "clientType": "CLIENT_TYPE_WEB"
    }

    logger.info(f"\n发送 Firebase 登录请求到:")
    logger.info(f"URL: {firebase_url}")
    logger.info(f"Data: {json.dumps(login_data, indent=2)}")

    response = client.post(firebase_url, json=login_data)

    logger.info(f"\n响应状态码: {response.status_code}")
    logger.info(f"\n完整返回值:")
    logger.info(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        result = response.json()
        logger.info(f"\n返回字段列表:")
        for key in result.keys():
            value = result[key]
            if isinstance(value, str) and len(value) > 50:
                logger.info(f"  {key}: {value[:50]}...")
            else:
                logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    test_firebase_login_response()
