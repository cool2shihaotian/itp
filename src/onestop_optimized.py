"""OneStop API - 优化版本

关键优化：
1. 修复 URL 路径（从 /v1/ 改为 /api/）
2. 优化 Headers 参数
3. 改进 Cookie 管理
4. 添加 session-check 的正确实现
"""
import json
import uuid
import time
from typing import Dict, Any, Optional
import logging
from .client import ITPClient


class OneStopBookingOptimized:
    """OneStop 选座系统 - 优化版本"""

    def __init__(self, client: ITPClient, config: Dict[str, Any], logger: logging.Logger):
        self.client = client
        self.config = config
        self.logger = logger
        self.play_seq: Optional[str] = None
        self.goods_code: Optional[str] = None
        self.place_code: Optional[str] = None

    def _generate_trace_id(self) -> str:
        """生成 trace ID"""
        return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

    def _get_standard_headers(self, session_id: str, referer: str = None) -> Dict[str, str]:
        """获取标准的 OneStop API headers"""
        trace_id = self._generate_trace_id()

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ko;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'no-cache',
            'Origin': 'https://tickets.interpark.com',
            'Referer': referer or 'https://tickets.interpark.com/onestop/schedule',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            # ⭐ 关键的 OneStop headers
            'x-onestop-channel': 'TRIPLE_KOREA',
            'x-onestop-session': session_id,
            'x-onestop-trace-id': trace_id,
            'x-ticket-bff-language': 'ZH',
        }

        return headers

    def get_play_dates(self, goods_code: str, place_code: str, biz_code: str = "88889",
                      session_id: str = None, ent_member_code: str = None) -> Optional[Dict]:
        """
        获取演出日期列表（优化版本）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            biz_code: 业务代码
            session_id: 会话 ID
            ent_member_code: 加密的会员代码

        Returns:
            演出日期列表
        """
        try:
            self.logger.info(f"[OneStop 优化版] 获取演出日期列表")

            # ✅ 修复：使用正确的 URL 路径
            # HAR 中的路径: /onestop/api/play/play-date/25018223
            url = f"https://tickets.interpark.com/onestop/api/play/play-date/{goods_code}"

            # 构建查询参数（按字母顺序排列，与 HAR 一致）
            params = {
                'bizCode': biz_code,
                'placeCode': place_code,
            }

            if session_id:
                params['sessionId'] = session_id

            if ent_member_code:
                params['entMemberCode'] = ent_member_code

            # 获取优化的 headers
            headers = self._get_standard_headers(
                session_id=session_id,
                referer='https://tickets.interpark.com/onestop/schedule'
            )

            # 添加特定的 headers
            headers['X-Requested-With'] = 'XMLHttpRequest'

            self.client.update_headers(headers)

            self.logger.debug(f"请求 URL: {url}")
            self.logger.debug(f"查询参数: {params}")
            self.logger.info(f"Session ID: {session_id}")
            self.logger.info(f"Trace ID: {headers['x-onestop-trace-id']}")

            # 发送请求
            response = self.client.get(url, params=params)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出日期列表获取成功！")

                # 美化输出
                if 'playDate' in result:
                    dates = result['playDate']
                    self.logger.info(f"可用日期: {', '.join(dates)}")

                return result
            elif response.status_code == 400:
                self.logger.error(f"❌ 400 Bad Request")
                self.logger.error(f"响应内容: {response.text}")

                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    self.logger.error(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    pass

                return None
            else:
                self.logger.warning(f"⚠️ 演出日期列表获取失败: {response.status_code}")
                self.logger.info(f"响应内容: {response.text[:500]}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出日期列表异常: {e}", exc_info=True)
            return None

    def check_session(self, session_id: str) -> Optional[Dict]:
        """
        检查会话状态（优化版本）

        Args:
            session_id: 会话 ID

        Returns:
            会话状态信息
        """
        try:
            self.logger.info(f"[OneStop 优化版] 检查会话状态")

            # ✅ 修复：使用正确的 URL 路径
            # 从 session_id 中提取数字部分: 25018223_M0000000751971768530066 -> M0000000751971768530066
            session_suffix = session_id.split('_')[-1] if '_' in session_id else session_id

            url = f"https://tickets.interpark.com/onestop/api/session-check/{session_suffix}"

            headers = self._get_standard_headers(
                session_id=session_id,
                referer='https://tickets.interpark.com/onestop/schedule'
            )
            headers['Content-Type'] = 'application/json'

            self.client.update_headers(headers)

            self.logger.info(f"Session ID: {session_id}")
            self.logger.info(f"Session suffix: {session_suffix}")

            # POST 请求（空 body）
            response = self.client.post(url, json={})

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("✅ 会话状态检查成功")
                self.logger.debug(f"会话信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            elif response.status_code == 404:
                self.logger.warning(f"⚠️ 会话不存在或已过期 (404)")
                self.logger.info("这可能意味着:")
                self.logger.info("  1. Session ID 已过期")
                self.logger.info("  2. Session ID 格式不正确")
                self.logger.info("  3. 需要重新调用 Middleware")
                return None
            else:
                self.logger.warning(f"⚠️ 会话状态检查失败: {response.status_code}")
                self.logger.info(f"响应内容: {response.text[:500]}")
                return None

        except Exception as e:
            self.logger.error(f"检查会话状态异常: {e}", exc_info=True)
            return None

    def get_play_seqs(self, goods_code: str, place_code: str, play_date: str,
                     session_id: str, biz_code: str = "88889") -> Optional[Dict]:
        """
        获取演出场次信息（优化版本）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            play_date: 演出日期 (YYYYMMDD)
            session_id: 会话 ID
            biz_code: 业务代码

        Returns:
            场次信息
        """
        try:
            self.logger.info(f"[OneStop 优化版] 获取演出场次信息: playDate={play_date}")

            # ✅ 修复：使用正确的 URL 路径
            url = f"https://tickets.interpark.com/onestop/api/play-seq/play/{goods_code}"

            # 查询参数
            params = {
                'bizCode': biz_code,
                'placeCode': place_code,
                'playDate': play_date,
                'sessionId': session_id,
            }

            headers = self._get_standard_headers(
                session_id=session_id,
                referer='https://tickets.interpark.com/onestop/schedule'
            )
            headers['X-Requested-With'] = 'XMLHttpRequest'

            self.client.update_headers(headers)

            response = self.client.get(url, params=params)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 演出场次信息获取成功")

                # 显示场次信息
                if 'playSeqs' in result:
                    seqs = result['playSeqs']
                    self.logger.info(f"可用场次: {len(seqs)} 个")
                    for seq in seqs[:3]:  # 只显示前 3 个
                        self.logger.info(f"  - {seq.get('playSeq', 'N/A')}: {seq.get('playTime', 'N/A')}")

                return result
            else:
                self.logger.warning(f"⚠️ 演出场次信息获取失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取演出场次信息异常: {e}", exc_info=True)
            return None

    def get_seat_blocks(self, goods_code: str, place_code: str, play_date: str,
                       play_seq: str, session_id: str, biz_code: str = "88889",
                       user_id: str = None) -> Optional[Dict]:
        """
        获取座位区块信息（优化版本）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            play_date: 演出日期
            play_seq: 场次编号
            session_id: 会话 ID
            biz_code: 业务代码
            user_id: 用户 ID

        Returns:
            座位区块信息
        """
        try:
            self.logger.info(f"[OneStop 优化版] 获取座位区块信息")

            # ✅ 修复：使用正确的 URL 路径
            url = f"https://tickets.interpark.com/onestop/api/play-seq/block-data"

            # 查询参数
            params = {
                'bizCode': biz_code,
                'goodsCode': goods_code,
                'page': '1',
                'placeCode': place_code,
                'playDate': play_date,
                'playSeq': play_seq,
                'sessionId': session_id,
            }

            if user_id:
                params['userId'] = user_id

            headers = self._get_standard_headers(
                session_id=session_id,
                referer='https://tickets.interpark.com/onestop/schedule'
            )
            headers['X-Requested-With'] = 'XMLHttpRequest'

            self.client.update_headers(headers)

            response = self.client.get(url, params=params)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 座位区块信息获取成功")
                return result
            else:
                self.logger.warning(f"⚠️ 座位区块信息获取失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取座位区块信息异常: {e}", exc_info=True)
            return None

    def get_seat_meta(self, goods_code: str, place_code: str, play_date: str,
                     play_seq: str, block_code: str, session_id: str,
                     biz_code: str = "88889") -> Optional[Dict]:
        """
        获取座位详细信息（优化版本）

        Args:
            goods_code: 商品代码
            place_code: 场馆代码
            play_date: 演出日期
            play_seq: 场次编号
            block_code: 区块代码
            session_id: 会话 ID
            biz_code: 业务代码

        Returns:
            座位详细信息
        """
        try:
            self.logger.info(f"[OneStop 优化版] 获取座位详细信息: blockCode={block_code}")

            # ✅ 修复：使用正确的 URL 路径
            url = f"https://tickets.interpark.com/onestop/api/play-seq/seat-meta"

            # 查询参数
            params = {
                'bizCode': biz_code,
                'blockCode': block_code,
                'goodsCode': goods_code,
                'page': '1',
                'placeCode': place_code,
                'playDate': play_date,
                'playSeq': play_seq,
                'sessionId': session_id,
            }

            headers = self._get_standard_headers(
                session_id=session_id,
                referer='https://tickets.interpark.com/onestop/schedule'
            )
            headers['X-Requested-With'] = 'XMLHttpRequest'

            self.client.update_headers(headers)

            response = self.client.get(url, params=params)

            self.logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                self.logger.info("✅ 座位详细信息获取成功")
                return result
            else:
                self.logger.warning(f"⚠️ 座位详细信息获取失败: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"获取座位详细信息异常: {e}", exc_info=True)
            return None