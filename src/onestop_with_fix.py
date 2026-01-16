"""OneStop API - 添加关键 headers"""
import json
import uuid
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class OneStopBookingFixed:
    """OneStop 选座系统 - 修复版本（添加关键 headers）"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.play_seq: Optional[str] = None

    def get_play_dates(self, goods_code: str, place_code: str, biz_code: str = "88889",
                      session_id: str = None, ent_member_code: str = None) -> Optional[Dict]:
        """
        获取演出日期列表（修复版本 - 添加关键 headers）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码
            session_id: 会话 ID
            ent_member_code: 加密的会员代码

        Returns:
            演出日期列表
        """
        try:
            self.logger.info(f"[OneStop] 获取演出日期列表（修复版本）")

            # 正确的 URL 格式
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

            # ⚠️ 关键修复：添加缺失的 headers
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/schedule',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                # ⭐ 关键 headers（从 HAR 中发现）
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id or '',
                'x-onestop-trace-id': str(uuid.uuid4())[:16],  # 生成 trace ID
                'x-ticket-bff-language': 'ZH',
            }

            self.client.update_headers(headers)

            self.logger.debug(f"请求 URL: {url}")
            self.logger.debug(f"查询参数: {params}")
            self.logger.info(f"x-onestop-session: {session_id}")
            self.logger.info(f"x-onestop-trace-id: {headers['x-onestop-trace-id']}")

            response = self.client.get(url, params=params)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出日期列表获取成功！")
                self.logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            else:
                self.logger.warning(f"⚠️ 演出日期列表获取失败: {response.status_code}")
                self.logger.info(f"响应: {response.text[:500]}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出日期列表异常: {e}", exc_info=True)
            return None

    def check_session(self, goods_code: str, session_id: str, play_seq: str = None,
                      biz_code: str = "88889") -> Optional[Dict]:
        """
        检查会话状态

        Args:
            goods_code: 商品代码
            session_id: 会话 ID
            play_seq: 演出序列号
            biz_code: 业务代码

        Returns:
            会话状态信息
        """
        try:
            self.logger.info(f"[OneStop] 检查会话状态")

            # 注意：session-check 的 URL 格式
            url = f"https://tickets.interpark.com/onestop/api/session-check/{session_id.split('_')[-1]}"

            # 设置 headers（包含关键 headers）
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/schedule',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': str(uuid.uuid4())[:16],
                'x-ticket-bff-language': 'ZH',
            }
            self.client.update_headers(headers)

            # POST 请求（空 body）
            response = self.client.post(url, json={})

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 会话状态检查成功")
                return result
            else:
                self.logger.warning(f"⚠️ 会话状态检查失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"检查会话状态异常: {e}", exc_info=True)
            return None

    def get_play_seats(self, goods_code: str, place_code: str, play_date: str,
                       session_id: str, biz_code: str = "88889") -> Optional[Dict]:
        """
        获取演出座位信息

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            play_date: 演出日期
            session_id: 会话 ID
            biz_code: 业务代码

        Returns:
            座位信息（包含座位图）
        """
        try:
            self.logger.info(f"[OneStop] 获取演出座位信息: playDate={play_date}")

            # URL 格式: /onestop/api/play-seq/play/{goodsCode}
            url = f"https://tickets.interpark.com/onestop/api/play-seq/play/{goods_code}"

            # 查询参数
            params = {
                'placeCode': place_code,
                'bizCode': biz_code,
                'playDate': play_date,  # 使用 playDate 而不是 playSeq
                'sessionId': session_id,
            }

            # 设置 headers
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/onestop/schedule',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'x-onestop-channel': 'TRIPLE_KOREA',
                'x-onestop-session': session_id,
                'x-onestop-trace-id': str(uuid.uuid4())[:16],
                'x-ticket-bff-language': 'ZH',
            }
            self.client.update_headers(headers)

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出座位信息获取成功")
                return result
            else:
                self.logger.warning(f"⚠️ 演出座位信息获取失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出座位信息异常: {e}", exc_info=True)
            return None
