"""调试 Waiting secure-url API"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager


def test_waiting_api_debug():
    """调试 Waiting secure-url API"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("调试 Waiting secure-url API")
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

    logger.info(f"Signature: {signature[:50]}...")
    logger.info(f"SecureData: {secure_data[:50]}...")

    # 步骤 4: 测试不同的 bizCode
    logger.info("\n[步骤 4/4] 测试不同的 bizCode...")

    # 从商品信息中获取实际的 bizCode
    goods_info = booking.get_goods_info(goods_code, place_code, biz_code_gates)
    if goods_info:
        actual_biz_code = goods_info.get('bizCode', '')
        reserve_biz_code = goods_info.get('reserveBizCode', '')
        logger.info(f"商品信息中的 bizCode: {actual_biz_code}")
        logger.info(f"商品信息中的 reserveBizCode: {reserve_biz_code}")

    # 尝试不同的 bizCode
    bizCodes_to_try = [
        ("61677", "商品信息中的 bizCode"),
        ("10965", "商品信息中的 reserveBizCode"),
        ("88889", "我们假设的 waiting/onestop code"),
    ]

    import requests

    for biz_code, description in bizCodes_to_try:
        logger.info(f"\n{'='*70}")
        logger.info(f"尝试 bizCode: {biz_code} ({description})")
        logger.info(f"{'='*70}")

        url = "https://ent-waiting-api.interpark.com/waiting/api/secure-url"

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://tickets.interpark.com',
            'Referer': 'https://tickets.interpark.com/',
        }

        data = {
            'bizCode': biz_code,
            'secureData': secure_data,
            'signature': signature,
            'goodsCode': goods_code,
        }

        logger.info(f"请求 URL: {url}")
        logger.info(f"请求头: {json.dumps(headers, indent=2)}")
        logger.info(f"请求体: {json.dumps(data, indent=2)}")

        try:
            response = client.post(url, json=data)

            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ 成功！ bizCode={biz_code}")
                logger.info(f"响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    logger.error(f"❌ 失败: {json.dumps(error_data, indent=2)}")
                except:
                    logger.error(f"❌ 失败: {response.text}")
            else:
                logger.error(f"❌ 失败: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ 异常: {e}", exc_info=True)

    # 如果所有 bizCode 都失败，尝试其他格式
    logger.info(f"\n{'='*70}")
    logger.info("尝试不同的请求格式...")
    logger.info(f"{'='*70}")

    # 尝试 form-data 格式
    logger.info("\n尝试 1: form-data 格式")
    url = "https://ent-waiting-api.interpark.com/waiting/api/secure-url"

    headers_form = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://tickets.interpark.com',
        'Referer': 'https://tickets.interpark.com/',
    }

    data_form = f'bizCode=61677&secureData={secure_data}&signature={signature}&goodsCode={goods_code}'

    logger.info(f"Content-Type: application/x-www-form-urlencoded")
    logger.info(f"请求体: {data_form[:200]}...")

    try:
        response = requests.post(url, headers=headers_form, data=data_form, cookies=client.session.cookies)
        logger.info(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"✅ form-data 格式成功！")
            logger.info(f"响应: {response.json()}")
        else:
            logger.error(f"❌ form-data 格式也失败: {response.text}")
    except Exception as e:
        logger.error(f"❌ form-data 格式异常: {e}")

    logger.info("\n" + "=" * 70)
    logger.info("调试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    test_waiting_api_debug()
