"""登录和认证模块"""
from typing import Dict, Any, Optional
import logging
import json
import uuid
from datetime import datetime
from .client import ITPClient
from . import api_config
from .cloudflare import CloudflareSolver


class AuthManager:
    """认证管理器"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化认证管理器

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: logger 对象
        """
        self.client = client
        self.config = config
        self.logger = logger
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.device_id: Optional[str] = None
        self.turnstile_token: Optional[str] = None  # Cloudflare Turnstile token

        # 初始化 Cloudflare 解决器
        self.cloudflare_solver = CloudflareSolver(client, config, logger)

    def _generate_device_id(self) -> str:
        """生成设备 ID"""
        return str(uuid.uuid4())

    def _setup_firebase_headers(self) -> Dict[str, str]:
        """设置 Firebase 登录所需的 headers"""
        return {
            'Content-Type': 'application/json',
            'Origin': 'https://world.nol.com',
            'Referer': 'https://world.nol.com/',
            'x-browser-channel': 'stable',
            # TODO: x-browser-validation 可能需要动态生成
            'x-browser-year': api_config.FIREBASE_CONFIG['browser_year'],
            'x-client-version': api_config.FIREBASE_CONFIG['client_version'],
            'x-firebase-gmpid': api_config.FIREBASE_CONFIG['gmp_id'],
            'x-client-data': 'CI+2yQEIprbJAQipncoBCJ3hygEIlaHLAQiGoM0BGO+izwE=',
        }

    def login(self, username: str, password: str, skip_cloudflare: bool = False) -> bool:
        """
        登录 Interpark (NOL)

        Args:
            username: 邮箱
            password: 密码
            skip_cloudflare: 是否跳过 Cloudflare 验证（默认 False）

        Returns:
            登录是否成功
        """
        self.logger.info("开始登录流程...")

        try:
            # 1. 设置设备 ID
            if not self.device_id:
                self.device_id = self._generate_device_id()
                self.client.set_cookie(api_config.COOKIE_NAMES['device_id'], self.device_id)
                self.logger.info(f"设备 ID: {self.device_id}")

            # 2. Cloudflare 验证
            if not skip_cloudflare:
                self.logger.info("开始 Cloudflare Turnstile 验证...")

                # 使用 Capsolver 解决 Cloudflare 验证
                self.turnstile_token = self.cloudflare_solver.solve_cloudflare_challenge(
                    website_url="https://world.nol.com",
                    website_key="0x4AAAAAABGU_tHsh_LkPT_k"  # 从抓包数据中提取
                )

                if not self.turnstile_token:
                    self.logger.error("Cloudflare 验证失败")
                    return False

                self.logger.info("Cloudflare 验证成功")
            else:
                self.logger.info("跳过 Cloudflare 验证")

            # 3. Firebase 登录
            self.logger.info("正在通过 Firebase 登录...")
            firebase_url = f"{api_config.FIREBASE_CONFIG['signin_url']}?key={api_config.FIREBASE_CONFIG['api_key']}"

            # 设置 Firebase headers
            firebase_headers = self._setup_firebase_headers()
            self.client.update_headers(firebase_headers)

            # 准备登录数据
            login_data = {
                "email": username,
                "password": password,
                "returnSecureToken": True,
                "clientType": "CLIENT_TYPE_WEB"
            }

            # 发送登录请求
            response = self.client.post(
                firebase_url,
                json=login_data
            )

            if response.status_code != 200:
                self.logger.error(f"Firebase 登录失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return False

            # 解析响应
            result = response.json()
            self.access_token = result.get('idToken')
            self.refresh_token = result.get('refreshToken')
            self.user_id = result.get('localId')  # Firebase user ID

            if not self.access_token:
                self.logger.error("未获取到 access token")
                return False

            self.logger.info("Firebase 登录成功")

            # 4. 调用 NOL 登录接口，获取 NOL access_token
            nol_token = self._get_nol_token(self.access_token, self.turnstile_token)
            if nol_token:
                self.nol_access_token = nol_token
                self.logger.info("NOL token 获取成功")
            else:
                self.logger.warning("NOL token 获取失败")

            # 5. 设置 cookies
            self.client.set_cookie(api_config.COOKIE_NAMES['access_token'], self.access_token)
            self.client.set_cookie(api_config.COOKIE_NAMES['refresh_token'], self.refresh_token)
            self.client.set_cookie(api_config.COOKIE_NAMES['language'], 'zh-CN')

            # 6. 获取 eKYC token
            ekyc_token = self._get_ekyc_token()
            if ekyc_token:
                self.logger.info("eKYC token 获取成功")
            else:
                self.logger.warning("eKYC token 获取失败，但登录成功")

            self.logger.info("=" * 50)
            self.logger.info("登录成功！")
            self.logger.info(f"用户 ID: {self.user_id}")
            self.logger.info(f"Access Token: {self.access_token[:50]}...")
            self.logger.info("=" * 50)

            return True

        except Exception as e:
            self.logger.error(f"登录过程出错: {e}", exc_info=True)
            return False

    def _get_nol_token(self, firebase_token: str, turnstile_token: str = None) -> Optional[str]:
        """
        使用 Firebase token 获取 NOL access_token

        Args:
            firebase_token: Firebase idToken
            turnstile_token: Cloudflare Turnstile token（可选，但如果 NOL 要求验证则必需）

        Returns:
            NOL access_token 或 None
        """
        try:
            self.logger.info("正在获取 NOL access_token...")

            # NOL 登录接口
            nol_login_url = "https://world.nol.com/auth-web/api/users/auth/login/web"

            # 设置 headers（从 HAR 中提取）
            headers = {
                'Content-Type': 'application/json',
                'Origin': 'https://world.nol.com',
                'Referer': 'https://world.nol.com/',
                'x-service-origin': 'global',
                'x-triple-user-lang': 'zh-CN',
            }
            self.client.update_headers(headers)

            # 准备请求数据
            login_data = {
                "fbToken": firebase_token
            }

            # 如果有 turnstile token，添加到请求中
            if turnstile_token:
                login_data["turnstileToken"] = turnstile_token
                self.logger.info("使用 Turnstile token")
            else:
                self.logger.warning("⚠️ 没有 Turnstile token，可能会被拒绝")

            # 发送请求
            response = self.client.post(nol_login_url, json=login_data)

            if response.status_code == 201:
                self.logger.info("NOL 登录接口调用成功")

                # 检查响应中的 cookies
                cookies = response.cookies
                if 'access_token' in cookies:
                    nol_token = cookies['access_token']
                    self.logger.info(f"✅ 成功获取 NOL access_token: {nol_token[:60]}...")

                    # 更新 cookie
                    self.client.set_cookie('access_token', nol_token)

                    return nol_token
                else:
                    self.logger.warning("响应中没有 access_token cookie")
                    self.logger.debug(f"响应 cookies: {dict(cookies)}")

                    # 检查响应体
                    try:
                        resp_data = response.json()
                        self.logger.debug(f"响应数据: {resp_data}")
                    except:
                        pass

            else:
                self.logger.error(f"NOL 登录接口失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")

            return None

        except Exception as e:
            self.logger.error(f"获取 NOL token 出错: {e}", exc_info=True)
            return None

    def _get_ekyc_token(self) -> Optional[str]:
        """
        获取 eKYC token

        Returns:
            eKYC token 或 None
        """
        try:
            self.logger.info("正在获取 eKYC token...")

            # 设置 headers
            headers = {
                'x-service-origin': api_config.NOL_API['service_origin'],
            }
            self.client.update_headers(headers)

            # 发送请求
            response = self.client.get(api_config.NOL_API['ekyc_token_url'])

            if response.status_code == 200:
                result = response.json()
                ekyc_token = result.get('token')
                if ekyc_token:
                    self.logger.info(f"eKYC token: {ekyc_token[:50]}...")
                    return ekyc_token
                else:
                    self.logger.warning(f"eKYC 响应中没有 token: {result}")
            else:
                self.logger.error(f"获取 eKYC token 失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")

            return None

        except Exception as e:
            self.logger.error(f"获取 eKYC token 出错: {e}", exc_info=True)
            return None

    def is_logged_in(self) -> bool:
        """
        检查是否已登录

        Returns:
            是否已登录
        """
        # 检查是否有有效的 access token
        if self.access_token:
            return True

        # 检查 cookies
        cookies = self.client.get_cookies()
        if api_config.COOKIE_NAMES['access_token'] in cookies:
            self.access_token = cookies[api_config.COOKIE_NAMES['access_token']]
            return True

        return False

    def logout(self) -> bool:
        """
        登出

        Returns:
            登出是否成功
        """
        self.logger.info("开始登出...")

        # 清除 tokens
        self.access_token = None
        self.refresh_token = None

        # 清除 cookies
        self.client.session.cookies.clear()

        self.logger.info("登出成功")
        return True

    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证所需的 headers

        Returns:
            headers 字典
        """
        headers = {}

        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        return headers
