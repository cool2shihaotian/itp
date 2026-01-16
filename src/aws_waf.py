"""AWS WAF 验证解决模块 - 使用 Capmonster"""
import time
import requests
import logging
from typing import Dict, Any, Optional


class CapmonsterClient:
    """Capmonster API 客户端"""

    def __init__(self, api_key: str, logger: logging.Logger):
        self.api_key = api_key
        self.logger = logger
        self.base_url = "https://api.capmonster.cloud"

    def create_task(self, website_url: str, website_key: str,
                    use_proxy: bool = False) -> Optional[str]:
        """
        创建 AWS WAF 解决任务

        Args:
            website_url: WAF 挑战所在的网站 URL
            website_key: 网站 key（通常从页面中提取）
            use_proxy: 是否使用代理

        Returns:
            任务 ID，失败返回 None
        """
        try:
            # 构建任务类型
            task_type = "AWSWafTaskProxyLess" if not use_proxy else "AWSWafTask"

            # 构建任务数据
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": website_url,
                }
            }

            # 如果使用代理，需要添加代理配置
            if use_proxy:
                task_data["task"]["proxyAddress"] = ""  # 需要从配置读取
                task_data["task"]["proxyPort"] = ""
                task_data["task"]["proxyType"] = "HTTP"

            self.logger.info(f"创建 Capmonster 任务: {website_url}")
            self.logger.debug(f"任务类型: {task_type}")

            response = requests.post(
                f"{self.base_url}/createTask",
                json=task_data,
                timeout=30
            )

            result = response.json()

            if result.get("errorId") == 0:
                task_id = result.get("taskId")
                self.logger.info(f"✅ Capmonster 任务创建成功: {task_id}")
                return task_id
            else:
                self.logger.error(f"❌ 创建任务失败: {result.get('errorDescription', 'Unknown error')}")
                return None

        except Exception as e:
            self.logger.error(f"创建 Capmonster 任务异常: {e}", exc_info=True)
            return None

    def get_task_result(self, task_id: str, max_retries: int = 60,
                       interval: int = 2) -> Optional[Dict[str, Any]]:
        """
        获取任务结果

        Args:
            task_id: 任务 ID
            max_retries: 最大重试次数
            interval: 轮询间隔（秒）

        Returns:
            任务结果，包含 cookie 等，失败返回 None
        """
        try:
            self.logger.info(f"等待 Capmonster 解决任务: {task_id}")

            for i in range(max_retries):
                response = requests.post(
                    f"{self.base_url}/getTaskResult",
                    json={
                        "clientKey": self.api_key,
                        "taskId": task_id
                    },
                    timeout=30
                )

                result = response.json()

                if result.get("errorId") == 0:
                    status = result.get("status")

                    if status == "ready":
                        self.logger.info("✅ Capmonster 任务完成")
                        solution = result.get("solution", {})
                        return solution
                    elif status == "processing":
                        self.logger.debug(f"任务处理中... ({i+1}/{max_retries})")
                        time.sleep(interval)
                    else:
                        self.logger.warning(f"未知状态: {status}")
                        time.sleep(interval)
                else:
                    self.logger.error(f"获取结果失败: {result.get('errorDescription')}")
                    return None

            self.logger.error(f"任务超时（{max_retries * interval}秒）")
            return None

        except Exception as e:
            self.logger.error(f"获取任务结果异常: {e}", exc_info=True)
            return None


class AWSWAFSolver:
    """AWS WAF 挑战解决器"""

    def __init__(self, api_key: str, use_proxy: bool = False,
                 logger: logging.Logger = None):
        self.api_key = api_key
        self.use_proxy = use_proxy
        self.logger = logger or logging.getLogger(__name__)
        self.client = CapmonsterClient(api_key, logger)

    def solve_waf_challenge(self, website_url: str,
                           website_key: str = None) -> Optional[str]:
        """
        解决 AWS WAF 挑战

        Args:
            website_url: WAF 挑战所在的网站 URL
            website_key: 网站 key（可选，某些情况下需要）

        Returns:
            WAF cookie token，失败返回 None
        """
        try:
            self.logger.info("开始解决 AWS WAF 挑战...")
            self.logger.debug(f"目标 URL: {website_url}")

            # 创建任务
            task_id = self.client.create_task(
                website_url=website_url,
                website_key=website_key or "",
                use_proxy=self.use_proxy
            )

            if not task_id:
                self.logger.error("❌ AWS WAF 挑战解决失败：无法创建任务")
                return None

            # 获取结果
            solution = self.client.get_task_result(task_id)

            if solution:
                # Capmonster 返回的 solution 格式:
                # {
                #   "token": "xxx",
                #   "cookies": [...]
                # }
                token = solution.get("token")

                if token:
                    self.logger.info("✅ AWS WAF 挑战解决成功！")
                    self.logger.debug(f"Token: {token[:50]}...")
                    return token
                else:
                    self.logger.warning("解决方案中未找到 token")
                    # 尝试从 cookies 中提取
                    cookies = solution.get("cookies", [])
                    if cookies:
                        self.logger.info(f"从 cookies 中提取数据: {len(cookies)} 个")
            else:
                self.logger.error("❌ AWS WAF 挑战解决失败：无法获取结果")

            return None

        except Exception as e:
            self.logger.error(f"解决 AWS WAF 挑战异常: {e}", exc_info=True)
            return None

    def solve_waf_challenge_with_cookies(self, website_url: str,
                                        website_key: str = None) -> Optional[Dict[str, str]]:
        """
        解决 AWS WAF 挑战并返回完整的 cookies

        Args:
            website_url: WAF 挑战所在的网站 URL
            website_key: 网站 key（可选）

        Returns:
            Cookie 字典，失败返回 None
        """
        try:
            self.logger.info("开始解决 AWS WAF 挑战（获取 cookies）...")

            task_id = self.client.create_task(
                website_url=website_url,
                website_key=website_key or "",
                use_proxy=self.use_proxy
            )

            if not task_id:
                return None

            solution = self.client.get_task_result(task_id)

            if solution:
                token = solution.get("token")
                cookies = solution.get("cookies", [])

                if token:
                    # 构建完整的 cookie 字典
                    cookie_dict = {
                        "awswaf-token": token
                    }

                    # 添加额外的 cookies
                    for cookie in cookies:
                        if isinstance(cookie, dict):
                            name = cookie.get("name")
                            value = cookie.get("value")
                            if name and value:
                                cookie_dict[name] = value

                    self.logger.info(f"✅ 获取到 {len(cookie_dict)} 个 cookies")
                    return cookie_dict

            return None

        except Exception as e:
            self.logger.error(f"解决 AWS WAF 挑战异常: {e}", exc_info=True)
            return None
