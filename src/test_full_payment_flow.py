"""测试完整的付款流程

基于 HAR 文件分析的完整 Interpark 选座和付款流程测试
"""

import sys
import os
import json
import time
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.waiting import WaitingQueue
from src.onestop_middleware_v3 import OneStopMiddlewareV3
from src.onestop_with_fix import OneStopBookingFixed
from src.polling_seat_selector import PollingSeatSelector


def test_full_payment_flow():
    """测试完整的付款流程"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试完整付款流程")
    logger.info("=" * 70)

    # ===== 初始化 =====
    client = ITPClient(config, logger)

    # ===== 步骤 1: 登录 =====
    logger.info("\n【步骤 1/8】登录")
    auth_manager = AuthManager(client, config, logger)

    username = config.get('account', {}).get('username', '')
    password = config.get('account', {}).get('password', '')

    if not username or not password:
        logger.error("❌ 配置文件中未找到账号密码")
        logger.info("请在 config.yaml 中配置:")
        logger.info("  account:")
        logger.info("    username: your_email")
        logger.info("    password: your_password")
        return False

    login_success = auth_manager.login(username, password, skip_cloudflare=False)

    if not login_success:
        logger.error("❌ 登录失败")
        return False

    logger.info(f"✅ 登录成功！User ID: {auth_manager.user_id}")

    # ===== 步骤 2: Bridge Auth =====
    logger.info("\n【步骤 2/8】Bridge Auth")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)
    logger.info("✅ Bridge Auth 完成")

    # ===== 步骤 3: 获取会员信息 =====
    logger.info("\n【步骤 3/8】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    logger.info(f"✅ Member Code: {member_info.get('memberCode', 'N/A')}")

    # ===== 步骤 4: Waiting 排队 =====
    logger.info("\n【步骤 4/8】Waiting 排队")
    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info.get('signature', ''),
        secure_data=member_info.get('secureData', ''),
        biz_code='88889',
        goods_code='25018223'
    )

    waiting.line_up(secure_result.get('key', ''))
    logger.info(f"✅ Waiting ID: {waiting.waiting_id}")

    # ===== 步骤 5: Rank 轮询获取 sessionId =====
    logger.info("\n【步骤 5/8】Rank 轮询获取 sessionId")
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {
        'bizCode': '88889',
        'waitingId': waiting.waiting_id
    }

    # 第一次 rank 请求（开始排队）
    logger.info("第一次 rank 请求...")
    response1 = client.get(rank_url, params=params)
    if response1.status_code == 200:
        rank1_data = response1.json()
        logger.info(f"第一次 rank 成功，状态: {rank1_data.get('status', 'N/A')}")
    else:
        logger.warning(f"第一次 rank 返回 {response1.status_code}，继续尝试")

    # 等待更长时间（3-5秒）
    logger.info("等待 4 秒...")
    time.sleep(4)

    # 第二次 rank 请求（获取 sessionId）
    logger.info("第二次 rank 请求...")
    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error(f"❌ Rank 请求失败: {response2.status_code}")
        logger.error(f"响应: {response2.text}")
        return False

    rank_data = response2.json()
    session_id = rank_data.get('sessionId', '')

    if not session_id:
        logger.error("❌ 未获取到 sessionId")
        logger.error(f"Rank 响应: {json.dumps(rank_data, indent=2, ensure_ascii=False)}")
        return False

    logger.info(f"✅ Session ID: {session_id}")

    # ===== 步骤 6: Middleware =====
    logger.info("\n【步骤 6/8】Middleware")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_result = middleware_v3.call_middleware_set_cookie(rank_data)

    if not middleware_result:
        logger.warning("⚠️ Middleware 失败，但继续尝试")
    else:
        logger.info("✅ Middleware 完成")

    # ===== 步骤 7: 获取演出日期 =====
    logger.info("\n【步骤 7/8】获取演出日期")
    onestop = OneStopBookingFixed(client, config, logger)

    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info.get('encMemberCode', '')
    )

    if not play_dates:
        logger.error("❌ 获取演出日期失败")
        return False

    # 数据格式可能是：
    # {"playDate": ["20260212", "20260213", ...]}
    # 或
    # {"plays": [{"playDate": "...", "playTime": "..."}, ...]}

    play_dates_list = play_dates.get('playDate', [])
    plays = play_dates.get('plays', [])

    # 如果 playDate 是数组
    if isinstance(play_dates_list, list) and len(play_dates_list) > 0:
        logger.info(f"✅ 找到 {len(play_dates_list)} 个日期")

        # 显示可用日期
        logger.info("\n可用日期:")
        for i, date in enumerate(play_dates_list[:5], 1):
            logger.info(f"  {i}. {date}")

        # 选择第一个日期
        selected_date = play_dates_list[0]
        play_seq = "001"  # 默认场次

        logger.info(f"\n选择日期: {selected_date}")
        logger.info(f"场次: {play_seq}")
    elif isinstance(plays, list) and len(plays) > 0:
        logger.info(f"✅ 找到 {len(plays)} 个场次")

        # 显示可用日期
        logger.info("\n可用日期:")
        for i, play in enumerate(plays[:5], 1):
            play_date = play.get('playDate')
            play_time = play.get('playTime')
            logger.info(f"  {i}. {play_date} ({play_time})")

        # 选择第一个日期
        selected_date = plays[0].get('playDate')
        play_seq = plays[0].get('playSeq', '001')

        logger.info(f"\n选择日期: {selected_date}")
    else:
        logger.error("❌ 未找到可用日期")
        logger.error(f"响应数据: {json.dumps(play_dates, indent=2, ensure_ascii=False)}")
        return False

    # ===== 步骤 8: 模拟找到座位并执行付款流程 =====
    logger.info("\n【步骤 8/8】执行付款流程")
    logger.info("=" * 70)
    logger.info("⚠️ 注意：由于没有真实可售座位，使用 HAR 文件中的示例数据")
    logger.info("=" * 70)

    # 从 HAR 文件中的真实数据
    mock_seat = {
        'play_date': selected_date,
        'play_seq': play_seq,
        'seat_info_id': '25018223:25001698:001:2500',
        'seat_grade': '1',
        'seat_grade_name': 'R座',
        'floor': '1층',
        'row_no': 'D1구역 3열',
        'seat_no': '4',
        'price': 143000,
        'poll_count': 1,
        'elapsed_time': 0,
        'strategy': 'test'
    }

    logger.info(f"座位信息:")
    logger.info(f"  座位ID: {mock_seat['seat_info_id']}")
    logger.info(f"  价位: {mock_seat['seat_grade_name']} ({mock_seat['price']:,}韩元)")
    logger.info(f"  位置: {mock_seat['floor']} - {mock_seat['row_no']} - {mock_seat['seat_no']}")

    # 执行完整付款流程
    polling_selector = PollingSeatSelector(client, config, logger)

    payment_url = polling_selector.quick_purchase(
        selected_seat=mock_seat,
        session_id=session_id,
        member_info=member_info,
        use_full_flow=True
    )

    if payment_url:
        logger.info("\n" + "=" * 70)
        logger.info("✅ 完整付款流程测试成功！")
        logger.info("=" * 70)
        logger.info(f"\n支付链接:\n{payment_url}")
        logger.info("\n提示:")
        logger.info("  1. 打开上述链接完成支付")
        logger.info("  2. 如果提示座位不可用，可能是该座位已被售出")
        logger.info("  3. 可以重新运行程序获取其他座位")
        return True
    else:
        logger.error("\n❌ 付款流程失败")
        logger.error("可能的原因:")
        logger.error("  1. Session ID 过期")
        logger.error("  2. 座位已被售出")
        logger.error("  3. 网络问题")
        logger.error("  4. 接口参数错误")
        return False


if __name__ == "__main__":
    try:
        success = test_full_payment_flow()

        logger_msg = "\n" + "=" * 70
        if success:
            logger_msg += "\n✅ 测试成功！"
        else:
            logger_msg += "\nℹ️ 测试完成"
        logger_msg += "\n" + "=" * 70

        print(logger_msg)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
