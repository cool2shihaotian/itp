"""选座策略模块 - 多种选座策略实现"""
import json
import uuid
from typing import Dict, Any, Optional, List
import logging
from .client import ITPClient


class SeatSelectionStrategy:
    """选座策略基类"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger

    def select_seat(self, seats_info: List[Dict], user_config: Dict = None) -> Optional[Dict]:
        """
        选择座位（子类实现）

        Args:
            seats_info: 场次和座位信息列表
            user_config: 用户配置

        Returns:
            选中的座位信息
        """
        raise NotImplementedError("子类必须实现此方法")


class DefaultStrategy(SeatSelectionStrategy):
    """策略1: 默认策略 - 选择第一个场次和第一个价位"""

    def select_seat(self, seats_info: List[Dict], user_config: Dict = None) -> Optional[Dict]:
        """
        默认策略

        规则:
        1. 选择第一个场次
        2. 选择第一个价位（不论是否有余票）
        """
        if not seats_info or len(seats_info) == 0:
            self.logger.error("没有可用的场次信息")
            return None

        # 选择第一个场次
        selected_play = seats_info[0]
        play_seq = selected_play.get('playSeq')
        play_time = selected_play.get('playTime')

        # 获取座位列表
        available_seats = selected_play.get('seats', [])
        if len(available_seats) == 0:
            self.logger.error("场次没有可用的座位等级")
            return None

        # 选择第一个座位
        selected_seat = available_seats[0]

        result = {
            'play_date': selected_play.get('playDate'),
            'play_seq': play_seq,
            'play_time': play_time,
            'seat_grade': selected_seat.get('seatGrade'),
            'seat_grade_name': selected_seat.get('seatGradeName'),
            'price_grade': self._get_price_grade(selected_seat.get('seatGrade')),
            'price': selected_seat.get('salesPrice'),
            'remain_count': selected_seat.get('remainCount', 0),
            'strategy': 'default'
        }

        self.logger.info(f"使用默认策略:")
        self.logger.info(f"  场次: {play_seq} ({play_time})")
        self.logger.info(f"  价位: {selected_seat.get('seatGradeName')} ({selected_seat.get('salesPrice'):,}韩元)")
        self.logger.info(f"  余票: {selected_seat.get('remainCount', 0)}")

        return result

    def _get_price_grade(self, seat_grade: str) -> str:
        """根据 seatGrade 获取 priceGrade"""
        price_grade_map = {
            "1": "U1",
            "2": "U1",
            "3": "U2",
            "4": "U2",
        }
        return price_grade_map.get(seat_grade, "U1")


class AvailableFirstStrategy(SeatSelectionStrategy):
    """策略2: 优先有票 - 选择第一个有余票的座位"""

    def select_seat(self, seats_info: List[Dict], user_config: Dict = None) -> Optional[Dict]:
        """
        优先有票策略

        规则:
        1. 遍历所有场次
        2. 找到第一个有余票的场次
        3. 选择该场次中第一个有余票的价位

        如果所有场次都没有余票，返回第一个场次和价位（降级处理）
        """
        if not seats_info or len(seats_info) == 0:
            self.logger.error("没有可用的场次信息")
            return None

        self.logger.info("使用【优先有票】策略搜索...")

        # 遍历所有场次，找第一个有余票的
        for play in seats_info:
            play_seq = play.get('playSeq')
            play_time = play.get('playTime')
            play_date = play.get('playDate')

            seats = play.get('seats', [])
            for seat in seats:
                remain_count = seat.get('remainCount', 0)

                self.logger.debug(f"检查: 场次{play_seq} ({play_time}) - {seat.get('seatGradeName')} 余票:{remain_count}")

                if remain_count > 0:
                    # 找到第一个有余票的座位
                    result = {
                        'play_date': play_date,
                        'play_seq': play_seq,
                        'play_time': play_time,
                        'seat_grade': seat.get('seatGrade'),
                        'seat_grade_name': seat.get('seatGradeName'),
                        'price_grade': self._get_price_grade(seat.get('seatGrade')),
                        'price': seat.get('salesPrice'),
                        'remain_count': remain_count,
                        'strategy': 'available_first'
                    }

                    self.logger.info(f"✅ 找到有余票的座位!")
                    self.logger.info(f"  日期: {play_date}")
                    self.logger.info(f"  场次: {play_seq} ({play_time})")
                    self.logger.info(f"  价位: {seat.get('seatGradeName')} ({seat.get('salesPrice'):,}韩元)")
                    self.logger.info(f"  余票: {remain_count} 张")

                    return result

        # 如果都没有余票，降级到默认策略
        self.logger.warning("⚠️ 所有场次都没有余票，降级到默认策略（选择第一个场次和价位）")

        selected_play = seats_info[0]
        selected_seat = selected_play.get('seats', [{}])[0]

        result = {
            'play_date': selected_play.get('playDate'),
            'play_seq': selected_play.get('playSeq'),
            'play_time': selected_play.get('playTime'),
            'seat_grade': selected_seat.get('seatGrade'),
            'seat_grade_name': selected_seat.get('seatGradeName'),
            'price_grade': self._get_price_grade(selected_seat.get('seatGrade')),
            'price': selected_seat.get('salesPrice'),
            'remain_count': 0,
            'strategy': 'available_first_fallback'
        }

        self.logger.info(f"选择第一个场次（无余票）:")
        self.logger.info(f"  场次: {selected_play.get('playSeq')} ({selected_play.get('playTime')})")
        self.logger.info(f"  价位: {selected_seat.get('seatGradeName')} ({selected_seat.get('salesPrice'):,}韩元)")
        self.logger.info(f"  余票: 0（售罄）")

        return result

    def _get_price_grade(self, seat_grade: str) -> str:
        """根据 seatGrade 获取 priceGrade"""
        price_grade_map = {
            "1": "U1",
            "2": "U1",
            "3": "U2",
            "4": "U2",
        }
        return price_grade_map.get(seat_grade, "U1")


class PricePriorityStrategy(SeatSelectionStrategy):
    """策略3: 价格优先"""

    def select_seat(self, seats_info: List[Dict], user_config: Dict = None) -> Optional[Dict]:
        """
        价格优先策略

        Args:
            user_config: 必须包含 prefer 字段 ('cheapest' 或 'expensive')

        规则:
        1. 收集所有场次和价位
        2. 按价格排序
        3. 选择第一个有余票的
        """
        if not user_config or 'prefer' not in user_config:
            self.logger.error("价格优先策略需要配置 prefer 字段 (cheapest/expensive)")
            return None

        prefer = user_config['prefer']
        self.logger.info(f"使用【价格优先】策略: {prefer}")

        # 收集所有座位
        all_seats = []
        for play in seats_info:
            for seat in play.get('seats', []):
                all_seats.append({
                    'play': play,
                    'seat': seat,
                    'price': seat.get('salesPrice', 0)
                })

        # 按价格排序
        if prefer == 'cheapest':
            all_seats.sort(key=lambda x: x['price'])
            self.logger.info("排序: 从低到高")
        else:  # expensive
            all_seats.sort(key=lambda x: -x['price'])
            self.logger.info("排序: 从高到低")

        # 找第一个有余票的
        for item in all_seats:
            seat = item['seat']
            remain_count = seat.get('remainCount', 0)

            if remain_count > 0:
                play = item['play']
                result = {
                    'play_date': play.get('playDate'),
                    'play_seq': play.get('playSeq'),
                    'play_time': play.get('playTime'),
                    'seat_grade': seat.get('seatGrade'),
                    'seat_grade_name': seat.get('seatGradeName'),
                    'price_grade': self._get_price_grade(seat.get('seatGrade')),
                    'price': seat.get('salesPrice'),
                    'remain_count': remain_count,
                    'strategy': f'price_priority_{prefer}'
                }

                self.logger.info(f"✅ 找到符合价格的座位:")
                self.logger.info(f"  日期: {play.get('playDate')}")
                self.logger.info(f"  场次: {play.get('playSeq')} ({play.get('playTime')})")
                self.logger.info(f"  价位: {seat.get('seatGradeName')} ({seat.get('salesPrice'):,}韩元)")
                self.logger.info(f"  余票: {remain_count} 张")

                return result

        self.logger.warning("⚠️ 没有找到有余票的座位")
        return None

    def _get_price_grade(self, seat_grade: str) -> str:
        """根据 seatGrade 获取 priceGrade"""
        price_grade_map = {
            "1": "U1",
            "2": "U1",
            "3": "U2",
            "4": "U2",
        }
        return price_grade_map.get(seat_grade, "U1")


class CustomStrategy(SeatSelectionStrategy):
    """策略4: 用户自定义"""

    def select_seat(self, seats_info: List[Dict], user_config: Dict = None) -> Optional[Dict]:
        """
        自定义策略

        Args:
            user_config: 用户配置
                - preferred_date: 优先日期
                - preferred_time: 优先时间
                - preferred_grade: 优先座位等级
                - max_price: 最高价格
                - min_remain: 最少余票
        """
        if not user_config:
            self.logger.error("自定义策略需要提供用户配置")
            return None

        self.logger.info("使用【自定义】策略")
        self.logger.info(f"配置: {json.dumps(user_config, indent=2, ensure_ascii=False)}")

        filtered_plays = []

        # 过滤场次
        for play in seats_info:
            # 过滤日期
            if user_config.get('preferred_date'):
                if play.get('playDate') != user_config['preferred_date']:
                    continue

            # 过滤时间
            if user_config.get('preferred_time'):
                if play.get('playTime') != user_config['preferred_time']:
                    continue

            # 过滤座位
            for seat in play.get('seats', []):
                # 过滤座位等级
                if user_config.get('preferred_grade'):
                    if seat.get('seatGradeName') != user_config['preferred_grade']:
                        continue

                # 过滤价格
                if user_config.get('max_price'):
                    if seat.get('salesPrice', 0) > user_config['max_price']:
                        continue

                # 过滤余票
                if user_config.get('min_remain'):
                    if seat.get('remainCount', 0) < user_config['min_remain']:
                        continue

                # 符合所有条件
                filtered_plays.append({
                    'play': play,
                    'seat': seat
                })

        # 选择第一个符合条件的
        if filtered_plays:
            item = filtered_plays[0]
            play = item['play']
            seat = item['seat']

            result = {
                'play_date': play.get('playDate'),
                'play_seq': play.get('playSeq'),
                'play_time': play.get('playTime'),
                'seat_grade': seat.get('seatGrade'),
                'seat_grade_name': seat.get('seatGradeName'),
                'price_grade': self._get_price_grade(seat.get('seatGrade')),
                'price': seat.get('salesPrice'),
                'remain_count': seat.get('remainCount', 0),
                'strategy': 'custom'
            }

            self.logger.info(f"✅ 找到符合条件的座位:")
            self.logger.info(f"  日期: {play.get('playDate')}")
            self.logger.info(f"  场次: {play.get('playSeq')} ({play.get('playTime')})")
            self.logger.info(f"  价位: {seat.get('seatGradeName')} ({seat.get('salesPrice'):,}韩元)")
            self.logger.info(f"  余票: {seat.get('remainCount', 0)} 张")

            return result

        self.logger.warning("⚠️ 没有找到符合配置的座位")
        return None

    def _get_price_grade(self, seat_grade: str) -> str:
        """根据 seatGrade 获取 priceGrade"""
        price_grade_map = {
            "1": "U1",
            "2": "U1",
            "3": "U2",
            "4": "U2",
        }
        return price_grade_map.get(seat_grade, "U1")


class SeatSelector:
    """选座器 - 统一的选座接口"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger

        # 初始化策略
        self.strategies = {
            'default': DefaultStrategy(client, config, logger),
            'available_first': AvailableFirstStrategy(client, config, logger),
            'price_priority': PricePriorityStrategy(client, config, logger),
            'custom': CustomStrategy(client, config, logger)
        }

        # 默认策略
        self.default_strategy = config.get('seat_selection', {}).get('strategy', 'available_first')

    def select(self, seats_info: List[Dict], strategy: str = None, user_config: Dict = None) -> Optional[Dict]:
        """
        选择座位

        Args:
            seats_info: 场次和座位信息列表
            strategy: 策略名称 ('default', 'available_first', 'price_priority', 'custom')
            user_config: 用户配置（某些策略需要）

        Returns:
            选中的座位信息
        """
        if not seats_info or len(seats_info) == 0:
            self.logger.error("没有可用的场次信息")
            return None

        # 使用指定策略或默认策略
        strategy_name = strategy or self.default_strategy

        if strategy_name not in self.strategies:
            self.logger.error(f"未知的策略: {strategy_name}")
            self.logger.info(f"使用默认策略: {self.default_strategy}")
            strategy_name = self.default_strategy

        self.logger.info(f"使用策略: {strategy_name}")

        strategy_instance = self.strategies[strategy_name]
        result = strategy_instance.select_seat(seats_info, user_config)

        if result:
            self.logger.info("=" * 70)
            self.logger.info("选座结果:")
            self.logger.info("=" * 70)
            self.logger.info(f"日期: {result['play_date']}")
            self.logger.info(f"场次: {result['play_seq']} ({result['play_time']})")
            self.logger.info(f"价位: {result['seat_grade_name']} ({result['price']:,}韩元)")
            self.logger.info(f"余票: {result['remain_count']} 张")
            self.logger.info(f"策略: {result['strategy']}")
            self.logger.info("=" * 70)
        else:
            self.logger.error("选座失败")

        return result
