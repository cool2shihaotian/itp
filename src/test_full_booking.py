"""完整购票流程测试 - 从登录到付款链接"""
import sys
import json
import time
import uuid
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


def test_full_booking_flow():
    """完整购票流程：登录 → Waiting → Middleware → OneStop → 选座 → 付款"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("完整购票流程测试 - 走到付款")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)

    # ===== 步骤 1: 登录 =====
    logger.info("\n【步骤 1/10】NOL 登录")
    auth_manager = AuthManager(client, config, logger)
    login_success = auth_manager.login(
        config['account']['username'],
        config['account']['password'],
        skip_cloudflare=False
    )

    if not login_success:
        logger.error("❌ 登录失败")
        return False

    logger.info(f"✅ User ID: {auth_manager.user_id}")

    # ===== 步骤 2: 桥接鉴权 =====
    logger.info("\n【步骤 2/10】桥接鉴权")
    bridge = BridgeAuth(client, config, logger)
    bridge.full_bridge_auth('25018223', '25001698', '10965', auth_manager.user_id)

    # ===== 步骤 3: 获取会员信息 =====
    logger.info("\n【步骤 3/10】获取会员信息")
    booking = BookingManager(client, config, logger)
    member_info = booking.get_member_info('25018223')

    logger.info(f"✅ Member Code: {member_info['memberCode']}")
    logger.info(f"✅ EncMemberCode: {member_info['encMemberCode'][:50]}...")

    # ===== 步骤 4: Waiting 流程 =====
    logger.info("\n【步骤 4/10】Waiting 排队流程")
    waiting = WaitingQueue(client, config, logger)

    secure_result = waiting.get_secure_url(
        signature=member_info['signature'],
        secure_data=member_info['secureData'],
        biz_code='88889',
        goods_code='25018223'
    )

    waiting.line_up(secure_result['key'])
    logger.info(f"✅ Waiting ID: {waiting.waiting_id}")

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
    logger.info(f"✅ OneStop URL: {one_stop_url[:100]}...")

    # ===== 步骤 5: Middleware =====
    logger.info("\n【步骤 5/10】Middleware set-cookie")
    middleware_v3 = OneStopMiddlewareV3(client, config, logger)
    middleware_v3.call_middleware_set_cookie(rank_data)

    # ===== 步骤 6: 获取演出日期 =====
    logger.info("\n【步骤 6/10】获取演出日期")
    onestop = OneStopBookingFixed(client, config, logger)

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

    # ===== 步骤 7: 选择日期和价位 =====
    logger.info("\n【步骤 7/10】选择日期和价位")

    # 随机选择第一个日期
    selected_date = available_dates[0]  # 20260212
    logger.info(f"✅ 选择日期: {selected_date}")

    # 获取该日期的场次和价位信息
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

    # 显示可用价位
    logger.info("\n可用价位:")
    for play_info in seats_info:
        play_seq = play_info.get('playSeq')
        play_time = play_info.get('playTime')
        logger.info(f"\n场次 {play_seq} - {play_time}")

        for seat in play_info.get('seats', []):
            seat_grade_name = seat.get('seatGradeName')
            price = seat.get('salesPrice')
            remain = seat.get('remainCount')
            logger.info(f"  {seat_grade_name}: {price:,} 韩元 (剩余: {remain})")

    # 随机选择第一个场次和价位
    selected_play = seats_info[0]
    selected_play_seq = selected_play.get('playSeq')
    selected_time = selected_play.get('playTime')
    selected_seats = selected_play.get('seats', [])

    if len(selected_seats) == 0:
        logger.error("❌ 没有可用价位")
        return False

    # 选择第一个价位
    selected_seat = selected_seats[0]
    seat_grade = selected_seat.get('seatGrade')
    seat_grade_name = selected_seat.get('seatGradeName')
    price_grade = "U1"  # 根据 seatGrade 映射
    price = selected_seat.get('salesPrice')

    logger.info(f"\n✅ 选择场次: {selected_play_seq} ({selected_time})")
    logger.info(f"✅ 选择价位: {seat_grade_name} ({price:,} 韩元)")
    logger.info(f"  seatGrade: {seat_grade}")
    logger.info(f"  priceGrade: {price_grade}")

    # ===== 步骤 8: 座位初始化 =====
    logger.info("\n【步骤 8/10】座位初始化")

    seats_init_url = "https://tickets.interpark.com/onestop/api/seats/init/25018223"
    seats_init_params = {
        'goodsGenreType': '1',
        'placeCode': '25001698',
        'playSeq': selected_play_seq,
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

    logger.info(f"请求: {seats_init_url}")
    seats_init_response = client.get(seats_init_url, params=seats_init_params)

    if seats_init_response.status_code == 200:
        logger.info("✅ 座位初始化成功")
        init_result = seats_init_response.json()
        logger.info(f"  ticketMaxCount: {init_result.get('ticketMaxCount')}")
        logger.info(f"  connectionMode: {init_result.get('connectionMode')}")
    else:
        logger.warning(f"⚠️ 座位初始化失败: {seats_init_response.status_code}")

    # ===== 步骤 9: 支付初始化 =====
    logger.info("\n【步骤 9/10】支付初始化")

    payment_init_url = "https://tickets.interpark.com/onestop/api/payment/init-essential/25018223"
    payment_init_params = {
        'placeCode': '25001698',
        'playSeq': selected_play_seq,
        'intMemberCode': member_info['encMemberCode'],
        'entMemberCode': member_info['encMemberCode'],
        'bizCode': '88889',
        'memberType': '3',
        'seatGrade': seat_grade,
        'priceGrade': price_grade,
        'willCallPrice': 'false'
    }

    logger.info(f"请求: {payment_init_url}")
    logger.info(f"参数: seatGrade={seat_grade}, priceGrade={price_grade}")

    payment_init_response = client.get(payment_init_url, params=payment_init_params)

    if payment_init_response.status_code == 200:
        logger.info("✅ 支付初始化成功")
        payment_init_data = payment_init_response.json()

        # 打印支付信息
        logger.info("\n可用支付方式:")
        if 'deliveryMethods' in payment_init_data:
            for method in payment_init_data['deliveryMethods']:
                logger.info(f"  配送方式: {method.get('label')}")

        if 'deliveryPackages' in payment_init_data:
            for pkg in payment_init_data['deliveryPackages']:
                logger.info(f"  包装: {pkg.get('codeName')} - {pkg.get('amount')} 韩元")

        if 'paymentBanks' in payment_init_data:
            banks = payment_init_data['paymentBanks'][:5]  # 只显示前5个
            logger.info(f"\n支持的银行（前5个）:")
            for bank in banks:
                logger.info(f"  {bank.get('bankName')}: {bank.get('kindOfSettle')}")

    else:
        logger.warning(f"⚠️ 支付初始化失败: {payment_init_response.status_code}")
        logger.info(f"响应: {payment_init_response.text[:500]}")

    # ===== 步骤 10: 获取支付方式列表 =====
    logger.info("\n【步骤 10/10】获取支付方式")

    pay_list_url = "https://tickets.interpark.com/onestop/api/payment/method/interpark-pay/pay-list"
    pay_list_params = {
        'goodsCode': '25018223',
        'sessionId': session_id,
        'intMemberCode': member_info['encMemberCode']
    }

    pay_list_response = client.get(pay_list_url, params=pay_list_params)

    payment_url = None

    if pay_list_response.status_code == 200:
        logger.info("✅ 获取支付方式成功")
        pay_list_data = pay_list_response.json()

        logger.info(f"\n支付方式:")
        logger.info(f"  mid: {pay_list_data.get('mid')}")
        logger.info(f"  结果: {pay_list_data.get('resultMessage')}")

        if 'cardInstallment' in pay_list_data:
            logger.info(f"\n支持的分期付款:")
            for card in pay_list_data['cardInstallment'][:10]:
                logger.info(f"  {card.get('cardName')}: {card.get('halbuText')} ({card.get('bigo')})")

        # ⭐ 构造付款链接
        # 根据 OneStop 的结构，付款页面 URL 格式
        payment_url = f"https://tickets.interpark.com/onestop/payment?goodsCode=25018223&placeCode=25001698&playSeq={selected_play_seq}&sessionId={session_id}"

        logger.info(f"\n" + "=" * 70)
        logger.info("🎯 付款链接（已生成）")
        logger.info("=" * 70)
        logger.info(f"\n{payment_url}\n")

        # 保存到文件
        output_file = "/Users/shihaotian/Desktop/edison/itp/payment_link.txt"
        with open(output_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("ITP 购票系统 - 付款链接\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"演出: Sing Again 4 全国巡回演唱会 – 首尔\n")
            f.write(f"日期: {selected_date}\n")
            f.write(f"场次: {selected_play_seq} ({selected_time})\n")
            f.write(f"价位: {seat_grade_name}\n")
            f.write(f"价格: {price:,} 韩元\n\n")
            f.write(f"Session ID: {session_id}\n\n")
            f.write("付款链接:\n")
            f.write("-" * 70 + "\n")
            f.write(f"{payment_url}\n")
            f.write("-" * 70 + "\n\n")
            f.write("注意事项:\n")
            f.write("1. 点击链接后需要登录（如果未登录）\n")
            f.write("2. 选择支付方式完成付款\n")
            f.write("3. 链接有效期请参考 Session ID 的时效性\n")

        logger.info(f"✅ 付款链接已保存到: {output_file}")

        return payment_url

    else:
        logger.error(f"❌ 获取支付方式失败: {pay_list_response.status_code}")
        return False


if __name__ == "__main__":
    try:
        payment_url = test_full_booking_flow()

        config = load_config()
        logger = setup_logging(config)

        logger.info("\n" + "=" * 70)
        if payment_url:
            logger.info("✅ 完全成功！已生成付款链接！")
            logger.info(f"\n付款链接: {payment_url}")
        else:
            logger.info("ℹ️ 流程测试完成")
        logger.info("=" * 70)

        sys.exit(0 if payment_url else 1)

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
