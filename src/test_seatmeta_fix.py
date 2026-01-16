#!/usr/bin/env python3
"""测试 seatMeta API 修复 - 逐个区域查询 + 完整 headers"""
import sys
import os
sys.path.insert(0, '/Users/shihaotian/Desktop/edison/itp/src')

import logging
from client import ITPClient
from polling_seat_selector import PollingSeatSelector

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("测试 seatMeta API - 逐个区域查询 + 完整 headers")
    logger.info("=" * 70)

    # 创建配置和客户端
    config = {
        'partner_token': '',
        'niost_hash': ''
    }

    client = ITPClient(config, logger)

    # 创建选座器
    selector = PollingSeatSelector(client, config, logger)

    # 使用 20260212 场次（playSeq=001）
    play_date = "20260212"
    play_seq = "001"

    # 使用一个真实的 session_id（从之前的测试获取）
    session_id = "25018223_M0000000756621768545182"

    logger.info(f"\n目标日期: {play_date}")
    logger.info(f"场次编号: {play_seq}")
    logger.info(f"Session ID: {session_id}")

    # 步骤 1: 获取区域代码
    logger.info("\n" + "=" * 70)
    logger.info("步骤 1: 获取区域代码（block-data）")
    logger.info("=" * 70)

    block_keys = selector.get_block_keys(play_seq, session_id)

    if not block_keys:
        logger.error("❌ 获取区域代码失败")
        return

    logger.info(f"✅ 获取到 {len(block_keys)} 个区域代码:")
    for i, key in enumerate(block_keys[:5], 1):  # 只显示前 5 个
        logger.info(f"  {i}. {key}")
    if len(block_keys) > 5:
        logger.info(f"  ... 还有 {len(block_keys) - 5} 个区域")

    # 步骤 2: 测试 seatMeta 查询（逐个区域）
    logger.info("\n" + "=" * 70)
    logger.info("步骤 2: 测试 seatMeta API（逐个区域查询）")
    logger.info("=" * 70)

    # 只测试前 3 个区域
    test_blocks = block_keys[:3]
    logger.info(f"测试前 {len(test_blocks)} 个区域...")

    for i, block_key in enumerate(test_blocks, 1):
        logger.info(f"\n--- 区域 {i}/{len(test_blocks)}: {block_key} ---")

        seat = selector.get_real_seat_availability(
            play_seq=play_seq,
            block_keys=[block_key],  # 逐个查询
            session_id=session_id,
            max_price=None
        )

        if seat:
            logger.info(f"✅ 区域 {block_key} 找到可售座位!")
            logger.info(f"  座位ID: {seat['seat_info_id']}")
            logger.info(f"  价位: {seat['seat_grade_name']} ({seat['price']:,}韩元)")
            logger.info(f"  位置: {seat['floor']} - {seat['row_no']} - {seat['seat_no']}")
            break
        else:
            logger.info(f"ℹ️ 区域 {block_key} 暂无可售座位")

    logger.info("\n" + "=" * 70)
    logger.info("✅ 测试完成！")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
