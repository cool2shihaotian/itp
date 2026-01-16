"""主程序入口"""
import sys
import time
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.auth import AuthManager
from src.ticket import TicketManager
from src.seat import SeatSelector
from src.payment import PaymentManager


def main():
    """主函数"""
    # 加载配置
    config = load_config()

    # 设置日志
    logger = setup_logging(config)
    logger.info("=" * 50)
    logger.info("ITP 自动购票程序启动")
    logger.info("=" * 50)

    try:
        # 初始化客户端
        client = ITPClient(config, logger)

        # 登录
        auth_manager = AuthManager(client, config, logger)
        username = config['account']['username']
        password = config['account']['password']

        if not auth_manager.login(username, password):
            logger.error("登录失败")
            return

        logger.info("登录成功")

        # 初始化管理器
        ticket_manager = TicketManager(client, config, logger)
        seat_selector = SeatSelector(client, config, logger)
        payment_manager = PaymentManager(client, config, logger)

        # 获取活动信息
        event_code = config['event']['event_code']
        schedule_code = config['event']['schedule_code']

        event_info = ticket_manager.get_event_info(event_code)
        logger.info(f"活动信息: {event_info}")

        # 等待发售时间或排队
        # TODO: 根据实际情况调整逻辑

        # 排队
        ticket_manager.wait_in_queue(event_info.get('queue_url'))

        # 获取可用座位
        available_seats = ticket_manager.get_available_seats(schedule_code)
        logger.info(f"可用座位数量: {len(available_seats)}")

        # 选择座位
        selected_seats = seat_selector.select_seats(available_seats)
        if not selected_seats:
            logger.error("未找到合适的座位")
            return

        logger.info(f"选择座位: {selected_seats}")

        # 预留座位
        reservation = ticket_manager.reserve_seats(selected_seats)
        reservation_id = reservation.get('reservation_id')

        # 提交订单
        order = payment_manager.submit_order(reservation_id, selected_seats)
        order_id = order.get('order_id')

        # 支付
        payment_result = payment_manager.process_payment(order_id)

        if payment_result.get('success'):
            logger.info("=" * 50)
            logger.info("购票成功！")
            logger.info(f"订单号: {order_id}")
            logger.info("=" * 50)
        else:
            logger.error("支付失败")

    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
    finally:
        logger.info("程序结束")


if __name__ == "__main__":
    main()
