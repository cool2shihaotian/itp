"""Cloudflare Turnstile 验证解决模块"""
import time
import json
import logging
from typing import Dict, Any, Optional
from .client import ITPClient


class CapsolverClient:
    """Capsolver 客户端"""

    CAPSOLVER_API_BASE = "https://api.capsolver.com"

    def __init__(self, api_key: str, logger: logging.Logger):
        """
        初始化 Capsolver 客户端

        Args:
            api_key: Capsolver API Key
            logger: logger 对象
        """
        self.api_key = api_key
        self.logger = logger

    def create_task(self, website_url: str, website_key: str) -> Optional[str]:
        """
        创建 Cloudflare Turnstile 解决任务

        Args:
            website_url: 网站 URL
            website_key: 网站 key (sitekey)

        Returns:
            任务 ID，失败返回 None
        """
        self.logger.info(f"创建 Capsolver 任务: {website_url}")

        task_data = {
            "clientKey": self.api_key,
            "task": {
                "type": "AntiTurnstileTaskProxyLess",
                "websiteURL": website_url,
                "websiteKey": website_key,
                "action": None,  # 某些网站需要
                "data": None,    # 某些网站需要
                "pageData": None,
                "proxy": None    # 使用 ProxyLess，不需要代理
            }
        }

        try:
            response = requests.post(
                f"{self.CAPSOLVER_API_BASE}/createTask",
                json=task_data,
                headers={'Content-Type': 'application/json'}
            )

            result = response.json()

            if result.get('errorId') == 0:
                task_id = result.get('taskId')
                self.logger.info(f"✅ Capsolver 任务创建成功: {task_id}")
                return task_id
            else:
                self.logger.error(f"❌ Capsolver 任务创建失败: {result.get('errorDescription', 'Unknown error')}")
                return None

        except Exception as e:
            self.logger.error(f"创建 Capsolver 任务异常: {e}", exc_info=True)
            return None

    def get_task_result(self, task_id: str, max_wait: int = 120) -> Optional[str]:
        """
        获取任务结果（轮询直到解决完成）

        Args:
            task_id: 任务 ID
            max_wait: 最大等待时间（秒）

        Returns:
            解决后的 token，失败返回 None
        """
        self.logger.info(f"等待 Capsolver 解决任务: {task_id}")

        start_time = time.time()
        poll_interval = 1  # 初始轮询间隔

        while time.time() - start_time < max_wait:
            try:
                response = requests.post(
                    f"{self.CAPSOLVER_API_BASE}/getTaskResult",
                    json={
                        "clientKey": self.api_key,
                        "taskId": task_id
                    },
                    headers={'Content-Type': 'application/json'}
                )

                result = response.json()

                if result.get('errorId') == 0:
                    status = result.get('status')

                    if status == 'ready':
                        token = result.get('solution', {}).get('token')
                        self.logger.info(f"✅ Cloudflare Turnstile 解决成功！")
                        self.logger.debug(f"Token: {token[:50]}...")
                        return token
                    elif status == 'processing':
                        self.logger.debug(f"任务处理中... ({int(time.time() - start_time)}s)")
                        time.sleep(poll_interval)
                        # 逐渐增加轮询间隔
                        poll_interval = min(poll_interval * 1.5, 6)
                    else:
                        self.logger.error(f"未知任务状态: {status}")
                        return None
                else:
                    self.logger.error(f"获取任务结果失败: {result.get('errorDescription', 'Unknown error')}")
                    return None

            except Exception as e:
                self.logger.error(f"获取任务结果异常: {e}", exc_info=True)
                time.sleep(poll_interval)

        self.logger.error(f"任务解决超时（{max_wait}秒）")
        return None

    def solve_turnstile(self, website_url: str, website_key: str, max_wait: int = 120) -> Optional[str]:
        """
        完整的 Cloudflare Turnstile 解决流程

        Args:
            website_url: 网站 URL
            website_key: 网站 key
            max_wait: 最大等待时间（秒）

        Returns:
            解决后的 token
        """
        # 创建任务
        task_id = self.create_task(website_url, website_key)
        if not task_id:
            return None

        # 等待结果
        token = self.get_task_result(task_id, max_wait)
        return token


# 导入 requests
import requests


class CloudflareSolver:
    """Cloudflare Turnstile 验证解决器"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化 Cloudflare 解决器

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: logger 对象
        """
        self.client = client
        self.config = config
        self.logger = logger

        # 初始化 Capsolver
        capsolver_config = config.get('capsolver', {})
        self.capsolver_enabled = capsolver_config.get('enabled', False)
        self.capsolver_api_key = capsolver_config.get('api_key', '')

        if self.capsolver_enabled and self.capsolver_api_key:
            self.capsolver = CapsolverClient(self.capsolver_api_key, logger)
            self.logger.info("Capsolver 已启用")
        else:
            self.capsolver = None
            self.logger.warning("Capsolver 未启用或未配置 API Key")

    def solve_cloudflare_challenge(self, website_url: str, website_key: str = None) -> Optional[str]:
        """
        解决 Cloudflare Turnstile 挑战

        Args:
            website_url: 网站 URL（例如：https://world.nol.com）
            website_key: Cloudflare sitekey（如果为 None，尝试从页面提取）

        Returns:
            验证 token
        """
        if not self.capsolver:
            self.logger.error("Capsolver 未启用，无法解决 Cloudflare 验证")
            return None

        self.logger.info("开始解决 Cloudflare Turnstile 验证...")

        # 如果没有提供 website_key，尝试从抓包数据中使用默认值
        if not website_key:
            # 从你的抓包数据看，Turnstile URL 中包含了验证信息
            # 实际的 website_key 需要从页面 HTML 或 JavaScript 中提取
            website_key = "0x4AAAAAABGU_tHsh_LkPT_k"  # 从你的抓包数据中的 URL 提取
            self.logger.info(f"使用默认 website_key: {website_key}")

        # 使用 Capsolver 解决
        token = self.capsolver.solve_turnstile(website_url, website_key)

        if token:
            self.logger.info("✅ Cloudflare 验证解决成功")
        else:
            self.logger.error("❌ Cloudflare 验证解决失败")

        return token

    def submit_cloudflare_token(self, token: str, challenge_url: str) -> bool:
        """
        提交 Cloudflare 验证 token

        Args:
            token: Capsolver 解决后的 token
            challenge_url: Cloudflare 挑战 URL

        Returns:
            提交是否成功
        """
        self.logger.info("提交 Cloudflare 验证 token...")

        # 根据抓包数据，提交 token 到 Cloudflare
        # 注意：实际的 URL 和参数格式可能需要调整
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'content-type': 'text/plain;charset=UTF-8',
                'origin': 'https://challenges.cloudflare.com',
                'referer': f'https://challenges.cloudflare.com/',
            }

            # 提交 token
            response = self.client.post(challenge_url, data=token, headers=headers)

            if response.status_code == 200:
                self.logger.info("✅ Cloudflare token 提交成功")
                return True
            else:
                self.logger.error(f"❌ Cloudflare token 提交失败: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"提交 Cloudflare token 异常: {e}", exc_info=True)
            return False
