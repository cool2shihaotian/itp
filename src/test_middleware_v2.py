"""测试 OneStop Middleware V2 - 基于 rank 放行材料"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.waiting import WaitingQueue
from src.onestop_middleware_v2 import OneStopMiddlewareV2


def test_middleware_v2():
    """测试基于 rank 放行材料的 middleware"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试: OneStop Middleware V2 (基于 rank 放行材料)")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # 1. NOL 登录
    logger.info("\n[步骤 1/6] NOL 登录")
    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    # 2. 桥接鉴权
    logger.info("\n[步骤 2/6] 桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    # 3. 获取会员信息
    logger.info("\n[步骤 3/6] 获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    logger.info(f"✅ Member Code: {member_info['memberCode']}")
    logger.info(f"✅ EncMemberCode: {member_info['encMemberCode'][:50]}...")

    # 4. Waiting 流程
    logger.info("\n[步骤 4/6] Waiting 排队流程")
    waiting = WaitingQueue(client, config, logger)

    # 4.1 secure-url
    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )
    key = secure_result['key']
    logger.info(f"✅ Key: {key[:50]}...")

    # 4.2 line-up
    waiting.line_up(key=key)
    logger.info(f"✅ Waiting ID: {waiting.waiting_id}")

    # 4.3 rank 轮询
    logger.info("\n[步骤 5/6] Rank 轮询（获取放行材料）")
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}

    # 第一次 rank
    response1 = client.get(rank_url, params=params)
    logger.info(f"第 1 次 rank: {response1.status_code}")
    if response1.status_code == 200:
        rank1 = response1.json()
        logger.info(f"totalRank: {rank1.get('totalRank')}")
        logger.info(f"redirectChannel: {rank1.get('redirectChannel')}")

    # 等待 2 秒
    time.sleep(2)

    # 第二次 rank（应该获取到放行材料）
    response2 = client.get(rank_url, params=params)
    logger.info(f"第 2 次 rank: {response2.status_code}")

    if response2.status_code != 200:
        logger.error("❌ Rank 失败")
        return False

    rank_data = response2.json()

    if 'sessionId' not in rank_data:
        logger.error("❌ Rank 响应中无 sessionId")
        logger.info(f"响应: {json.dumps(rank_data, indent=2, ensure_ascii=False)}")
        return False

    logger.info(f"\n✅ 获取到放行材料:")
    logger.info(f"  sessionId: {rank_data['sessionId']}")
    logger.info(f"  oneStopUrl: {rank_data.get('oneStopUrl', '')[:100]}...")
    logger.info(f"  key: {rank_data.get('key', '')[:50]}...")
    logger.info(f"  k (signature): {rank_data.get('k', '')[:50]}...")
    logger.info(f"  totalRank: {rank_data.get('totalRank')}")
    logger.info(f"  redirectChannel: {rank_data.get('redirectChannel')}")

    # 保存完整的 rank 数据
    logger.info(f"\n完整 rank 数据:")
    logger.info(json.dumps(rank_data, indent=2, ensure_ascii=False))

    # 5. Middleware V2
    logger.info("\n[步骤 6/6] Middleware V2（基于放行材料）")
    middleware_v2 = OneStopMiddlewareV2(client, config, logger)

    middleware_success = middleware_v2.call_middleware_set_cookie(rank_data)

    # 6. 测试 OneStop API
    logger.info("\n" + "=" * 70)
    logger.info("测试 OneStop play-date API")
    logger.info("=" * 70)

    onestop_url = f"https://tickets.interpark.com/onestop/api/play/play-date/25018223"
    onestop_params = {
        'placeCode': '25001698',
        'bizCode': '88889',
        'sessionId': rank_data['sessionId'],
        'entMemberCode': member_info['encMemberCode']
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://tickets.interpark.com/onestop/schedule',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    client.update_headers(headers)

    logger.info(f"请求 URL: {onestop_url}")
    logger.info(f"请求参数: {json.dumps(onestop_params, indent=2)}")

    onestop_response = client.get(onestop_url, params=onestop_params)
    logger.info(f"\n响应状态码: {onestop_response.status_code}")

    if onestop_response.status_code == 200:
        logger.info("✅ 成功！OneStop API 调用成功！")
        result = onestop_response.json()
        logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        logger.info("\n" + "=" * 70)
        logger.info("🎉 完全成功！Middleware V2 生效！")
        logger.info("=" * 70)
        return True
    else:
        logger.warning(f"⚠️ OneStop API 失败: {onestop_response.status_code}")
        logger.info(f"响应: {onestop_response.text[:500]}")

        # 尝试使用 oneStopUrl 作为 referer
        logger.info("\n尝试使用 oneStopUrl 作为 Referer...")
        headers['Referer'] = rank_data.get('oneStopUrl', '')
        client.update_headers(headers)

        onestop_response2 = client.get(onestop_url, params=onestop_params)
        logger.info(f"响应状态码: {onestop_response2.status_code}")

        if onestop_response2.status_code == 200:
            logger.info("✅ 使用 oneStopUrl 作为 Referer 成功！")
            result = onestop_response2.json()
            logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            logger.info("\n" + "=" * 70)
            logger.info("🎉 成功！需要使用 oneStopUrl 作为 Referer")
            logger.info("=" * 70)
            return True
        else:
            logger.info(f"响应: {onestop_response2.text[:500]}")

            logger.info("\n" + "=" * 70)
            logger.info("ℹ️ OneStop API 仍然失败")
            logger.info("可能需要进一步调试")
            logger.info("=" * 70)
            return False


if __name__ == "__main__":
    try:
        success = test_middleware_v2()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ 测试完全成功！")
        else:
            logger.info("ℹ️ 测试未完全成功，需要进一步调试")
        logger.info("=" * 70)

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
