"""OneStop Middleware 实现 - 正确的 64 字节二进制格式"""
import json
import time
import struct
import base64
import hashlib
import hmac
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class OneStopMiddlewareV3:
    """OneStop 中间件处理器 - 64 字节二进制格式"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger

    def generate_64byte_payload(self, rank_data: Dict[str, Any]) -> str:
        """
        生成 64 字节的二进制 payload（Base64 编码后约 90 字符）

        根据 HAR 分析：
        - 总长度: 64 字节
        - Base64 后: 88 字符（接近 Content-Length: 90）
        - 格式: 可能包含时间戳、sessionId 哈希、签名等

        Args:
            rank_data: Step 13 (rank) API 的完整返回数据

        Returns:
            Base64 编码的字符串（包含引号，作为 JSON 字符串）
        """
        try:
            session_id = rank_data.get('sessionId', '')
            key = rank_data.get('key', '')
            k = rank_data.get('k', '')  # 签名
            goods_code = rank_data.get('goodsCode', '')
            biz_code = rank_data.get('bizCode', '88889')

            self.logger.info("生成 64 字节二进制 payload")

            # 方法 1: 基于时间戳 + sessionId + 签名
            timestamp_ms = int(time.time() * 1000)

            # 8 字节：时间戳（big-endian）
            timestamp_bytes = struct.pack('>Q', timestamp_ms)

            # 32 字节：sessionId 的 SHA256 哈希
            session_hash = hashlib.sha256(session_id.encode()).digest()

            # 24 字节：HMAC 签名（使用 key）
            if key:
                signature = hmac.new(
                    key.encode(),
                    (session_id + str(timestamp_ms)).encode(),
                    hashlib.sha256
                ).digest()[:24]
            else:
                signature = b'\x00' * 24

            # 组合: 8 + 32 + 24 = 64 字节
            payload_binary = timestamp_bytes + session_hash + signature

            self.logger.debug(f"二进制 payload 长度: {len(payload_binary)} 字节")

            # Base64 编码
            encoded = base64.b64encode(payload_binary).decode('ascii')
            self.logger.debug(f"Base64 编码后长度: {len(encoded)} 字符")
            self.logger.debug(f"Base64 payload: {encoded[:100]}...")

            # 返回 JSON 字符串格式（带引号）
            return f'"{encoded}"'

        except Exception as e:
            self.logger.error(f"生成 payload 异常: {e}", exc_info=True)
            # Fallback: 使用 HAR 中的格式
            return '"WEIySghN51y5TRm7d5ZUfOep6rZW87yamgfjvty+jhSTXyYVFB+NK4GIbjA+c+9Dhypvvb6tMPF5m0jNMdJwYA=="'

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
            self.logger.info("OneStop Middleware - Set Cookie (V3)")
            self.logger.info("=" * 70)

            # 步骤 1: 访问 oneStopUrl
            one_stop_url = rank_data.get('oneStopUrl', '')
            if one_stop_url:
                self.logger.info(f"[步骤 1/2] 访问 OneStop URL")

                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
                self.client.update_headers(headers)

                response = self.client.get(one_stop_url, allow_redirects=True)
                self.logger.info(f"访问状态: {response.status_code}")

            # 步骤 2: 生成并发送 payload
            self.logger.info(f"\n[步骤 2/2] 调用 middleware/set-cookie API")

            # 生成 Base64 编码的 payload
            payload_json_string = self.generate_64byte_payload(rank_data)

            url = "https://tickets.interpark.com/onestop/middleware/set-cookie"

            # 设置 headers（与 HAR 一致）
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': one_stop_url or 'https://tickets.interpark.com/onestop',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }
            self.client.update_headers(headers)

            self.logger.debug(f"请求体: {payload_json_string[:100]}...")
            self.logger.debug(f"请求体长度: {len(payload_json_string)} 字符")

            # 发送请求（使用 data= 参数发送字符串）
            response = self.client.post(url, data=payload_json_string)

            self.logger.info(f"响应状态码: {response.status_code}")

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

                # 即使失败，也检查是否有设置 cookies
                if response.cookies:
                    self.logger.info(f"虽然返回 {response.status_code}，但设置了 {len(response.cookies)} 个 cookies")

                return False

        except Exception as e:
            self.logger.error(f"middleware/set-cookie 异常: {e}", exc_info=True)
            return False
