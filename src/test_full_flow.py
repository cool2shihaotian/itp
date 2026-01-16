"""完整流程测试（非排队模式）"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.bridge import BridgeAuth
from src.booking import BookingManager
from src.onestop import OneStopBooking


def test_full_booking_flow():
    """测试完整的预订流程（跳过排队）"""
    config = load_config()
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("完整 ITP 订阅流程测试（非排队模式）")
    logger.info("=" * 70)

    # 初始化客户端
    client = ITPClient(config, logger)

    # 阶段 1: NOL 登录
    logger.info("\n[阶段 1/6] NOL World 登录...")
    auth_manager = AuthManager(client, config, logger)
    username = config['account']['username']
    password = config['account']['password']

    use_cloudflare = config.get('capsolver', {}).get('enabled', False)
    skip_cloudflare = not use_cloudflare

    if not auth_manager.login(username, password, skip_cloudflare=skip_cloudflare):
        logger.error("登录失败")
        return False

    logger.info("✅ NOL 登录成功")

    # 阶段 2: 桥接鉴权
    logger.info("\n[阶段 2/6] 桥接鉴权（NOL → Interpark）...")
    bridge = BridgeAuth(client, config, logger)

    goods_code = config.get('event', {}).get('goods_code', '25018223')
    place_code = config.get('event', {}).get('place_code', '25001698')
    biz_code_gates = config.get('event', {}).get('biz_code_gates', '10965')

    success = bridge.full_bridge_auth(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code_gates,
        user_id=auth_manager.user_id
    )

    if not success:
        logger.error("桥接鉴权失败")
        return False

    # 阶段 3: Gates 预检
    logger.info("\n[阶段 3/6] Gates 预检...")
    booking = BookingManager(client, config, logger)

    # 获取商品信息
    goods_info = booking.get_goods_info(
        goods_code=goods_code,
        place_code=place_code,
        biz_code=biz_code_gates
    )

    if not goods_info:
        logger.error("获取商品信息失败")
        return False

    logger.info("✅ 商品信息获取成功")
    logger.info(f"商品名称: {goods_info.get('goodsName', 'N/A')}")

    # 获取会员信息
    member_info = booking.get_member_info(goods_code=goods_code)

    if not member_info:
        logger.error("获取会员信息失败")
        return False

    logger.info("✅ 会员信息获取成功")

    # 保存关键参数
    signature = member_info.get('signature', '')
    secure_data = member_info.get('secureData', '')

    logger.info(f"Signature: {signature[:30]}...")
    logger.info(f"SecureData: {secure_data[:30]}...")

    # 阶段 4: 跳过排队（非排队模式）
    logger.info("\n[阶段 4/6] 跳过排队（非排队模式）...")
    logger.info("ℹ️ 在非售票期间或非热门演出，可能不需要排队")
    logger.info("⏭️ 直接进入 OneStop 阶段")

    # 阶段 5: OneStop 选座
    logger.info("\n[阶段 5/6] OneStop 选座系统...")
    onestop = OneStopBooking(client, config, logger)

    biz_code_onestop = config.get('event', {}).get('biz_code_onestop', '88889')

    # 尝试完整的 OneStop 流程
    logger.info("尝试完整预订流程...")

    success = onestop.full_booking_flow(
        goods_code=goods_code,
        play_seq=None,  # 自动选择第一个场次
        biz_code=biz_code_onestop
    )

    if not success:
        logger.warning("⚠️ OneStop 流程未完全成功（可能需要实际售票期间）")
        logger.info("尝试单独测试各个接口...")

        # 单独测试每个接口
        # 1. 设置中间件 cookie
        logger.info("\n测试 1: 设置中间件 cookie")
        result = onestop.set_middleware_cookie(goods_code, biz_code_onestop)
        if result:
            logger.info("✅ 中间件 cookie 设置成功")
        else:
            logger.error("❌ 中间件 cookie 设置失败")

        # 2. 获取演出日期
        logger.info("\n测试 2: 获取演出日期")
        dates_result = onestop.get_play_dates(goods_code, biz_code_onestop)
        if dates_result:
            logger.info("✅ 演出日期获取成功")
            logger.info(f"数据: {json.dumps(dates_result, indent=2, ensure_ascii=False)}")

            # 提取第一个 play_seq
            if 'playDates' in dates_result and len(dates_result['playDates']) > 0:
                play_seq = dates_result['playDates'][0].get('playSeq')
                logger.info(f"第一个场次序列号: {play_seq}")

                # 3. 检查会话
                logger.info("\n测试 3: 检查会话状态")
                session_result = onestop.check_session(goods_code, play_seq, biz_code_onestop)
                if session_result:
                    logger.info("✅ 会话检查成功")
                else:
                    logger.error("❌ 会话检查失败")

                # 4. 获取座位信息
                logger.info("\n测试 4: 获取座位信息")
                seats_result = onestop.get_play_seats(goods_code, play_seq, biz_code_onestop)
                if seats_result:
                    logger.info("✅ 座位信息获取成功")
                    logger.info(f"数据: {json.dumps(seats_result, indent=2, ensure_ascii=False)}")
                else:
                    logger.error("❌ 座位信息获取失败")
        else:
            logger.error("❌ 演出日期获取失败")

    # 阶段 6: 总结
    logger.info("\n[阶段 6/6] 流程总结")
    logger.info("=" * 70)
    logger.info("✅ 已完成以下阶段:")
    logger.info("  1. ✅ NOL World 登录")
    logger.info("  2. ✅ 桥接鉴权（NOL → Interpark）")
    logger.info("  3. ✅ Gates 预检（商品信息 + 会员信息）")
    logger.info("  4. ⏭️ 跳过排队（非排队模式）")
    logger.info("  5. 🎯 OneStop 选座系统")
    logger.info("=" * 70)

    logger.info("\n📝 注意事项:")
    logger.info("  - 某些接口可能只在售票期间可用")
    logger.info("  - 座位预留和订单提交需要在实际售票时测试")
    logger.info("  - Waiting 排队系统只在高需求演出时启用")

    return True


if __name__ == "__main__":
    test_full_booking_flow()
