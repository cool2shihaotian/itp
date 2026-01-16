"""活动信息模块"""
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class EventManager:
    """活动信息管理器"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化活动管理器

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: logger 对象
        """
        self.client = client
        self.config = config
        self.logger = logger

    def get_sales_info(self, goods_code: str, place_code: str, biz_code: str = None) -> Optional[Dict]:
        """
        获取发售信息

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码（可选）

        Returns:
            发售信息字典，失败返回 None
        """
        try:
            self.logger.info(f"获取发售信息: goods={goods_code}, place={place_code}")

            # 构建查询参数
            params = {
                "goodsCode": goods_code,
                "placeCode": place_code,
            }
            if biz_code:
                params["bizCode"] = biz_code

            # 发送请求
            response = self.client.get(
                self.client.config.get('nol_api', {}).get('salesinfo_url',
                    'https://world.nol.com/api/ent-channel-out/v1/goods/salesinfo'),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ 发售信息获取成功")
                return data
            else:
                self.logger.error(f"❌ 获取发售信息失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取发售信息异常: {e}", exc_info=True)
            return None

    def enter_event(self, goods_code: str, place_code: str) -> Optional[Dict]:
        """
        用户进入活动页面

        Args:
            goods_code: 商品代码
            place_code: 场馆代码

        Returns:
            进入信息字典，失败返回 None
        """
        try:
            self.logger.info(f"用户进入活动: goods={goods_code}, place={place_code}")

            # 设置特殊的 headers
            headers = {
                'x-service-origin': 'global',
                'x-triple-user-lang': 'zh-CN',
            }
            self.client.update_headers(headers)

            # 构建查询参数
            params = {
                "goods_code": goods_code,
                "place_code": place_code,
            }

            # 发送请求
            response = self.client.get(
                self.client.config.get('nol_api', {}).get('enter_url',
                    'https://world.nol.com/api/users/enter'),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ 进入活动成功")
                return data
            else:
                self.logger.error(f"❌ 进入活动失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"进入活动异常: {e}", exc_info=True)
            return None

    def get_event_detail(self, goods_code: str, place_code: str) -> Optional[Dict]:
        """
        获取活动详细信息（包含发售信息和用户进入信息）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码

        Returns:
            活动详细信息字典
        """
        result = {
            "goods_code": goods_code,
            "place_code": place_code,
            "sales_info": None,
            "enter_info": None,
        }

        # 获取发售信息
        sales_info = self.get_sales_info(goods_code, place_code)
        result["sales_info"] = sales_info

        # 获取用户进入信息
        enter_info = self.enter_event(goods_code, place_code)
        result["enter_info"] = enter_info

        return result
