"""座位选择模块"""
from typing import Dict, Any, List, Optional
import logging
from .client import ITPClient


class SeatSelector:
    """座位选择器"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化座位选择器

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: logger 对象
        """
        self.client = client
        self.config = config
        self.logger = logger
        self.seat_priority = config.get('seat_priority', [])

    def select_seats(self, available_seats: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        根据配置的优先级选择座位

        Args:
            available_seats: 可用座位列表

        Returns:
            选中的座位列表，如果没有合适的返回 None
        """
        self.logger.info("开始选择座位...")

        # 按优先级遍历配置
        for priority in self.seat_priority:
            target_zone = priority.get('zone')
            target_price = priority.get('price')
            quantity = priority.get('quantity', 1)

            # 筛选符合条件的座位
            matched_seats = self._filter_seats(
                available_seats,
                target_zone,
                target_price,
                quantity
            )

            if matched_seats:
                self.logger.info(
                    f"找到匹配座位: 区域={target_zone}, "
                    f"价格={target_price}, 数量={quantity}"
                )
                return matched_seats[:quantity]

        self.logger.warning("未找到匹配的座位")
        return None

    def _filter_seats(
        self,
        seats: List[Dict[str, Any]],
        zone: str,
        price: str,
        quantity: int
    ) -> List[Dict[str, Any]]:
        """
        筛选座位

        Args:
            seats: 座位列表
            zone: 目标区域
            price: 目标价格
            quantity: 需要数量

        Returns:
            筛选后的座位列表
        """
        filtered = []
        for seat in seats:
            # TODO: 根据实际座位数据结构调整筛选逻辑
            seat_zone = seat.get('zone', '')
            seat_price = seat.get('price', '')

            # 如果 price 为空，只匹配区域
            if not price:
                if seat_zone == zone:
                    filtered.append(seat)
            else:
                if seat_zone == zone and seat_price == price:
                    filtered.append(seat)

            if len(filtered) >= quantity:
                break

        return filtered

    def get_seat_map(self, schedule_code: str) -> Dict[str, Any]:
        """
        获取座位图

        Args:
            schedule_code: 场次 code

        Returns:
            座位图数据
        """
        self.logger.info(f"获取座位图: {schedule_code}")
        # TODO: 根据抓包数据实现
        raise NotImplementedError("等待抓包数据后实现")
