"""排队系统模块 - Interpark Waiting Queue"""
from typing import Dict, Any, Optional
import logging
import time
import json
from .client import ITPClient
from .aws_waf import AWSWAFSolver


class WaitingQueue:
    """Interpark 排队系统"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.waiting_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.secure_url: Optional[str] = None

        # 初始化 AWS WAF 解决器
        capmonster_config = config.get('capmonster', {})
        self.capmonster_enabled = capmonster_config.get('enabled', False)
        self.waf_solver = None

        if self.capmonster_enabled:
            api_key = capmonster_config.get('api_key')
            use_proxy = capmonster_config.get('use_proxy', False)
            if api_key:
                self.waf_solver = AWSWAFSolver(api_key, use_proxy, logger)
                self.logger.info("✅ Capmonster AWS WAF 解决器已启用")
            else:
                self.logger.warning("⚠️ Capmonster 已启用但未配置 api_key")
        else:
            self.logger.info("ℹ️ Capmonster 未启用，AWS WAF 挑战将被跳过")

    def get_secure_url(self, signature: str, secure_data: str, biz_code: str = "88889",
                      goods_code: str = None) -> Optional[Dict]:
        """
        获取排队安全 URL（排队入口）

        Args:
            signature: 从 member-info 获取的签名
            secure_data: 从 member-info 获取的安全数据
            biz_code: 业务代码（默认 88889 用于 waiting）
            goods_code: 商品代码

        Returns:
            包含 secureUrl 和 key 的字典
        """
        try:
            self.logger.info(f"[排队 1/4] 获取安全 URL (secure-url)")

            url = "https://ent-waiting-api.interpark.com/waiting/api/secure-url"

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
                'secureData': secure_data,
                'signature': signature,
                'preSales': 'N',  # 是否预售，默认 N（否）
                'lang': 'zh',     # 语言
                'from': 'NTG',    # 来源（New Ticket Global）
            }

            if goods_code:
                data['goodsCode'] = goods_code

            self.logger.debug(f"请求数据: {json.dumps(data, indent=2)}")

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ secure-url 获取成功")
                self.logger.debug(f"完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

                # 响应可能返回 redirectUrl 或 secureUrl
                url_field = result.get('redirectUrl') or result.get('secureUrl')

                if url_field:
                    self.secure_url = url_field
                    self.logger.debug(f"URL: {self.secure_url}")

                    # 提取 key（用于后续 line-up）
                    # 格式: https://...?key=xxx
                    if 'key=' in self.secure_url:
                        from urllib.parse import unquote
                        key = self.secure_url.split('key=')[-1].split('&')[0]

                        # ⚠️ 关键修复：URL 解码 key
                        # HAR 文件显示 line-up API 需要解码后的 key（包含 / 和 +）
                        # 而不是 URL 编码的格式（包含 %2F 和 %2B）
                        key_decoded = unquote(key)

                        self.logger.debug(f"URL 编码的 key: {key[:50]}...")
                        self.logger.debug(f"解码后的 key: {key_decoded[:50]}...")

                        result['key'] = key_decoded  # 存储解码后的 key
                        self.logger.info(f"✅ 提取到 key (已解码): {key_decoded[:50]}...")
                        return result

                    # 提取 sessionId
                    if 'sessionId=' in self.secure_url:
                        self.session_id = self.secure_url.split('sessionId=')[-1].split('&')[0]
                        self.logger.debug(f"session_id: {self.session_id}")

                # 检查是否有直接的 key 字段
                if 'key' in result:
                    self.logger.info(f"✅ 从响应中获取 key: {result['key'][:50]}...")
                    return result

                self.logger.warning(f"⚠️ 未找到 key，响应字段: {list(result.keys())}")
                return result
            else:
                self.logger.error(f"❌ secure-url 获取失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取 secure-url 异常: {e}", exc_info=True)
            return None

    def solve_aws_waf(self, waf_url: str = None, website_key: str = None) -> Optional[str]:
        """
        解决 AWS WAF 挑战

        Args:
            waf_url: WAF 挑战 URL（如果未提供，使用 secure_url 或默认值）
            website_key: 网站 key（某些情况下需要从页面提取）

        Returns:
            验证后的 token
        """
        try:
            self.logger.info(f"[排队 2/4] 解决 AWS WAF 挑战")

            # 检查是否启用 Capmonster
            if not self.capmonster_enabled or not self.waf_solver:
                self.logger.info("ℹ️ Capmonster 未启用，跳过 AWS WAF 挑战")
                self.logger.info("ℹ️ 某些情况下可能不需要显式解决 WAF，直接尝试 line-up")
                return ""

            # 如果没有提供 WAF URL，从 secure_url 提取或使用默认值
            if not waf_url:
                if self.secure_url:
                    # 尝试从 secure_url 提取基础 URL
                    # secureUrl 可能包含 WAF 挑战信息
                    waf_url = self.secure_url.split('?')[0]
                else:
                    # 使用默认的 Interpark WAF URL
                    waf_url = "https://tickets.interpark.com/"

            self.logger.info(f"使用 Capmonster 解决 AWS WAF 挑战...")
            self.logger.debug(f"目标 URL: {waf_url}")

            # 调用 Capmonster 解决 WAF 挑战
            token = self.waf_solver.solve_waf_challenge(
                website_url=waf_url,
                website_key=website_key
            )

            if token:
                self.logger.info("✅ AWS WAF 挑战解决成功")

                # 将 token 设置为 cookie
                self.client.set_cookie('awswaf-token', token)
                self.logger.debug("WAF token 已设置为 cookie")

                return token
            else:
                self.logger.warning("⚠️ Capmonster WAF 解决失败，但继续尝试 line-up")
                return ""

        except Exception as e:
            self.logger.error(f"解决 AWS WAF 异常: {e}", exc_info=True)
            return None

    def line_up(self, key: str) -> Optional[Dict]:
        """
        进入排队（line-up）

        根据 HAR 文件分析，line-up API 只需要 key 参数，不需要 bizCode、platform、goodsCode

        Args:
            key: 从 secure-url 获取的 key（URL 编码格式）

        Returns:
            包含 waitingId 的字典
        """
        try:
            self.logger.info(f"[排队 3/4] 进入排队 (line-up)")

            url = "https://ent-waiting-api.interpark.com/waiting/api/line-up"

            # 设置 headers（与 HAR 一致）
            headers = {
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }
            self.client.update_headers(headers)

            # ⚠️ 关键修复：根据 HAR 文件，请求体只包含 key，不包含其他参数
            # 请求体格式: {"key":"..."}
            # key 需要使用 URL 编码的原始值（从 secure-url 获取的值）
            data = {
                'key': key
            }

            self.logger.debug(f"请求数据: {json.dumps(data, indent=2)}")

            response = self.client.post(url, json=data)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ line-up 成功")

                # 提取 waitingId
                if 'waitingId' in result:
                    self.waiting_id = result['waitingId']
                    self.logger.info(f"waiting_id: {self.waiting_id}")

                return result
            else:
                self.logger.error(f"❌ line-up 失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"line-up 异常: {e}", exc_info=True)
            return None

    def poll_rank(self, waiting_id: str = None, biz_code: str = "88889",
                  interval: int = 2, timeout: int = 300) -> Optional[Dict]:
        """
        轮询排队位置（rank）

        Args:
            waiting_id: 排队 ID
            biz_code: 业务代码
            interval: 轮询间隔（秒）
            timeout: 超时时间（秒）

        Returns:
            排队状态信息
        """
        try:
            self.logger.info(f"[排队 4/4] 轮询排队位置 (rank)")

            if not waiting_id:
                waiting_id = self.waiting_id

            if not waiting_id:
                self.logger.error("❌ 缺少 waiting_id，无法轮询")
                return None

            url = "https://ent-waiting-api.interpark.com/waiting/api/rank"

            # 构建查询参数
            params = {
                'bizCode': biz_code,
                'waitingId': waiting_id,
            }

            start_time = time.time()
            poll_count = 0

            while time.time() - start_time < timeout:
                poll_count += 1
                self.logger.debug(f"轮询 #{poll_count}: waiting_id={waiting_id[:20]}...")

                response = self.client.get(url, params=params)

                if response.status_code == 200:
                    result = response.json()
                    self.logger.debug(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

                    # 检查排队状态
                    status = result.get('status', '')
                    rank = result.get('rank', 0)

                    self.logger.info(f"📊 当前状态: {status}, 排队位置: {rank}")

                    # 如果可以进入（status 为特定值），返回结果
                    if status in ['ENTER', 'READY', 'SUCCESS']:
                        self.logger.info("✅ 排队完成，可以进入！")
                        return result

                    # 如果还需要等待，继续轮询
                    if status in ['WAIT', 'QUEUE', 'PENDING']:
                        time.sleep(interval)
                        continue

                    # 其他未知状态，返回结果
                    return result
                else:
                    self.logger.warning(f"⚠️ rank 请求失败: {response.status_code}")
                    self.logger.warning(f"响应: {response.text}")
                    time.sleep(interval)

            self.logger.warning(f"⏰ 排队超时（{timeout}秒）")
            return None

        except Exception as e:
            self.logger.error(f"轮询 rank 异常: {e}", exc_info=True)
            return None

    def visit_waiting_page(self, key: str, goods_code: str = None, member_id: str = None) -> Optional[str]:
        """
        访问 Waiting 页面获取 sessionId（纯 requests 实现，无需浏览器）

        Args:
            key: 从 secure-url 获取的 key
            goods_code: 商品代码（用于验证 sessionId）
            member_id: 会员 ID（用于验证 sessionId）

        Returns:
            sessionId，格式: {goodsCode}_M00000{member_id}{timestamp}
        """
        try:
            self.logger.info(f"[排队页面] 访问 Waiting 页面获取 sessionId")

            # 构建 waiting 页面 URL
            url = f"https://tickets.interpark.com/waiting?key={key}"

            # 设置 headers（模拟浏览器访问）
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }
            self.client.update_headers(headers)

            self.logger.debug(f"访问 URL: {url[:100]}...")

            # 访问 waiting 页面
            response = self.client.get(url, allow_redirects=True)

            self.logger.info(f"响应状态码: {response.status_code}")
            self.logger.info(f"最终 URL: {response.url[:150]}...")

            # 打印所有 cookies
            self.logger.info(f"收到的 Cookies 数量: {len(response.cookies)}")
            for cookie in response.cookies:
                self.logger.info(f"  🍪 {cookie.name} = {cookie.value[:100] if len(cookie.value) > 100 else cookie.value}")

            # 方法 1: 从 cookies 中提取 sessionId
            for cookie in response.cookies:
                self.logger.debug(f"Cookie: {cookie.name} = {cookie.value[:50] if len(cookie.value) > 50 else cookie.value}")

                # 检查常见的 sessionId cookie 名称
                if 'session' in cookie.name.lower() or 'sid' in cookie.name.lower():
                    session_id = cookie.value
                    # 验证格式
                    if goods_code and member_id:
                        if self._validate_session_id(session_id, goods_code, member_id):
                            self.session_id = session_id
                            self.logger.info(f"✅ 从 cookie 获取 sessionId: {session_id}")
                            return session_id
                    else:
                        # 如果无法验证，仍然返回
                        self.logger.info(f"✅ 从 cookie 获取 sessionId（未验证）: {session_id}")
                        self.session_id = session_id
                        return session_id

            # 方法 2: 从重定向 URL 中提取 sessionId
            if response.url and 'sessionId=' in response.url:
                session_id = response.url.split('sessionId=')[-1].split('&')[0]
                if self._validate_session_id(session_id, goods_code, member_id):
                    self.session_id = session_id
                    self.logger.info(f"✅ 从重定向 URL 获取 sessionId: {session_id}")
                    return session_id

            # 打印 HTML 内容的前 500 字符用于调试
            html_preview = response.text[:500] if response.text else "(空)"
            self.logger.info(f"HTML 内容预览 (前 500 字符):\n{html_preview}")

            # 方法 3: 从响应 HTML 中提取 sessionId（JavaScript 变量）
            import re
            session_patterns = [
                r'sessionId["\']?\s*[:=]\s*["\']([^"\']+)',
                r'SESSION_ID["\']?\s*[:=]\s*["\']([^"\']+)',
                r'(\d+_M\d+_\d+)',  # 格式: 25018223_M0000000751971768530066
            ]

            for pattern in session_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if self._validate_session_id(match, goods_code, member_id):
                        self.session_id = match
                        self.logger.info(f"✅ 从 HTML 中获取 sessionId: {match}")
                        return match

            # 方法 4: 从 Set-Cookie 响应头中提取
            if 'Set-Cookie' in response.headers:
                import http.cookies
                cookie_header = response.headers.get('Set-Cookie', '')
                self.logger.debug(f"Set-Cookie header: {cookie_header[:200]}...")

                # 尝试从 Set-Cookie 中解析
                for pattern in session_patterns:
                    match = re.search(pattern, cookie_header)
                    if match:
                        session_id = match.group(1)
                        if self._validate_session_id(session_id, goods_code, member_id):
                            self.session_id = session_id
                            self.logger.info(f"✅ 从 Set-Cookie 获取 sessionId: {session_id}")
                            return session_id

            # 方法 5: 尝试调用一个需要 sessionId 的 API，看服务器是否会设置它
            self.logger.info("ℹ️ 尝试通过 API 调用触发 sessionId 生成...")

            # 调用 rank API（可能会触发 sessionId 设置）
            rank_url = "https://ent-waiting-api.interpark.com/waiting/api/rank"
            params = {
                'bizCode': '88889',
                'waitingId': 'dummy',  # 可能会触发错误但设置 cookie
            }

            rank_response = self.client.get(rank_url, params=params)

            # 检查新的 cookies
            for cookie in rank_response.cookies:
                if 'session' in cookie.name.lower() or 'sid' in cookie.name.lower():
                    session_id = cookie.value
                    if self._validate_session_id(session_id, goods_code, member_id):
                        self.session_id = session_id
                        self.logger.info(f"✅ 从 API 响应 cookie 获取 sessionId: {session_id}")
                        return session_id

            self.logger.warning("⚠️ 未能从 waiting 页面获取 sessionId")
            self.logger.info("提示: 可能需要实际售票期间才能生成 sessionId")
            return None

        except Exception as e:
            self.logger.error(f"访问 waiting 页面异常: {e}", exc_info=True)
            return None

    def generate_session_id(self, goods_code: str, member_id: str = None) -> str:
        """
        生成 sessionId（基于 HAR 文件中发现的模式）

        格式: {goodsCode}_M00000{member_id}{timestamp}
        例如: 25018223_M0000000751971768530066

        Args:
            goods_code: 商品代码
            member_id: 会员 ID（如果为 None，使用时间戳的一部分）

        Returns:
            生成的 sessionId
        """
        import time

        # 当前时间戳（毫秒）
        timestamp_ms = int(time.time() * 1000)

        # 如果提供了 member_id，使用它
        # 否则使用时间戳的后半部分
        if member_id:
            # 确保 member_id 是数字
            member_id = str(member_id).replace('M00000', '').replace('M', '')
            # 补齐到 8 位（基于 HAR 分析）
            member_id = member_id.zfill(8)
        else:
            # 使用时间戳的一部分作为 member_id
            member_id = str(timestamp_ms)[-8:]

        # 组合: M00000 + member_id + timestamp
        # 注意：HAR 中的格式是 M00000{8位member_id}{10位timestamp}
        # 总长度应该是: 5(M00000) + 8(member_id) + 10(timestamp) = 23 位
        session_id = f"M00000{member_id}{timestamp_ms}"

        # 完整 sessionId: {goodsCode}_{session_id}
        full_session_id = f"{goods_code}_{session_id}"

        self.logger.info(f"生成 sessionId: {full_session_id}")
        self.logger.debug(f"  组成部分: goods_code={goods_code}, member_id={member_id}, timestamp={timestamp_ms}")

        self.session_id = full_session_id
        return full_session_id

    def _validate_session_id(self, session_id: str, goods_code: str = None, member_id: str = None) -> bool:
        """
        验证 sessionId 格式是否正确

        Args:
            session_id: 待验证的 sessionId
            goods_code: 商品代码（用于验证）
            member_id: 会员 ID（用于验证）

        Returns:
            是否有效
        """
        if not session_id:
            return False

        # 基本格式检查: {goodsCode}_M00000{member_id}{timestamp}
        # 例如: 25018223_M0000000751971768530066

        import re

        # 检查基本格式: 数字_M数字_数字
        pattern = r'^\d+_M\d+_\d+$'
        if not re.match(pattern, session_id):
            self.logger.debug(f"sessionId 格式不匹配: {session_id}")
            return False

        # 如果提供了 goods_code，验证前缀
        if goods_code:
            if not session_id.startswith(goods_code + '_'):
                self.logger.debug(f"sessionId goods_code 不匹配: {session_id} (期望: {goods_code})")
                # 不一定要完全匹配，可能格式略有不同
                # return False

        # 如果提供了 member_id，验证是否包含
        if member_id:
            if member_id not in session_id:
                self.logger.debug(f"sessionId member_id 不匹配: {session_id} (期望包含: {member_id})")
                # 可能是加密后的 member_id
                # return False

        # 长度检查（通常 20-50 字符）
        if len(session_id) < 10 or len(session_id) > 100:
            self.logger.debug(f"sessionId 长度异常: {len(session_id)}")
            return False

        return True

    def full_waiting_queue(self, signature: str, secure_data: str, goods_code: str = None,
                          biz_code: str = "88889", skip_waf: bool = True) -> bool:
        """
        完整的排队流程

        Args:
            signature: 从 member-info 获取的签名
            secure_data: 从 member-info 获取的安全数据
            goods_code: 商品代码
            biz_code: 业务代码
            skip_waf: 是否跳过 AWS WAF 挑战

        Returns:
            是否成功完成排队
        """
        self.logger.info("=" * 70)
        self.logger.info("🔀 开始排队流程（Interpark Waiting Queue）")
        self.logger.info("=" * 70)

        # 步骤 1: 获取 secure-url
        secure_result = self.get_secure_url(
            signature=signature,
            secure_data=secure_data,
            biz_code=biz_code,
            goods_code=goods_code
        )

        if not secure_result:
            self.logger.error("排队失败：无法获取 secure-url")
            return False

        # 提取 key
        key = secure_result.get('key', '')
        if not key:
            self.logger.error("secure-url 响应中未找到 key")
            return False

        # 步骤 2: AWS WAF 挑战（可选）
        if not skip_waf:
            waf_result = self.solve_aws_waf()
            if not waf_result:
                self.logger.warning("⚠️ WAF 挑战失败，但继续尝试 line-up")
        else:
            self.logger.info("⏭️ 跳过 AWS WAF 挑战")

        # 步骤 3: 进入排队（line-up）
        # 根据 HAR 分析，line-up 只需要 key 参数
        line_up_result = self.line_up(key=key)

        if not line_up_result:
            self.logger.error("排队失败：line-up 失败")
            return False

        # 步骤 4: 轮询排队位置
        rank_result = self.poll_rank(
            waiting_id=self.waiting_id,
            biz_code=biz_code
        )

        if not rank_result:
            self.logger.error("排队失败：轮询超时或失败")
            return False

        self.logger.info("=" * 70)
        self.logger.info("✅ 排队完成！已准备好进入 OneStop")
        self.logger.info("=" * 70)

        return True
