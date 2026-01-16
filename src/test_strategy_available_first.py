"""测试选座策略2：优先有票"""
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
from src.onestop_middleware_v3 import OneStopMiddlewareV3
from src.onestop_with_fix import OneStopBookingFixed
from src.seat_strategy import SeatSelector


def test_available_first_strategy():
    """测试优先有票策略"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("测试选座策略2：优先有票")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # ===== 快速登录和初始化 =====
    logger.info("\n【快速登录和初始化】")

    auth_manager = AuthManager(client, config, logger)
    auth_manager.login(config['account']['username'], config['account']['password'], skip_cloudflare=False)

    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    waiting = WaitingQueue(client, config, logger)
    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )
    waiting.line_up(secure_result['key'])

    # Rank 轮询
    rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
    params = {'bizCode': '88889', 'waitingId': waiting.waiting_id}

    response1 = client.get(rank_url, params=params)
    time.sleep(2)

    response2 = client.get(rank_url, params=params)

    if response2.status_code != 200:
        logger.error("❌ Rank 失败")
        return False

    rank_data = response2.json()
    session_id = rank_data['sessionId']
    one_stop_url = rank_data.get('oneStopUrl', '')

    logger.info(f"✅ SessionId: {session_id}")

    # Middleware
    logger.info("\n【Middleware】")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # ===== 获取演出信息 =====
    logger.info("\n【获取演出信息】")

    onestop = OneStopBookingFixed(client, config, logger)

    # 1. 获取演出日期
    play_dates = onestop.get_play_dates(
        goods_code='25018223',
        place_code='25001698',
        biz_code='88889',
        session_id=session_id,
        ent_member_code=member_info['encMemberCode']
    )

    if not play_dates:
        logger.error("❌ 获取演出日期失败")
        return False

    available_dates = play_dates.get('playDate', [])
    logger.info(f"✅ 可用日期: {available_dates}")

    # 2. 获取场次和座位信息（使用第一个日期）
    selected_date = available_dates[0]
    logger.info(f"\n获取日期 {selected_date} 的场次信息...")

    seats_info = onestop.get_play_seats(
        goods_code='25018223',
        place_code='25001698',
        play_date=selected_date,
        session_id=session_id,
        biz_code='88889'
    )

    if not seats_info or len(seats_info) == 0:
        logger.error("❌ 获取座位信息失败")
        return False

    # 显示所有场次和余票情况
    logger.info("\n" + "=" * 70)
    logger.info("所有场次和余票情况:")
    logger.info("=" * 70)

    for play in seats_info:
        play_seq = play.get('playSeq')
        play_time = play.get('playTime')
        logger.info(f"\n场次 {play_seq} - {play_time}")

        for seat in play.get('seats', []):
            seat_grade_name = seat.get('seatGradeName')
            price = seat.get('salesPrice')
            remain = seat.get('remainCount')

            # 用 emoji 标记余票状态
            if remain > 0:
                status = f"✅ 有票 ({remain}张)"
            else:
                status = f"❌ 售罄"

            logger.info(f"  {seat_grade_name}: {price:,}韩元 - {status}")

    # ===== 使用选座策略 =====
    logger.info("\n" + "=" * 70)
    logger.info("使用选座策略")
    logger.info("=" * 70)

    selector = SeatSelector(client, config, logger)

    # 策略2: 优先有票
    logger.info("\n【策略2: 优先有票】")
    selected = selector.select(
        seats_info=seats_info,
        strategy='available_first'
    )

    if not selected:
        logger.error("❌ 选座失败")
        return False

    # ===== 座位初始化 =====
    logger.info("\n【座位初始化】")

    import uuid
    seats_init_url = "https://tickets.interpark.com/onestop/api/seats/init/25018223"
    seats_init_params = {
        'goodsGenreType': '1',
        'placeCode': '25001698',
        'playSeq': selected['play_seq'],
        'seatGrade': '',
        'bizCode': '88889',
        'seatRenderType': 'D2003',
        'reserved': 'true',
        'entMemberCode': member_info['encMemberCode'],
        'sessionId': session_id,
        'kindOfGoods': '01003'
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://tickets.interpark.com/onestop/schedule',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': str(uuid.uuid4())[:16],
        'x-ticket-bff-language': 'ZH',
    }
    client.update_headers(headers)

    seats_init_response = client.get(seats_init_url, params=seats_init_params)

    if seats_init_response.status_code == 200:
        logger.info("✅ 座位初始化成功")
    else:
        logger.warning(f"⚠️ 座位初始化失败: {seats_init_response.status_code}")

    # ===== 生成付款链接 =====
    logger.info("\n【生成付款链接】")

    payment_url = f"https://tickets.interpark.com/onestop/payment?goodsCode=25018223&placeCode=25001698&playSeq={selected['play_seq']}&sessionId={session_id}"

    logger.info("\n" + "=" * 70)
    logger.info("🎯 选座完成!")
    logger.info("=" * 70)
    logger.info(f"\n选中的座位信息:")
    logger.info(f"  日期: {selected['play_date']}")
    logger.info(f"  场次: {selected['play_seq']} ({selected['play_time']})")
    logger.info(f"  价位: {selected['seat_grade_name']}")
    logger.info(f"  价格: {selected['price']:,} 韩元")
    logger.info(f"  余票: {selected['remain_count']} 张")
    logger.info(f"  策略: {selected['strategy']}")
    logger.info(f"\n付款链接:")
    logger.info(f"  {payment_url}")

    # 保存到文件
    output_file = "/Users/shihaotian/Desktop/edison/itp/payment_link_available_first.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("ITP 购票系统 - 付款链接（策略2：优先有票）\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"演出: Sing Again 4 全国巡回演唱会 – 首尔\n")
        f.write(f"日期: {selected['play_date']}\n")
        f.write(f"场次: {selected['play_seq']} ({selected['play_time']})\n")
        f.write(f"价位: {selected['seat_grade_name']}\n")
        f.write(f"价格: {selected['price']:,} 韩元\n")
        f.write(f"余票: {selected['remain_count']} 张\n")
        f.write(f"选座策略: {selected['strategy']}\n\n")
        f.write(f"Session ID: {session_id}\n\n")
        f.write("付款链接:\n")
        f.write("-" * 70 + "\n")
        f.write(f"{payment_url}\n")
        f.write("-" * 70 + "\n\n")
        f.write("说明:\n")
        f.write("此链接使用【优先有票】策略生成，会选择第一个有余票的场次和价位。\n")

    logger.info(f"\n✅ 付款链接已保存到: {output_file}")

    return payment_url


if __name__ == "__main__":
    try:
        payment_url = test_available_first_strategy()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if payment_url:
            logger.info("✅ 测试成功！已使用【优先有票】策略生成付款链接！")
        else:
            logger.info("ℹ️ 测试完成")
        logger.info("=" * 70)

        sys.exit(0 if payment_url else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
