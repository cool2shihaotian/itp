"""轮询选座策略 - 持续监控余票，有票立即购买"""
import json
import time
import uuid
from typing import Dict, Any, Optional, List
import logging
from client import ITPClient
from payment_flow import InterparkPaymentFlow


class PollingSeatSelector:
    """轮询选座器 - 持续监控余票，有票后立即购买"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger

    def get_block_keys(self, play_seq: str, session_id: str, user_id: str = None) -> Optional[List[str]]:
        """
        获取所有区域代码（blockKeys）

        Args:
            play_seq: 场次编号
            session_id: 会话 ID
            user_id: 用户 ID（必需！）

        Returns:
            区域代码列表，或 None
        """
        if not user_id:
            self.logger.warning("⚠️ user_id 未设置，block-data API 可能会失败")

        try:
            url = "https://tickets.interpark.com/onestop/api/seats/block-data"
            params = {
                'goodsCode': '25018223',
                'placeCode': '25001698',
                'playSeq': play_seq
            }

            # 设置必要的 cookies
            if user_id:
                self.client.session.cookies.set('userId', user_id)
            self.client.session.cookies.set('ent_onestop_channel', 'TRIPLE_KOREA')

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://tickets.interpark.com/onestop/seat',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': str(uuid.uuid4())[:16],
                'x-requested-with': 'XMLHttpRequest',
                'x-ticket-bff-language': 'ZH'
            }
            self.client.update_headers(headers)

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                blocks = response.json()
                block_keys = [block['blockKey'] for block in blocks]
                self.logger.debug(f"获取到 {len(block_keys)} 个区域代码")
                return block_keys
            else:
                self.logger.warning(f"获取区域代码失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取区域代码异常: {e}")
            return None

    def get_real_seat_availability(self, play_seq: str, block_keys: List[str],
                                   session_id: str, max_price: int = None,
                                   user_id: str = None) -> Optional[Dict]:
        """
        通过 seatMeta 接口获取真实座位状态

        Args:
            play_seq: 场次编号
            block_keys: 区域代码列表
            session_id: 会话 ID
            max_price: 最高价格限制
            user_id: 用户 ID（必需！）

        Returns:
            第一个可售座位，或 None
        """
        try:
            url = "https://tickets.interpark.com/onestop/api/seatMeta"

            # 设置必要的 cookies
            if user_id:
                self.client.session.cookies.set('userId', user_id)
            self.client.session.cookies.set('ent_onestop_channel', 'TRIPLE_KOREA')

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://tickets.interpark.com/onestop/seat',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': str(uuid.uuid4())[:16],
                'x-requested-with': 'XMLHttpRequest',
                'x-ticket-bff-language': 'ZH'
            }
            self.client.update_headers(headers)

            # 逐个查询每个区域（避免批量请求的 500 错误）
            for block_key in block_keys:
                # 构建参数
                params = {
                    'goodsCode': '25018223',
                    'placeCode': '25001698',
                    'playSeq': play_seq,
                    'blockKeys': block_key  # 单个区域
                }

                response = self.client.get(url, params=params)

                if response.status_code == 200:
                    try:
                        seat_data = response.json()

                        # 解析座位数据
                        if isinstance(seat_data, list) and len(seat_data) > 0:
                            for block in seat_data:
                                seats = block.get('seats', [])
                                if not seats:
                                    continue

                                for seat in seats:
                                    # 检查是否可售
                                    if not seat.get('isExposable', False):
                                        continue

                                    # 检查价格
                                    price = seat.get('salesPrice', 0)
                                    if max_price and price > max_price:
                                        continue

                                    # 找到可售座位！
                                    self.logger.info(f"✅ 找到可售座位: {seat.get('seatInfoId')}")
                                    return {
                                        'play_seq': play_seq,
                                        'seat_info_id': seat.get('seatInfoId'),
                                        'seat_grade': seat.get('seatGrade'),
                                        'seat_grade_name': seat.get('seatGradeName'),
                                        'floor': seat.get('floor'),
                                        'row_no': seat.get('rowNo'),
                                        'seat_no': seat.get('seatNo'),
                                        'price': price
                                    }
                    except Exception as e:
                        self.logger.warning(f"解析座位数据异常: {e}")
                        continue
                elif response.status_code == 500:
                    # 某些区域可能返回 500，继续查询其他区域
                    self.logger.debug(f"区域 {block_key} 返回 500，跳过")
                    continue
                else:
                    self.logger.warning(f"区域 {block_key} 请求失败: {response.status_code}")

            return None

        except Exception as e:
            self.logger.error(f"获取真实座位状态异常: {e}")
            return None

    def poll_and_select(self, onestop, play_date: str, session_id: str,
                       member_info: Dict, poll_interval: int = 3,
                       timeout: int = 300, max_price: int = None,
                       user_id: str = None) -> Optional[Dict]:
        """
        轮询选座：持续监控真实座位状态（基于 seatMeta 接口）

        Args:
            onestop: OneStopBookingFixed 实例
            play_date: 目标日期
            session_id: 会话 ID
            member_info: 会员信息
            poll_interval: 轮询间隔（秒），默认 3 秒
            timeout: 超时时间（秒），默认 300 秒（5分钟）
            max_price: 最高价格限制（可选）
            user_id: 用户 ID（必需！）

        Returns:
            选中的座位信息，或 None（超时）
        """
        self.logger.info("=" * 70)
        self.logger.info("【轮询选座模式】基于真实座位状态（seatMeta）持续监控")
        self.logger.info("=" * 70)
        self.logger.info(f"目标日期: {play_date}")
        self.logger.info(f"轮询间隔: {poll_interval} 秒")
        self.logger.info(f"超时时间: {timeout} 秒 ({timeout//60} 分钟)")
        if max_price:
            self.logger.info(f"最高价格: {max_price:,} 韩元")

        if not user_id:
            self.logger.warning("⚠️ user_id 未设置，API 调用可能失败！")

        # 首先获取场次列表
        play_dates = onestop.get_play_dates(
            goods_code='25018223',
            place_code='25001698',
            biz_code='88889',
            session_id=session_id,
            ent_member_code=member_info['encMemberCode']
        )

        if not play_dates:
            self.logger.error("❌ 获取演出日期失败")
            return None

        # 获取目标日期的场次
        plays = play_dates.get('plays', [])
        play_dates_list = play_dates.get('playDate', [])

        # 处理两种响应格式
        if plays and len(plays) > 0:
            # 完整格式：包含场次信息
            target_plays = [p for p in plays if p.get('playDate') == play_date]
            if not target_plays:
                self.logger.error(f"❌ 找不到日期 {play_date} 的场次")
                return None
            play_seq = target_plays[0].get('playSeq', '001')
            play_time = target_plays[0].get('playTime', '')
            self.logger.info(f"目标场次: {play_seq} ({play_time})")
        elif play_dates_list and len(play_dates_list) > 0:
            # 简化格式：只有日期数组，使用默认 playSeq
            if play_date not in play_dates_list:
                self.logger.error(f"❌ 找不到日期 {play_date}，可用日期: {play_dates_list}")
                return None
            # 从日期提取 playSeq（例如：20260212 -> 001）
            # 使用索引来确定场次编号
            date_index = play_dates_list.index(play_date)
            play_seq = f"{date_index + 1:03d}"  # 001, 002, 003...
            play_time = ""
            self.logger.info(f"目标日期: {play_date}")
            self.logger.info(f"使用场次编号: {play_seq} (基于日期索引)")
        else:
            self.logger.error("❌ 未找到演出日期信息")
            return None

        # 获取所有区域代码（只需获取一次）
        block_keys = self.get_block_keys(play_seq, session_id, user_id=user_id)
        if not block_keys:
            self.logger.error("❌ 获取区域代码失败")
            return None

        self.logger.info(f"✅ 获取到 {len(block_keys)} 个区域代码")

        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < timeout:
            poll_count += 1
            elapsed = time.time() - start_time

            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"第 {poll_count} 次轮询 (已用时: {int(elapsed)}秒)")
            self.logger.info(f"{'='*70}")

            # 检查真实座位状态
            available_seat = self.get_real_seat_availability(
                play_seq=play_seq,
                block_keys=block_keys,
                session_id=session_id,
                max_price=max_price,
                user_id=user_id
            )

            if available_seat:
                # 找到有票的座位！
                self.logger.info("\n" + "🎉" * 35)
                self.logger.info("✅ 找到真实可售座位！尝试锁定...")
                self.logger.info("🎉" * 35)

                # 尝试立即预选座位，验证是否真的可用
                self.logger.info("\n⚠️ 注意：从发现到预选有时间差，座位可能已被占用")
                self.logger.info("如果预选失败，系统会自动继续轮询下一个座位\n")

                result = {
                    'play_date': play_date,
                    'play_seq': available_seat['play_seq'],
                    'seat_info_id': available_seat['seat_info_id'],
                    'seat_grade': available_seat['seat_grade'],
                    'seat_grade_name': available_seat['seat_grade_name'],
                    'floor': available_seat['floor'],
                    'row_no': available_seat['row_no'],
                    'seat_no': available_seat['seat_no'],
                    'price': available_seat['price'],
                    'poll_count': poll_count,
                    'elapsed_time': int(elapsed),
                    'strategy': 'polling_seatmeta'
                }

                self.logger.info("选中的座位信息:")
                self.logger.info(f"  场次: {result['play_seq']}")
                self.logger.info(f"  座位ID: {result['seat_info_id']}")
                self.logger.info(f"  价位: {result['seat_grade_name']} ({result['price']:,}韩元)")
                self.logger.info(f"  位置: {result['floor']} - {result['row_no']} - {result['seat_no']}")
                self.logger.info(f"  轮询次数: {poll_count}")
                self.logger.info(f"  用时: {int(elapsed)} 秒")

                # ⚠️ 注意：这里只返回座位信息，不进行预选
                # 预选应该在付款流程中进行，失败时继续轮询
                self.logger.info("\n💡 座位信息已返回，将在付款流程中尝试预选")
                self.logger.info("💡 如果预选失败（座位被占用），请增加轮询时间继续尝试\n")

                return result
            else:
                # 没有余票，继续轮询
                remaining_time = timeout - int(elapsed)
                self.logger.info(f"ℹ️ 暂无符合条件的余票，{remaining_time} 秒后继续轮询...")

                if remaining_time > 0:
                    time.sleep(min(poll_interval, remaining_time))
                else:
                    self.logger.warning("⏰ 轮询超时")
                    break

        # 轮询超时
        self.logger.error("\n" + "=" * 70)
        self.logger.error(f"❌ 轮询超时（{timeout}秒），未找到有余票的座位")
        self.logger.error("=" * 70)

        return None

    def _show_seat_status(self, seats_info: List[Dict], max_price: int = None):
        """显示当前余票情况"""
        self.logger.info(f"\n当前余票情况:")
        self.logger.info("-" * 70)

        for play in seats_info:
            play_seq = play.get('playSeq')
            play_time = play.get('playTime')

            for seat in play.get('seats', []):
                seat_grade_name = seat.get('seatGradeName')
                price = seat.get('salesPrice')
                remain = seat.get('remainCount', 0)

                # 价格过滤
                if max_price and price > max_price:
                    continue

                # 状态标记
                if remain > 0:
                    status = f"✅ 有票 ({remain}张)"
                    self.logger.info(f"  [{play_seq}] {seat_grade_name}: {price:,}韩元 - {status}")
                else:
                    status = f"❌ 售罄"
                    self.logger.debug(f"  [{play_seq}] {seat_grade_name}: {price:,}韩元 - {status}")

    def _find_available_seat(self, seats_info: List[Dict], max_price: int = None) -> Optional[Dict]:
        """
        查找第一个有余票的座位

        Args:
            seats_info: 场次和座位信息
            max_price: 最高价格限制

        Returns:
            可用的座位信息，或 None
        """
        for play in seats_info:
            play_seq = play.get('playSeq')
            play_time = play.get('playTime')
            play_date = play.get('playDate')

            for seat in play.get('seats', []):
                remain_count = seat.get('remainCount', 0)
                price = seat.get('salesPrice', 0)

                # 检查余票
                if remain_count > 0:
                    # 检查价格
                    if max_price and price > max_price:
                        continue

                    # 找到了！
                    return {
                        'play_date': play_date,
                        'play_seq': play_seq,
                        'play_time': play_time,
                        'seat_grade': seat.get('seatGrade'),
                        'seat_grade_name': seat.get('seatGradeName'),
                        'price': price,
                        'remain_count': remain_count
                    }

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

    def reserve_seat(self, selected_seat: Dict, session_id: str) -> Optional[Dict]:
        """
        锁定座位：调用 reserve 接口预留座位

        Args:
            selected_seat: 选中的座位信息
            session_id: 会话 ID

        Returns:
            预留结果，或 None
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【锁定座位】调用 reserve 接口")
            self.logger.info("=" * 70)

            url = "https://tickets.interpark.com/onestop/api/seat/reserve"

            # 构建 seats 参数
            # 注意：seatInfoId 格式为 "25018223:25001698:001:333"
            # 可能需要解析，或者直接使用某些字段
            seats = [{
                'seatNo': selected_seat.get('seat_no'),           # 座位号
                'gradeCode': selected_seat.get('seat_grade'),      # 等级代码
            }]

            data = {
                'bizCode': '88889',
                'goodsCode': '25018223',
                'playSeq': selected_seat['play_seq'],
                'seats': seats,
            }

            self.logger.info(f"请求参数: {json.dumps(data, indent=2, ensure_ascii=False)}")

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/seat',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-requested-with': 'XMLHttpRequest'
            }
            self.client.update_headers(headers)

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 座位锁定成功！")
                self.logger.info(f"预留结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 座位锁定失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"锁定座位异常: {e}", exc_info=True)
            return None

    def quick_purchase(self, selected_seat: Dict, session_id: str, member_info: Dict,
                      use_full_flow: bool = True) -> Optional[str]:
        """
        快速购买：找到真实可售座位后，立即执行完整付款流程

        Args:
            selected_seat: 选中的座位信息
            session_id: 会话 ID
            member_info: 会员信息
            use_full_flow: 是否使用完整付款流程（默认 True）

        Returns:
            支付链接，或 None（失败）
        """
        self.logger.info("\n" + "=" * 70)
        self.logger.info("【快速购买】立即执行完整付款流程")
        self.logger.info("=" * 70)

        if use_full_flow:
            # 使用完整的付款流程（基于 HAR 文件分析）
            payment_flow = InterparkPaymentFlow(self.client, self.config, self.logger)

            payment_url = payment_flow.execute_full_flow(
                selected_seat=selected_seat,
                session_id=session_id,
                member_info=member_info
            )

            if payment_url:
                # 保存到文件
                output_file = f"/Users/shihaotian/Desktop/edison/itp/payment_link_full_{int(time.time())}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 70 + "\n")
                    f.write("ITP 购票系统 - 完整付款流程\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"演出: Sing Again 4 全国巡回演唱会 – 首尔\n")
                    f.write(f"日期: {selected_seat['play_date']}\n")
                    f.write(f"场次: {selected_seat['play_seq']}\n")
                    f.write(f"座位ID: {selected_seat['seat_info_id']}\n")
                    f.write(f"价位: {selected_seat['seat_grade_name']}\n")
                    f.write(f"位置: {selected_seat['floor']} - {selected_seat['row_no']} - {selected_seat['seat_no']}\n")
                    f.write(f"价格: {selected_seat['price']:,} 韩元\n\n")
                    f.write(f"轮询统计:\n")
                    f.write(f"  轮询次数: {selected_seat['poll_count']}\n")
                    f.write(f"  用时: {selected_seat['elapsed_time']} 秒\n")
                    f.write(f"  检测方式: seatMeta 真实座位状态\n\n")
                    f.write(f"Session ID: {session_id}\n\n")
                    f.write("付款流程:\n")
                    f.write("  ✅ 1. 预选座位 (preselect)\n")
                    f.write("  ✅ 2. 确认选座 (select)\n")
                    f.write("  ✅ 3. 准备付款 (payment/ready)\n")
                    f.write("  ✅ 4. 请求支付 (eximbay/request)\n")
                    f.write("  ✅ 5. 生成支付链接\n\n")
                    f.write("付款链接:\n")
                    f.write("-" * 70 + "\n")
                    f.write(f"{payment_url}\n")
                    f.write("-" * 70 + "\n\n")
                    f.write("⚠️ 重要提示:\n")
                    f.write("1. ✅ 座位已通过完整流程锁定\n")
                    f.write("2. ✅ 支付网关已准备就绪\n")
                    f.write("3. 请尽快完成支付（座位已预留）\n")

                self.logger.info(f"\n✅ 付款链接已保存到: {output_file}")
            else:
                self.logger.error("❌ 完整付款流程失败")

            return payment_url
        else:
            # 简化版本：直接生成付款链接（不锁定座位）
            payment_url = f"https://tickets.interpark.com/onestop/payment?goodsCode=25018223&placeCode=25001698&playSeq={selected_seat['play_seq']}&sessionId={session_id}"

            self.logger.info("\n" + "=" * 70)
            self.logger.info("🎯 付款链接已生成！（简化版本，座位未锁定）")
            self.logger.info("=" * 70)
            self.logger.info(f"\n{payment_url}")

            return payment_url
