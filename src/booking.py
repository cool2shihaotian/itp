"""座位和预订模块"""
from typing import Dict, Any, Optional, List
import logging
from .client import ITPClient
from . import api_config


class BookingManager:
    """座位和预订管理器"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        """
        初始化预订管理器

        Args:
            client: ITPClient 实例
            config: 配置字典
            logger: logger 对象
        """
        self.client = client
        self.config = config
        self.logger = logger

    def get_goods_info(self, goods_code: str, place_code: str, biz_code: str = None,
                       lang: str = 'zh', play_seq: str = None) -> Optional[Dict]:
        """
        获取商品信息（座位图）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码（默认从配置获取）
            lang: 语言
            play_seq: 演出序列号

        Returns:
            商品信息字典，包含座位图数据
        """
        try:
            self.logger.info(f"获取商品信息: goods={goods_code}, place={place_code}")

            # 从配置获取 biz_code（如果未提供）
            if not biz_code:
                biz_code = self.config.get('event', {}).get('biz_code', '10965')

            # 构建查询参数
            params = {
                'bizCode': biz_code,
                'goodsCode': goods_code,
                'placeCode': place_code,
                'lang': lang,
                'passCode': '',
                'nc': self._get_timestamp(),  # 时间戳防止缓存
            }

            if play_seq:
                params['playSeq'] = play_seq

            # 发送请求
            response = self.client.get(
                api_config.TICKETS_API['goods_info_url'],
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ 商品信息获取成功")
                return data
            else:
                self.logger.error(f"❌ 获取商品信息失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取商品信息异常: {e}", exc_info=True)
            return None

    def get_member_info(self, goods_code: str, channel_code: str = 'gp') -> Optional[Dict]:
        """
        获取会员预订信息

        Args:
            goods_code: 商品代码
            channel_code: 渠道代码

        Returns:
            会员信息字典
        """
        try:
            self.logger.info(f"获取会员预订信息: goods={goods_code}")

            # 构建查询参数
            params = {
                'goodsCode': goods_code,
                'channelCode': channel_code
            }

            # 发送请求
            response = self.client.get(
                api_config.TICKETS_API['member_info_url'],
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ 会员信息获取成功")
                return data
            else:
                self.logger.error(f"❌ 获取会员信息失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取会员信息异常: {e}", exc_info=True)
            return None

    def check_ekyc_auth(self, biz_code: str = None) -> Optional[Dict]:
        """
        检查 eKYC 认证状态

        Args:
            biz_code: 业务代码

        Returns:
            eKYC 认证状态
        """
        try:
            self.logger.info("检查 eKYC 认证状态")

            # 从配置获取 biz_code
            if not biz_code:
                biz_code = self.config.get('event', {}).get('biz_code', '10965')

            # 构建 URL
            url = f"{api_config.TICKETS_API['ekyc_auth_url']}/{biz_code}"

            # 构建查询参数
            params = {
                'nc': self._get_timestamp()
            }

            # 发送请求
            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ eKYC 认证状态获取成功")
                return data
            else:
                self.logger.error(f"❌ eKYC 认证状态获取失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"检查 eKYC 认证异常: {e}", exc_info=True)
            return None

    def _get_timestamp(self) -> int:
        """获取当前时间戳（毫秒）"""
        import time
        return int(time.time() * 1000)
