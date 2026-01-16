"""Interpark 完整付款流程实现

基于 HAR 文件分析实现的完整选座和付款流程：
1. preselect - 预选座位（WebSocket 锁定）
2. select - 确认选座
3. payment/ready - 准备付款（生成 cartID）
4. eximbay/request - 请求支付（获取 fgkey）
5. Eximbay 支付网关 - 完成支付
"""

import json
import uuid
import time
from typing import Dict, Any, Optional
import logging


class InterparkPaymentFlow:
    """Interpark 完整付款流程"""

    def __init__(self, client, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化付款流程

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: 日志记录器
        """
        self.client = client
        self.config = config
        self.logger = logger

        # 固定参数
        self.goods_code = '25018223'
        self.place_code = '25001698'
        self.biz_code = '88889'
        self.mcht_member_no = 'T38962139'  # 商户号

    def _generate_trace_id(self) -> str:
        """生成 trace ID"""
        return str(uuid.uuid4())

    def preselect_seat(self, selected_seat: Dict, session_id: str,
                      block_key: str = None) -> Optional[Dict]:
        """
        步骤 1: 预选座位（通过 WebSocket 锁定座位）

        Args:
            selected_seat: 选中的座位信息（从 seatMeta 获取）
            session_id: 会话 ID
            block_key: 区域代码（可选，如果座位信息中没有）

        Returns:
            预选结果，或 None
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【步骤 1/5】预选座位 (preselect)")
            self.logger.info("=" * 70)

            url = "https://tickets.interpark.com/onestop/api/seats/preselect"

            # 从 seatInfoId 中提取信息
            # 格式: "25018223:25001698:001:2500"
            # 分解: goodsCode:placeCode:playSeq:seatCode
            seat_info_id = selected_seat.get('seat_info_id', '')
            parts = seat_info_id.split(':')

            if len(parts) < 4:
                self.logger.error(f"❌ seatInfoId 格式错误: {seat_info_id}")
                return None

            play_seq_from_id = parts[2]  # 从 seatInfoId 提取 playSeq

            # 如果没有提供 blockKey，尝试构造
            if not block_key:
                # blockKey 格式: "001:401" (playSeq:blockNo)
                # 需要获取 blockNo，这里先简化处理
                block_key = f"{play_seq_from_id}:401"  # 默认使用 401

            data = {
                "blockKey": block_key,
                "goodsCode": self.goods_code,
                "placeCode": self.place_code,
                "playSeq": selected_seat.get('play_seq', play_seq_from_id),
                "seatInfoId": seat_info_id,
                "sessionId": session_id
            }

            self.logger.info(f"请求参数: {json.dumps(data, indent=2, ensure_ascii=False)}")

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/seat',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': self._generate_trace_id(),
                'x-requested-with': 'XMLHttpRequest'
            }
            self.client.update_headers(headers)

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 预选座位成功")
                self.logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 预选座位失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"预选座位异常: {e}", exc_info=True)
            return None

    def select_seat(self, selected_seat: Dict, session_id: str) -> Optional[Dict]:
        """
        步骤 2: 确认选座

        Args:
            selected_seat: 选中的座位信息
            session_id: 会话 ID

        Returns:
            选座结果，或 None
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【步骤 2/5】确认选座 (select)")
            self.logger.info("=" * 70)

            url = "https://tickets.interpark.com/onestop/api/seats/select"

            seat_info_id = selected_seat.get('seat_info_id', '')
            play_seq = selected_seat.get('play_seq', '')
            seat_grade = selected_seat.get('seat_grade', '1')

            data = {
                "goodsCode": self.goods_code,
                "placeCode": self.place_code,
                "playSeq": play_seq,
                "seatType": "DEFAULT",
                "seats": [
                    {
                        "seatGrade": seat_grade,
                        "seatInfoId": seat_info_id
                    }
                ],
                "seatCount": 1,
                "sessionId": session_id
            }

            self.logger.info(f"请求参数: {json.dumps(data, indent=2, ensure_ascii=False)}")

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/seat',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': self._generate_trace_id(),
                'x-requested-with': 'XMLHttpRequest'
            }
            self.client.update_headers(headers)

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 确认选座成功")
                self.logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.error(f"❌ 确认选座失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"确认选座异常: {e}", exc_info=True)
            return None

    def ready_payment(self, selected_seat: Dict, session_id: str,
                     member_info: Dict, delivery_info: Dict = None) -> Optional[Dict]:
        """
        步骤 3: 准备付款（生成购物车 ID）

        Args:
            selected_seat: 选中的座位信息
            session_id: 会话 ID
            member_info: 会员信息
            delivery_info: 配送信息（可选）

        Returns:
            付款准备结果（包含 cartID 和 cartIDSeq），或 None
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【步骤 3/5】准备付款 (payment/ready)")
            self.logger.info("=" * 70)

            url = f"https://tickets.interpark.com/onestop/api/payment/ready/{self.goods_code}"

            # 计算价格
            sales_price = int(selected_seat.get('price', 143000))
            commission_fee = 8000  # 固定手续费
            total_fee = sales_price + commission_fee

            # 默认配送信息
            if not delivery_info:
                delivery_info = {
                    "deliveryMethod": "WILL_CALL",
                    "deliveryAmount": 0,
                    "deliveryPackage": "",
                    "deliveryPackageAmount": 0,
                    "isDelivery": False,
                    "name": member_info.get('name', 'USER'),
                    "birthDate": member_info.get('birthDate', '9602120'),
                    "email": member_info.get('email', 'user@example.com'),
                    "userPhone": member_info.get('phone', '821012345678'),
                    "recipient": "",
                    "addressPhone": "",
                    "subAddressPhone": "",
                    "address": "undefined | undefined | undefined | undefined",
                    "subAddress": "",
                    "zipCode": "",
                    "bookPassword": ""
                }

            seat_grade = selected_seat.get('seat_grade', '1')
            seat_grade_name = selected_seat.get('seat_grade_name', 'R座')

            # 映射 seatGrade 到 priceGrade
            price_grade_map = {
                "1": "U1",  # R座
                "2": "U1",  # VIP
                "3": "U2",  # S座
                "4": "U2",  # A座
            }
            price_grade = price_grade_map.get(seat_grade, "U1")

            data = {
                "autoSeat": False,
                "bizCode": self.biz_code,
                "entMemberCode": member_info.get('encMemberCode', ''),
                "sessionId": session_id,
                "goodsCode": self.goods_code,
                "placeCode": self.place_code,
                "playSeq": selected_seat.get('play_seq', ''),
                "playDate": selected_seat.get('play_date', ''),
                "ticketCount": 1,
                "totalFee": total_fee,
                "totalCommissionFee": commission_fee,
                "paymentInfo": {
                    "settleCount": 1,
                    "kindOfPayment": "22003",  # 信用卡
                    "firstSettleAmount": total_fee,
                    "useVoucher": False,
                    "voucherCodes": [""],
                    "voucherSalesPrices": ["0"],
                    "pgType": "VN005",  # Eximbay
                    "cardNo": "",
                    "cardPassword": "",
                    "cardSsn": "",
                    "validInfo": "",
                    "cardKind": "12001"
                },
                "deliveryInfo": delivery_info,
                "discountInfo": {
                    "cardDiscountNumber": "",
                    "cardDiscountType": "",
                    "otherDiscountType": "",
                    "topingDiscountType": ""
                },
                "priceInfo": [
                    {
                        "dblDiscountOrNot": "N",
                        "discountCode": "00000",
                        "groupId": "12133",
                        "pgCode": "PG002",
                        "priceGrade": price_grade,
                        "priceGradeName": "一般",
                        "salesPrice": str(float(sales_price)),
                        "seatGrade": seat_grade,
                        "seatGradeName": seat_grade_name,
                        "ticketAmount": str(float(sales_price))
                    }
                ],
                "seatInfo": [
                    {
                        "blockNo": "401",  # 从 seatInfoId 提取或默认
                        "floor": selected_seat.get('floor', '1층'),
                        "rowNo": selected_seat.get('row_no', ''),
                        "seatGrade": seat_grade,
                        "seatNo": selected_seat.get('seat_no', ''),
                        "seatInfoId": selected_seat.get('seat_info_id', '')
                    }
                ],
                "couponInfo": {
                    "discountAmount": 0
                },
                "marketingAgree": False,
                "waitingInfo": {},
                "partnerPointInfo": {}
            }

            self.logger.info(f"请求参数 (关键信息):")
            self.logger.info(f"  座位ID: {selected_seat.get('seat_info_id')}")
            self.logger.info(f"  票价: {sales_price:,} 韩元")
            self.logger.info(f"  手续费: {commission_fee:,} 韩元")
            self.logger.info(f"  总价: {total_fee:,} 韩元")

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/price',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': self._generate_trace_id(),
                'x-requested-with': 'XMLHttpRequest',
                'x-ticket-bff-language': 'ZH'  # 添加语言 header
            }
            self.client.update_headers(headers)

            # 打印完整请求体（用于调试）
            self.logger.debug(f"完整请求体: {json.dumps(data, indent=2, ensure_ascii=False)}")

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 准备付款成功")
                self.logger.info(f"cartID: {result.get('cartID')}")
                self.logger.info(f"cartIDSeq: {result.get('cartIDSeq')}")
                return result
            else:
                self.logger.error(f"❌ 准备付款失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"准备付款异常: {e}", exc_info=True)
            return None

    def request_eximbay_payment(self, payment_ready_result: Dict,
                               member_info: Dict, total_fee: int) -> Optional[Dict]:
        """
        步骤 4: 请求 Eximbay 支付（获取 fgkey）

        Args:
            payment_ready_result: payment/ready 的返回结果
            member_info: 会员信息
            total_fee: 总金额

        Returns:
            Eximbay 支付请求结果（包含 fgkey），或 None
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【步骤 4/5】请求 Eximbay 支付 (eximbay/request)")
            self.logger.info("=" * 70)

            url = "https://tickets.interpark.com/onestop/api/payment/method/eximbay/request"

            # 生成 correlationId
            cart_id = payment_ready_result.get('cartID', '')
            cart_id_seq = payment_ready_result.get('cartIDSeq', '')
            correlation_id = f"{cart_id}{cart_id_seq}"

            data = {
                "mchtMemberNo": self.mcht_member_no,
                "correlationId": correlation_id,
                "payMethod": "CARD_ONESTOP",
                "currency": "KRW",
                "amount": str(total_fee),
                "lang": "EN",
                "callFromApp": "N",
                "callFromScheme": "",
                "displayType": "P",
                "autoclose": "Y",
                "ostype": "P",
                "catId": "ONESTOP",
                "buyerName": member_info.get('name', 'USER'),
                "buyerEmail": member_info.get('email', 'user@example.com'),
                "returnUrl": f"https://tickets.interpark.com/onestop/payment/callback?type=EXIMBAY&eximbayPaymentId={correlation_id}",
                "productName": "Sing Again 4 全国巡回演唱会 – 首尔",
                "prod": [
                    {
                        "name": "Sing Again 4 全国巡回演唱会 – 首尔",
                        "quantity": "1",
                        "price": str(total_fee),
                        "link": "https://tickets.interpark.com"
                    }
                ]
            }

            self.logger.info(f"请求参数 (关键信息):")
            self.logger.info(f"  correlationId: {correlation_id}")
            self.logger.info(f"  金额: {total_fee:,} 韩元")

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/payment',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-requested-with': 'XMLHttpRequest'
            }
            self.client.update_headers(headers)

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                fgkey = result.get('fgkey', '')
                self.logger.info("✅ 请求 Eximbay 支付成功")
                self.logger.info(f"fgkey: {fgkey[:20]}...{fgkey[-20:]}")
                return result
            else:
                self.logger.error(f"❌ 请求 Eximbay 支付失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"请求 Eximbay 支付异常: {e}", exc_info=True)
            return None

    def get_payment_url(self, eximbay_result: Dict) -> str:
        """
        步骤 5: 生成支付链接

        Args:
            eximbay_result: eximbay/request 的返回结果

        Returns:
            支付链接
        """
        try:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("【步骤 5/5】生成支付链接")
            self.logger.info("=" * 70)

            fgkey = eximbay_result.get('fgkey', '')
            payment = eximbay_result.get('payment', {})
            order_id = payment.get('order_id', '')

            # Eximbay 支付网关 URL
            # 注意：实际支付需要跳转到 Eximbay 的支付页面
            # 这里生成的是支付页面的 URL
            payment_url = f"https://tickets.interpark.com/onestop/payment/eximbay?fgkey={fgkey}"

            self.logger.info("✅ 支付链接生成成功")
            self.logger.info(f"订单ID: {order_id}")
            self.logger.info(f"支付链接: {payment_url}")

            return payment_url

        except Exception as e:
            self.logger.error(f"生成支付链接异常: {e}", exc_info=True)
            return ""

    def execute_full_flow(self, selected_seat: Dict, session_id: str,
                         member_info: Dict, delivery_info: Dict = None) -> Optional[str]:
        """
        执行完整的付款流程

        Args:
            selected_seat: 选中的座位信息
            session_id: 会话 ID
            member_info: 会员信息
            delivery_info: 配送信息（可选）

        Returns:
            支付链接，或 None（失败）
        """
        try:
            self.logger.info("\n" + "🎯" * 35)
            self.logger.info("开始执行完整的付款流程")
            self.logger.info("🎯" * 35)

            # 步骤 1: 预选座位
            preselect_result = self.preselect_seat(selected_seat, session_id)
            if not preselect_result:
                self.logger.error("❌ 预选座位失败，流程终止")
                return None

            # 步骤 2: 确认选座
            select_result = self.select_seat(selected_seat, session_id)
            if not select_result:
                self.logger.error("❌ 确认选座失败，流程终止")
                return None

            # 步骤 3: 准备付款
            payment_ready_result = self.ready_payment(
                selected_seat, session_id, member_info, delivery_info
            )
            if not payment_ready_result:
                self.logger.error("❌ 准备付款失败，流程终止")
                return None

            # 计算总金额
            sales_price = int(selected_seat.get('price', 143000))
            commission_fee = 8000
            total_fee = sales_price + commission_fee

            # 步骤 4: 请求 Eximbay 支付
            eximbay_result = self.request_eximbay_payment(
                payment_ready_result, member_info, total_fee
            )
            if not eximbay_result:
                self.logger.error("❌ 请求 Eximbay 支付失败，流程终止")
                return None

            # 步骤 5: 生成支付链接
            payment_url = self.get_payment_url(eximbay_result)

            self.logger.info("\n" + "✅" * 35)
            self.logger.info("完整付款流程执行成功！")
            self.logger.info("✅" * 35)

            return payment_url

        except Exception as e:
            self.logger.error(f"执行付款流程异常: {e}", exc_info=True)
            return None
