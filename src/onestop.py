"""OneStop 选座系统模块"""
from typing import Dict, Any, Optional, List
import logging
import json
from .client import ITPClient
from .onestop_middleware import OneStopMiddleware


class OneStopBooking:
    """OneStop 选座和预订系统"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.play_seq: Optional[str] = None
        self.middleware = OneStopMiddleware(client, config, logger)

    def set_middleware_cookie(self, goods_code: str, biz_code: str = "88889",
                             session_id: str = None, one_stop_url: str = None) -> Optional[Dict]:
        """
        设置 OneStop 中间件 cookie（纯 requests 实现）

        基于时间同步和 sessionId 的完整实现

        Args:
            goods_code: 商品代码
            biz_code: 业务代码
            session_id: 从 waiting rank 获取的 sessionId
            one_stop_url: 从 waiting rank 获取的 oneStopUrl

        Returns:
            设置结果
        """
        try:
            self.logger.info(f"[OneStop 1/5] 设置中间件 cookie (纯 requests)")

            # 如果提供了 session_id 和 one_stop_url，使用新的 middleware 实现
            if session_id:
                self.logger.info("使用基于时间的 middleware 实现")

                # 提取 key
                one_stop_key = None
                if one_stop_url and 'key=' in one_stop_url:
                    one_stop_key = one_stop_url.split('key=')[-1].split('&')[0]

                # 调用 middleware
                success = self.middleware.call_middleware_set_cookie(
                    session_id=session_id,
                    one_stop_url=one_stop_url,
                    one_stop_key=one_stop_key
                )

                if success:
                    return {'status': 'success', 'message': 'Middleware set successfully'}
                else:
                    # 即使失败也继续
                    return {'status': 'partial', 'message': 'Middleware called, continuing...'}
            else:
                # 旧的简单实现（向后兼容）
                self.logger.warning("⚠️ 未提供 session_id，使用简单实现（可能失败）")

                url = "https://tickets.interpark.com/onestop/middleware/set-cookie"

                headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json',
                    'Origin': 'https://tickets.interpark.com',
                    'Referer': 'https://tickets.interpark.com/',
                }
                self.client.update_headers(headers)

                data = {
                    'bizCode': biz_code,
                    'goodsCode': goods_code,
                }

                response = self.client.post(url, json=data)

                if response.status_code in [200, 201]:
                    result = response.json()
                    self.logger.info("✅ 中间件 cookie 设置成功")
                    return result
                else:
                    self.logger.warning(f"⚠️ 中间件 cookie 设置失败: {response.status_code}")
                    self.logger.info("继续尝试后续步骤...")
                    return {'status': 'skipped', 'message': 'Middleware failed, continuing...'}

        except Exception as e:
            self.logger.error(f"设置中间件 cookie 异常: {e}", exc_info=True)
            # 即使异常也继续
            return {'status': 'error', 'message': str(e)}

    def get_play_dates(self, goods_code: str, place_code: str, biz_code: str = "88889",
                      session_id: str = None, ent_member_code: str = None) -> Optional[Dict]:
        """
        获取演出日期列表

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码
            session_id: 会话 ID（从 Waiting 获取）
            ent_member_code: 加密的会员代码（从 member-info 获取）

        Returns:
            演出日期列表
        """
        try:
            self.logger.info(f"[OneStop 2/4] 获取演出日期列表")

            # 正确的 URL 格式: /onestop/api/play/play-date/{goodsCode}?placeCode={placeCode}&bizCode={bizCode}&sessionId={sessionId}&entMemberCode={entMemberCode}
            url = f"https://tickets.interpark.com/onestop/api/play/play-date/{goods_code}"

            # 构建查询参数
            params = {
                'placeCode': place_code,
                'bizCode': biz_code,
            }

            if session_id:
                params['sessionId'] = session_id

            if ent_member_code:
                params['entMemberCode'] = ent_member_code

            # ⚠️ 关键修复：设置正确的 Referer（基于 HAR 文件）
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://tickets.interpark.com/onestop/schedule',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }
            self.client.update_headers(headers)

            self.logger.debug(f"请求 URL: {url}")
            self.logger.debug(f"查询参数: {params}")

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出日期列表获取成功")
                self.logger.debug(f"日期数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 演出日期列表获取失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出日期列表异常: {e}", exc_info=True)
            return None

    def check_session(self, goods_code: str, play_seq: str = None,
                      biz_code: str = "88889") -> Optional[Dict]:
        """
        检查会话状态

        Args:
            goods_code: 商品代码
            play_seq: 演出序列号
            biz_code: 业务代码

        Returns:
            会话状态信息
        """
        try:
            self.logger.info(f"[OneStop 3/4] 检查会话状态")

            url = "https://tickets.interpark.com/onestop/api/session-check"

            # 设置 headers
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/',
            }
            self.client.update_headers(headers)

            # 构建请求体
            data = {
                'bizCode': biz_code,
                'goodsCode': goods_code,
            }

            if play_seq:
                data['playSeq'] = play_seq
                self.play_seq = play_seq

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 会话状态检查成功")
                self.logger.debug(f"会话数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 会话状态检查失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"检查会话状态异常: {e}", exc_info=True)
            return None

    def get_play_seats(self, goods_code: str, play_seq: str,
                       biz_code: str = "88889") -> Optional[Dict]:
        """
        获取演出座位信息

        Args:
            goods_code: 商品代码
            play_seq: 演出序列号
            biz_code: 业务代码

        Returns:
            座位信息（包含座位图）
        """
        try:
            self.logger.info(f"[OneStop 4/4] 获取演出座位信息")

            url = f"https://tickets.interpark.com/onestop/api/play-seq/play/{goods_code}/{play_seq}"

            # 构建查询参数
            params = {
                'bizCode': biz_code,
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出座位信息获取成功")
                self.logger.debug(f"座位数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 演出座位信息获取失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出座位信息异常: {e}", exc_info=True)
            return None

    def select_seats(self, goods_code: str, seats: List[Dict[str, Any]],
                     play_seq: str = None, biz_code: str = "88889") -> Optional[Dict]:
        """
        选择座位（预留座位）

        Args:
            goods_code: 商品代码
            seats: 座位列表 [{'seatNo': 'xxx', 'gradeCode': 'xxx', ...}]
            play_seq: 演出序列号
            biz_code: 业务代码

        Returns:
            预留结果
        """
        try:
            self.logger.info(f"[OneStop 5/5] 选择并预留座位")

            url = "https://tickets.interpark.com/onestop/api/seat/reserve"

            # 设置 headers
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/',
            }
            self.client.update_headers(headers)

            # 构建请求体
            data = {
                'bizCode': biz_code,
                'goodsCode': goods_code,
                'seats': seats,
            }

            if play_seq:
                data['playSeq'] = play_seq
            elif self.play_seq:
                data['playSeq'] = self.play_seq

            self.logger.info(f"选择座位: {json.dumps(seats, indent=2, ensure_ascii=False)}")

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 座位预留成功")
                return result
            else:
                self.logger.error(f"❌ 座位预留失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"预留座位异常: {e}", exc_info=True)
            return None

    def parse_seat_map(self, seat_data: Dict) -> List[Dict[str, Any]]:
        """
        解析座位图数据，提取可用座位

        Args:
            seat_data: get_play_seats 返回的座位数据

        Returns:
            可用座位列表
        """
        try:
            self.logger.info("解析座位图数据")

            available_seats = []

            # 根据实际数据结构解析座位信息
            # 这里需要根据实际 API 响应调整
            if 'prices' in seat_data:
                for price_info in seat_data['prices']:
                    # 提取价格等级信息
                    grade_code = price_info.get('gradeCode')
                    grade_name = price_info.get('gradeName')

                    self.logger.info(f"价格等级: {grade_name} ({grade_code})")

                    # 提取该等级下的可用座位
                    if 'seats' in price_info:
                        for seat in price_info['seats']:
                            if seat.get('available', False):
                                available_seats.append({
                                    'seatNo': seat.get('seatNo'),
                                    'gradeCode': grade_code,
                                    'gradeName': grade_name,
                                    'price': seat.get('price'),
                                    'section': seat.get('section'),
                                    'row': seat.get('row'),
                                    'col': seat.get('col'),
                                })

            self.logger.info(f"✅ 找到 {len(available_seats)} 个可用座位")
            return available_seats

        except Exception as e:
            self.logger.error(f"解析座位图异常: {e}", exc_info=True)
            return []

    def auto_select_seats(self, available_seats: List[Dict], preferences: Dict = None) -> List[Dict]:
        """
        根据偏好自动选择座位

        Args:
            available_seats: 可用座位列表
            preferences: 座位偏好配置

        Returns:
            选中的座位列表
        """
        try:
            self.logger.info("根据偏好自动选择座位")

            # 从配置获取偏好
            if not preferences:
                preferences = self.config.get('seat_preferences', {})

            ticket_count = preferences.get('ticket_count', 1)
            priority_sections = preferences.get('priority_sections', [])
            max_price = preferences.get('max_price')

            selected_seats = []
            seats_by_section = {}

            # 按区域分组座位
            for seat in available_seats:
                section = seat.get('section', 'default')
                if section not in seats_by_section:
                    seats_by_section[section] = []
                seats_by_section[section].append(seat)

            # 按优先级选择区域
            for section in priority_sections:
                if section in seats_by_section:
                    section_seats = seats_by_section[section]

                    # 按价格筛选
                    if max_price:
                        section_seats = [s for s in section_seats if s.get('price', float('inf')) <= max_price]

                    # 选择座位
                    needed = ticket_count - len(selected_seats)
                    if needed > 0 and len(section_seats) >= needed:
                        selected_seats.extend(section_seats[:needed])

                    if len(selected_seats) >= ticket_count:
                        break

            # 如果优先区域不够，从其他区域补充
            if len(selected_seats) < ticket_count:
                for section, seats in seats_by_section.items():
                    if section not in priority_sections:
                        needed = ticket_count - len(selected_seats)
                        if len(seats) >= needed:
                            selected_seats.extend(seats[:needed])
                            break

            if len(selected_seats) >= ticket_count:
                self.logger.info(f"✅ 成功选择 {len(selected_seats)} 个座位")
                for seat in selected_seats:
                    self.logger.info(f"  - {seat.get('gradeName')}: {seat.get('section')} {seat.get('seatNo')}")
            else:
                self.logger.warning(f"⚠️ 只找到 {len(selected_seats)}/{ticket_count} 个座位")

            return selected_seats

        except Exception as e:
            self.logger.error(f"自动选择座位异常: {e}", exc_info=True)
            return []

    def full_booking_flow(self, goods_code: str, play_seq: str = None,
                         biz_code: str = "88889") -> bool:
        """
        完整的 OneStop 预订流程

        Args:
            goods_code: 商品代码
            play_seq: 演出序列号（如果为 None，尝试从第一个日期获取）
            biz_code: 业务代码

        Returns:
            是否成功
        """
        self.logger.info("=" * 70)
        self.logger.info("🎯 开始 OneStop 预订流程")
        self.logger.info("=" * 70)

        # 步骤 1: 设置中间件 cookie
        middleware_result = self.set_middleware_cookie(goods_code, biz_code)
        if not middleware_result:
            self.logger.warning("⚠️ 中间件 cookie 设置失败，但继续尝试")

        # 步骤 2: 获取演出日期
        dates_result = self.get_play_dates(goods_code, biz_code)
        if not dates_result:
            self.logger.error("无法获取演出日期")
            return False

        # 如果没有提供 play_seq，使用第一个
        if not play_seq:
            # 根据实际数据结构提取第一个 play_seq
            if 'playDates' in dates_result and len(dates_result['playDates']) > 0:
                play_seq = dates_result['playDates'][0].get('playSeq')
                self.logger.info(f"自动选择第一个场次: {play_seq}")
            else:
                self.logger.error("无法获取演出序列号")
                return False

        # 步骤 3: 检查会话
        session_result = self.check_session(goods_code, play_seq, biz_code)
        if not session_result:
            self.logger.warning("⚠️ 会话检查失败，但继续尝试")

        # 步骤 4: 获取座位信息
        seats_result = self.get_play_seats(goods_code, play_seq, biz_code)
        if not seats_result:
            self.logger.error("无法获取座位信息")
            return False

        # 步骤 5: 解析并选择座位
        available_seats = self.parse_seat_map(seats_result)
        if not available_seats:
            self.logger.error("没有可用座位")
            return False

        selected_seats = self.auto_select_seats(available_seats)
        if not selected_seats:
            self.logger.error("自动选择座位失败")
            return False

        # 步骤 6: 预留座位
        reserve_result = self.select_seats(goods_code, selected_seats, play_seq, biz_code)
        if not reserve_result:
            self.logger.error("座位预留失败")
            return False

        self.logger.info("=" * 70)
        self.logger.info("✅ OneStop 预订流程完成！")
        self.logger.info("=" * 70)

        return True
