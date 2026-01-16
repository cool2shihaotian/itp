"""OneStop Middleware 实现 - 纯 requests 方案
基于 sessionId 与服务器时间的关系实现
"""
import hashlib
import hmac
import json
import base64
import time
import struct
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class OneStopMiddleware:
    """OneStop 中间件处理器 - 纯 requests 实现"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.server_time_ms = None
        self.server_time_offset = 0  # 服务器与本地时间的偏移量（毫秒）

    def get_server_time(self) -> Optional[int]:
        """
        获取服务器时间戳（毫秒）

        Returns:
            服务器时间戳（毫秒）
        """
        try:
            # 方法1: 使用 Interpark 的 getServerTime API
            url = "https://api-ticketfront.interpark.com/v1/getServerTime"
            params = {
                'type': '1',
                'nc': str(int(time.time() * 1000))
            }

            self.logger.debug(f"获取服务器时间: {url}")
            response = self.client.get(url, params=params)

            if response.status_code == 200 and response.text:
                server_time_ms = int(response.text)
                self.logger.info(f"✅ 服务器时间戳(毫秒): {server_time_ms}")

                # 计算时间偏移
                local_time_ms = int(time.time() * 1000)
                self.server_time_offset = server_time_ms - local_time_ms
                self.logger.debug(f"本地时间戳(毫秒): {local_time_ms}")
                self.logger.debug(f"时间偏移(毫秒): {self.server_time_offset}")

                self.server_time_ms = server_time_ms
                return server_time_ms

            self.logger.error(f"❌ 获取服务器时间失败: {response.status_code}")
            return None

        except Exception as e:
            self.logger.error(f"获取服务器时间异常: {e}", exc_info=True)
            return None

    def sync_time_with_session(self, session_id: str, goods_code: str) -> bool:
        """
        从 sessionId 中提取时间戳并同步时间

        Args:
            session_id: 从 waiting rank 获取的 sessionId
            goods_code: 商品代码

        Returns:
            是否成功
        """
        try:
            self.logger.info("从 sessionId 同步时间")

            # sessionId 格式: {goodsCode}_M00000{member_id}{timestamp}
            # 例如: 25018223_M0000000751971768530066

            # 提取时间戳部分（最后10位，秒级）
            parts = session_id.split('_')
            if len(parts) < 2:
                self.logger.error(f"sessionId 格式错误: {session_id}")
                return False

            session_part = parts[1]  # M0000000751971768530066

            # 提取最后10位作为时间戳（秒）
            if len(session_part) < 10:
                self.logger.error(f"session 部分长度不足: {session_part}")
                return False

            session_timestamp_sec = int(session_part[-10:])
            session_timestamp_ms = session_timestamp_sec * 1000

            self.logger.info(f"sessionId 时间戳(秒): {session_timestamp_sec}")
            self.logger.info(f"sessionId 时间戳(毫秒): {session_timestamp_ms}")

            # 获取当前服务器时间
            server_time_ms = self.get_server_time()
            if not server_time_ms:
                self.logger.warning("无法获取服务器时间，使用 sessionId 时间戳")
                server_time_ms = session_timestamp_ms

            # 计算时间差
            local_time_ms = int(time.time() * 1000)
            time_diff_sec = abs(server_time_ms - session_timestamp_ms) / 1000

            self.logger.info(f"时间差: {time_diff_sec:.2f} 秒")

            # 如果时间差太大（超过5秒），需要调整
            if time_diff_sec > 5:
                self.logger.warning(f"⚠️ 时间差过大: {time_diff_sec:.2f} 秒")
                self.logger.info("使用 sessionId 中的时间戳作为参考")

            self.server_time_ms = server_time_ms
            return True

        except Exception as e:
            self.logger.error(f"时间同步异常: {e}", exc_info=True)
            return False

    def visit_onestop_url(self, one_stop_url: str) -> bool:
        """
        访问 oneStopUrl，让服务器端建立 session

        这是关键步骤：必须先访问 oneStopUrl，让服务器端：
        1. 验证 sessionId
        2. 建立服务器端 session
        3. 设置必要的 cookies

        Args:
            one_stop_url: 从 waiting rank 获取的 oneStopUrl

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"[Middleware 1/3] 访问 OneStop URL")
            self.logger.debug(f"URL: {one_stop_url[:150]}...")

            # 设置 headers（模拟浏览器访问）
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }
            self.client.update_headers(headers)

            # 访问 oneStopUrl（允许重定向）
            response = self.client.get(one_stop_url, allow_redirects=True)

            self.logger.info(f"响应状态码: {response.status_code}")
            self.logger.info(f"最终 URL: {response.url[:150]}...")

            # 打印收到的 cookies
            self.logger.info(f"收到的 Cookies 数量: {len(response.cookies)}")
            for cookie in response.cookies:
                self.logger.info(f"  🍪 {cookie.name} = {cookie.value[:100] if len(cookie.value) > 100 else cookie.value}")

            if response.status_code == 200:
                self.logger.info("✅ 成功访问 OneStop URL")
                return True
            else:
                self.logger.warning(f"⚠️ 访问失败: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"访问 OneStop URL 异常: {e}", exc_info=True)
            return False

    def generate_middleware_payload(self, session_id: str, one_stop_key: str = None) -> str:
        """
        生成 middleware/set-cookie 的请求体

        基于分析，加密数据可能包含：
        1. sessionId
        2. 时间戳
        3. 签名

        Args:
            session_id: 会话 ID
            one_stop_key: 从 oneStopUrl 中提取的 key

        Returns:
            Base64 编码的请求体
        """
        try:
            # 获取当前服务器时间（或使用同步后的时间）
            if self.server_time_ms:
                timestamp = self.server_time_ms
            else:
                timestamp = int(time.time() * 1000)

            # 提取 sessionId 的组成部分
            parts = session_id.split('_')
            goods_code = parts[0] if len(parts) > 0 else ""
            session_part = parts[1] if len(parts) > 1 else ""

            # 生成加密数据
            # 根据分析，数据格式可能是:
            # - 8字节时间戳
            # - sessionId 哈希
            - 签名

            # 方法1: 简单的 JSON + Base64
            payload_json = {
                'sessionId': session_id,
                'goodsCode': goods_code,
                'timestamp': timestamp,
                'key': one_stop_key or ''
            }

            payload_str = json.dumps(payload_json, separators=(',', ':'))
            payload_bytes = payload_str.encode('utf-8')

            # 方法2: 二进制格式（更接近实际情况）
            # 64字节的二进制数据
            payload_binary = struct.pack('>Q', timestamp)  # 8字节时间戳(big-endian)

            # 添加 sessionId 的哈希
            session_hash = hashlib.sha256(session_id.encode()).digest()[:32]  # 32字节
            payload_binary += session_hash

            # 添加签名（HMAC-SHA256）
            if one_stop_key:
                signature = hmac.new(
                    one_stop_key.encode(),
                    payload_binary,
                    hashlib.sha256
                ).digest()[:24]  # 24字节签名
                payload_binary += signature

            self.logger.debug(f"二进制 payload 长度: {len(payload_binary)} 字节")

            # Base64 编码
            encoded = base64.b64encode(payload_binary).decode('ascii')

            self.logger.debug(f"生成的 payload: {encoded[:100]}...")
            return encoded

        except Exception as e:
            self.logger.error(f"生成 payload 异常: {e}", exc_info=True)
            # 返回一个基于 sessionId 的简单编码
            payload = f"{session_id}:{int(time.time()*1000)}".encode()
            return base64.b64encode(payload).decode('ascii')

    def call_middleware_set_cookie(self, session_id: str, one_stop_url: str = None,
                                   one_stop_key: str = None) -> bool:
        """
        调用 middleware/set-cookie API

        完整流程:
        1. 访问 oneStopUrl（如果提供）
        2. 同步服务器时间
        3. 生成加密的请求体
        4. 调用 middleware/set-cookie

        Args:
            session_id: 从 waiting rank 获取的 sessionId
            one_stop_url: 从 waiting rank 获取的 oneStopUrl
            one_stop_key: 从 oneStopUrl 提取的 key

        Returns:
            是否成功
        """
        try:
            self.logger.info("=" * 70)
            self.logger.info("OneStop Middleware - Set Cookie")
            self.logger.info("=" * 70)

            # 步骤 1: 访问 oneStopUrl（建立服务器端 session）
            if one_stop_url:
                success = self.visit_onestop_url(one_stop_url)
                if not success:
                    self.logger.warning("⚠️ 访问 OneStop URL 失败，但继续尝试")
            else:
                self.logger.info("未提供 oneStopUrl，跳过访问步骤")

            # 步骤 2: 同步时间
            self.logger.info(f"[Middleware 2/3] 同步服务器时间")
            time_synced = self.sync_time_with_session(session_id, session_id.split('_')[0])

            if not time_synced:
                self.logger.warning("⚠️ 时间同步失败，但继续尝试")

            # 步骤 3: 调用 middleware/set-cookie
            self.logger.info(f"[Middleware 3/3] 调用 middleware/set-cookie API")

            url = "https://tickets.interpark.com/onestop/middleware/set-cookie"

            # 从 oneStopUrl 提取 referer 和 key
            if one_stop_url and not one_stop_key:
                if 'key=' in one_stop_url:
                    one_stop_key = one_stop_url.split('key=')[-1].split('&')[0]

            # 生成请求体
            payload = self.generate_middleware_payload(session_id, one_stop_key)

            # 设置 headers（必须与 HAR 一致）
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': one_stop_url or 'https://tickets.interpark.com/onestop',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }
            self.client.update_headers(headers)

            self.logger.debug(f"请求数据: {payload[:100]}...")

            # 发送请求（payload 作为 JSON 字符串发送）
            response = self.client.post(url, data=payload)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code in [200, 201, 204]:
                self.logger.info("✅ middleware/set-cookie 成功")

                # 打印响应中设置的 cookies
                if response.cookies:
                    self.logger.info(f"响应设置的 Cookies: {len(response.cookies)}")
                    for cookie in response.cookies:
                        self.logger.info(f"  🍪 {cookie.name} = {cookie.value[:100]}")

                return True
            else:
                self.logger.warning(f"⚠️ middleware/set-cookie 失败: {response.status_code}")
                self.logger.debug(f"响应: {response.text[:500]}")

                # 即使失败，也可能已经设置了必要的 cookies
                # 继续 OneStop 流程
                self.logger.info("继续尝试 OneStop APIs...")

                return False

        except Exception as e:
            self.logger.error(f"middleware/set-cookie 异常: {e}", exc_info=True)
            return False

    def skip_middleware(self) -> bool:
        """
        跳过 middleware，直接进入 OneStop

        根据 HAR 文件分析，middleware 可能不是必需的：
        - 某些情况下可以直接调用 OneStop APIs
        - 关键是要有正确的 sessionId 和 cookies

        Returns:
            是否准备就绪
        """
        self.logger.info("ℹ️ 跳过 middleware/set-cookie")
        self.logger.info("提示: middleware 可能不总是必需的")
        return True
