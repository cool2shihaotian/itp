"""桥接鉴权模块 - NOL 到 Interpark"""
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class BridgeAuth:
    """NOL → Interpark 桥接鉴权"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.partner_token: Optional[str] = None
        self.partner_token_r: Optional[str] = None

    def get_enter_token(self, goods_code: str, place_code: str) -> Optional[Dict]:
        """
        获取进入 Interpark 的 partner token

        Args:
            goods_code: 商品代码
            place_code: 场馆代码

        Returns:
            包含 partner_token 的字典
        """
        try:
            self.logger.info(f"[桥接鉴权 1/2] 获取 enter token: goods={goods_code}, place={place_code}")

            url = "https://world.nol.com/api/users/enter/token"

            # 设置 headers
            headers = {
                'Content-Type': 'application/json',
                'Origin': 'https://world.nol.com',
                'Referer': 'https://world.nol.com/',
                'x-service-origin': 'global',
            }
            self.client.update_headers(headers)

            # 请求数据
            data = {
                "goods_code": goods_code,
                "place_code": place_code
            }

            response = self.client.post(url, json=data)

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ enter token 获取成功")

                # 提取 tokens - 注意返回的字段名
                if 'access_token' in result:
                    self.partner_token = result['access_token']
                    self.partner_token_r = result.get('refresh_token', '')
                    self.logger.debug(f"partner_token (access_token): {self.partner_token[:50]}...")
                    self.logger.debug(f"partner_token_r: {self.partner_token_r[:50]}...")

                    # 关键：将 partner_token 设置为 cookie，供后续 Interpark API 使用
                    self.client.set_cookie('partner_token', self.partner_token)
                    self.logger.info("✅ partner_token 已设置为 cookie")
                else:
                    self.logger.warning(f"响应中未找到 access_token，响应字段: {list(result.keys())}")

                return result
            else:
                self.logger.error(f"❌ enter token 获取失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"获取 enter token 异常: {e}", exc_info=True)
            return None

    def verify_bridge_token(self, goods_code: str, place_code: str, biz_code: str = "10965",
                            user_id: str = None, lang: str = "zh") -> Optional[Dict]:
        """
        验证 Interpark 桥接 token

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码（gates 阶段默认 10965）
            user_id: 用户 ID
            lang: 语言

        Returns:
            验证结果
        """
        try:
            self.logger.info(f"[桥接鉴权 2/2] 验证 bridge token")

            if not self.partner_token:
                self.logger.error("❌ 缺少 partner_token，请先调用 get_enter_token()")
                return None

            # 构建查询参数
            params = {
                'partner_token': self.partner_token,
                'partner_token_r': self.partner_token_r or '',
                'gc': goods_code,
                'pc': place_code,
                'bc': biz_code,
                'lg': lang,
            }

            if user_id:
                params['user_id'] = user_id

            # 设置 headers
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://tickets.interpark.com',
                'Referer': 'https://tickets.interpark.com/',
            }
            self.client.update_headers(headers)

            # 构建完整 URL（带查询参数）
            base_url = "https://ent-bridge.interpark.com/x13_02/v1/bridge/tokenVerify"
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{base_url}?{query_string}"

            self.logger.debug(f"完整 URL: {url[:150]}")

            # 使用 GET 请求（有些 API 即使是验证也用 GET）
            response = self.client.get(url)

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ bridge token 验证成功")
                return result
            else:
                self.logger.error(f"❌ bridge token 验证失败: {response.status_code}")
                self.logger.error(f"响应: {response.text}")

                # 如果验证失败，可能不需要显式验证，直接继续
                # 某些情况下，只要有了 enter token 就可以调用 gates 接口
                self.logger.warning("⚠️ tokenVerify 失败，但可能不影响后续流程")

                return None

        except Exception as e:
            self.logger.error(f"验证 bridge token 异常: {e}", exc_info=True)
            return None

    def full_bridge_auth(self, goods_code: str, place_code: str, biz_code: str = "10965",
                         user_id: str = None, lang: str = "zh", skip_verify: bool = True) -> bool:
        """
        完整的桥接鉴权流程

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码
            user_id: 用户 ID
            lang: 语言
            skip_verify: 是否跳过 tokenVerify（某些情况下可能不需要显式验证）

        Returns:
            是否成功
        """
        self.logger.info("=" * 70)
        self.logger.info("🌉 开始桥接鉴权流程（NOL → Interpark）")
        self.logger.info("=" * 70)

        # 步骤 1: 获取 enter token
        enter_result = self.get_enter_token(goods_code, place_code)
        if not enter_result:
            self.logger.error("桥接鉴权失败：无法获取 enter token")
            return False

        # 步骤 2: 验证 bridge token（可选）
        if not skip_verify:
            verify_result = self.verify_bridge_token(
                goods_code=goods_code,
                place_code=place_code,
                biz_code=biz_code,
                user_id=user_id,
                lang=lang
            )

            if not verify_result:
                self.logger.warning("⚠️ tokenVerify 失败，但继续尝试后续流程")

        self.logger.info("=" * 70)
        self.logger.info("✅ 桥接鉴权完成！已准备好进入 Interpark Gates")
        self.logger.info("=" * 70)

        return True
