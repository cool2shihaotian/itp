"""OneStop Middleware 实现 - 基于 rank 放行材料
根据 Step 13 的返回数据生成正确的 JSON 数组
"""
import json
import time
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class OneStopMiddlewareV2:
    """OneStop 中间件处理器 - 基于 rank 放行材料"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger

    def generate_middleware_payload(self, rank_data: Dict[str, Any]) -> str:
        """
        根据 Step 13 (rank) 的返回数据生成 middleware payload

        rank_data 包含：
        - sessionId: 会话 ID
        - oneStopUrl: 跳转 URL
        - key: 放行 key
        - k: 签名
        - totalRank: 0
        - myRank: 1
        - redirectChannel: IOP
        等

        Args:
            rank_data: Step 13 rank API 的完整返回数据

        Returns:
            JSON 数组字符串（用于 middleware/set-cookie）
        """
        try:
            self.logger.info("生成 middleware payload (JSON 数组)")

            # 提取关键字段
            session_id = rank_data.get('sessionId', '')
            one_stop_url = rank_data.get('oneStopUrl', '')
            key = rank_data.get('key', '')
            k = rank_data.get('k', '')  # 签名
            goods_code = rank_data.get('goodsCode', '')
            total_rank = rank_data.get('totalRank', 0)
            my_rank = rank_data.get('myRank', 1)
            redirect_channel = rank_data.get('redirectChannel', '')
            lang = rank_data.get('lang', 'zh')
            biz_code = rank_data.get('bizCode', '')

            # 从 oneStopUrl 提取 UUID key
            one_stop_key = ''
            if 'key=' in one_stop_url:
                one_stop_key = one_stop_url.split('key=')[-1].split('&')[0]

            self.logger.debug(f"sessionId: {session_id}")
            self.logger.debug(f"key: {key[:50] if key else '(empty)'}...")
            self.logger.debug(f"k: {k[:50] if k else '(empty)'}...")
            self.logger.debug(f"oneStopUrl key: {one_stop_key[:50] if one_stop_key else '(empty)'}...")

            # 方法 1: 简单的单元素数组（包含 sessionId）
            payload_array_1 = [session_id]
            size_1 = len(json.dumps(payload_array_1))
            self.logger.debug(f"方法 1 大小: {size_1} 字节")

            # 方法 2: 数组包含 key 和 sessionId
            payload_array_2 = [key, session_id]
            size_2 = len(json.dumps(payload_array_2))
            self.logger.debug(f"方法 2 大小: {size_2} 字节")

            # 方法 3: 数组包含多个字段
            payload_array_3 = [
                session_id,
                one_stop_key,
                k,
                goods_code
            ]
            size_3 = len(json.dumps(payload_array_3))
            self.logger.debug(f"方法 3 大小: {size_3} 字节")

            # 方法 4: 数组包含对象（放行材料）
            payload_array_4 = [{
                'sessionId': session_id,
                'key': one_stop_key,
                'signature': k,
                'goodsCode': goods_code,
                'bizCode': biz_code,
                'timestamp': int(time.time() * 1000)
            }]
            size_4 = len(json.dumps(payload_array_4))
            self.logger.debug(f"方法 4 大小: {size_4} 字节")

            # 方法 5: 单元素数组包含完整对象
            payload_array_5 = [{
                'sessionId': session_id,
                'oneStopUrl': one_stop_url,
                'key': key,
                'k': k,
                'goodsCode': goods_code,
                'bizCode': biz_code,
                'totalRank': total_rank,
                'myRank': my_rank,
                'redirectChannel': redirect_channel,
                'lang': lang,
                'userAgent': rank_data.get('userAgent', ''),
                'timestamp': int(time.time() * 1000)
            }]
            size_5 = len(json.dumps(payload_array_5))
            self.logger.debug(f"方法 5 大小: {size_5} 字节")

            # 选择最接近 90 字节的方法（HAR 显示 Content-Length: 90）
            best_payload = payload_array_1
            best_size = size_1

            for payload, size in [
                (payload_array_2, size_2),
                (payload_array_3, size_3),
                (payload_array_4, size_4),
                (payload_array_5, size_5)
            ]:
                if abs(size - 90) < abs(best_size - 90):
                    best_payload = payload
                    best_size = size

            self.logger.info(f"选择方法: payload 大小 {best_size} 字节")

            # 转换为 JSON 字符串
            payload_json = json.dumps(best_payload, separators=(',', ':'))

            self.logger.debug(f"生成的 payload: {payload_json[:200]}...")

            return payload_json

        except Exception as e:
            self.logger.error(f"生成 payload 异常: {e}", exc_info=True)
            # Fallback: 最简单的数组
            return json.dumps([rank_data.get('sessionId', '')])

    def call_middleware_set_cookie(self, rank_data: Dict[str, Any]) -> bool:
        """
        调用 middleware/set-cookie API

        Args:
            rank_data: Step 13 (rank) API 的完整返回数据

        Returns:
            是否成功
        """
        try:
            self.logger.info("=" * 70)
            self.logger.info("OneStop Middleware - Set Cookie (V2)")
            self.logger.info("=" * 70)

            # 步骤 1: 访问 oneStopUrl（建立服务器端 session）
            one_stop_url = rank_data.get('oneStopUrl', '')
            if one_stop_url:
                self.logger.info(f"[步骤 1/3] 访问 OneStop URL")

                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
                self.client.update_headers(headers)

                response = self.client.get(one_stop_url, allow_redirects=True)
                self.logger.info(f"访问状态: {response.status_code}")
                self.logger.info(f"收到的 cookies: {len(response.cookies)}")

                for cookie in response.cookies:
                    self.logger.debug(f"  🍪 {cookie.name} = {cookie.value[:80] if len(cookie.value) > 80 else cookie.value}")

            # 步骤 2: 生成 JSON 数组 payload
            self.logger.info(f"\n[步骤 2/3] 生成 middleware payload")
            payload = self.generate_middleware_payload(rank_data)

            # 步骤 3: 调用 middleware/set-cookie
            self.logger.info(f"\n[步骤 3/3] 调用 middleware/set-cookie API")

            url = "https://tickets.interpark.com/onestop/middleware/set-cookie"

            # 设置 headers（与 HAR 完全一致）
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': one_stop_url or 'https://tickets.interpark.com/onestop',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }
            self.client.update_headers(headers)

            self.logger.debug(f"请求 URL: {url}")
            self.logger.debug(f"Payload 大小: {len(payload)} 字节")
            self.logger.debug(f"Payload 内容: {payload}")

            # 尝试多种发送方式
            # 方式 1: 使用 json= 参数（自动序列化并设置 Content-Type）
            self.logger.info("尝试方式 1: json= 参数")
            response = self.client.post(url, json=json.loads(payload))

            # 如果方式 1 失败，记录但继续
            if response.status_code not in [200, 201, 204]:
                self.logger.info(f"方式 1 失败: {response.status_code}")
                self.logger.debug(f"响应: {response.text[:200]}")

            self.logger.info(f"响应状态码: {response.status_code}")
            self.logger.debug(f"响应 headers: {dict(response.headers)}")

            if response.status_code in [200, 201, 204]:
                self.logger.info("✅ middleware/set-cookie 成功！")

                # 打印响应中设置的 cookies
                if response.cookies:
                    self.logger.info(f"响应设置的 Cookies: {len(response.cookies)}")
                    for cookie in response.cookies:
                        self.logger.info(f"  🍪 {cookie.name} = {cookie.value[:100] if len(cookie.value) > 100 else cookie.value}")

                return True
            else:
                self.logger.warning(f"⚠️ middleware/set-cookie 返回: {response.status_code}")
                self.logger.info(f"响应内容: {response.text[:500]}")

                # 即使返回 400，也检查是否有设置 cookies
                if response.cookies:
                    self.logger.info(f"虽然返回 {response.status_code}，但设置了 {len(response.cookies)} 个 cookies")
                    for cookie in response.cookies:
                        self.logger.info(f"  🍪 {cookie.name} = {cookie.value[:100]}")

                return False

        except Exception as e:
            self.logger.error(f"middleware/set-cookie 异常: {e}", exc_info=True)
            return False
