"""HTTP 客户端封装"""
import requests
from typing import Dict, Any, Optional
import logging


class ITPClient:
    """Interpark Ticket HTTP 客户端"""

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化客户端

        Args:
            config: 配置字典
            logger: logger 对象
        """
        self.config = config
        self.logger = logger
        self.session = requests.Session()

        # 设置基本 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

        # 代理设置
        if config.get('proxy', {}).get('enabled', False):
            proxies = {
                'http': config['proxy'].get('http_proxy'),
                'https': config['proxy'].get('https_proxy')
            }
            self.session.proxies.update(proxies)
            self.logger.info(f"代理已启用: {proxies}")

        # Base URL (需要根据实际情况修改)
        self.base_url = "https://www.interpark.com"  # 待确认

    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            params: URL 参数
            **kwargs: 其他 requests 参数

        Returns:
            Response 对象
        """
        try:
            response = self.session.get(url, params=params, **kwargs)
            self.logger.debug(f"GET {url} - Status: {response.status_code}")
            return response
        except Exception as e:
            self.logger.error(f"GET 请求失败: {url} - {e}")
            raise

    def post(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            data: 表单数据
            json: JSON 数据
            **kwargs: 其他 requests 参数

        Returns:
            Response 对象
        """
        try:
            response = self.session.post(url, data=data, json=json, **kwargs)
            self.logger.debug(f"POST {url} - Status: {response.status_code}")
            return response
        except Exception as e:
            self.logger.error(f"POST 请求失败: {url} - {e}")
            raise

    def update_headers(self, headers: Dict[str, str]) -> None:
        """
        更新请求头

        Args:
            headers: 要添加或更新的 headers
        """
        self.session.headers.update(headers)
        self.logger.debug(f"Headers 已更新: {headers}")

    def set_cookie(self, name: str, value: str) -> None:
        """
        设置 Cookie

        Args:
            name: Cookie 名称
            value: Cookie 值
        """
        self.session.cookies.set(name, value)
        self.logger.debug(f"Cookie 已设置: {name}")

    def get_cookies(self) -> Dict[str, str]:
        """获取所有 Cookies"""
        return {cookie.name: cookie.value for cookie in self.session.cookies}

    def save_cookies(self) -> None:
        """保存 Cookies 到日志（用于调试）"""
        self.logger.info(f"当前 Cookies: {self.get_cookies()}")
