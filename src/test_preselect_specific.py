"""测试预选特定座位 - 使用已知成功的参数"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
from src.payment_flow import InterparkPaymentFlow
import json


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试预选座位 - 使用手动测试中成功的参数")
    logger.info("=" * 70)

    # 初始化
    client = ITPClient(config, logger)
    payment_flow = InterparkPaymentFlow(client, config, logger)

    # 使用手动测试中成功的数据
    selected_seat = {
        'play_date': '20260212',
        'play_seq': '001',
        'seat_info_id': '25018223:25001698:001:2510',  # ✅ 使用手动测试中的座位ID
        'seat_grade': '1',
        'seat_grade_name': 'R석',
        'floor': '1층',
        'row_no': 'D1구역 3열',
        'seat_no': '17',
        'price': 143000,
        'block_key': '001:401',
        'poll_count': 1,
        'elapsed_time': 0
    }

    session_id = '25018223_M0000000760281768556329'  # ✅ 使用手动测试中的 session

    logger.info(f"\n座位信息:")
    logger.info(f"  座位ID: {selected_seat['seat_info_id']}")
    logger.info(f"  blockKey: {selected_seat['block_key']}")
    logger.info(f"  Session ID: {session_id}")

    # 测试 preselect
    logger.info("\n" + "=" * 70)
    logger.info("调用 preselect API")
    logger.info("=" * 70)

    # 直接构造请求
    url = "https://tickets.interpark.com/onestop/api/seats/preselect"

    data = {
        "blockKey": "001:401",
        "goodsCode": "25018223",
        "placeCode": "25001698",
        "playSeq": "001",
        "seatInfoId": "25018223:25001698:001:2510",
        "sessionId": session_id
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://tickets.interpark.com',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': 'wNdjgj2qRrAcQsKe',
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'ZH'
    }

    logger.info(f"\n请求URL: {url}")
    logger.info(f"请求参数: {json.dumps(data, indent=2, ensure_ascii=False)}")

    response = client.post(url, json=data, headers=headers)

    logger.info(f"\n响应状态码: {response.status_code}")
    logger.info(f"响应内容: {response.text}")

    if response.status_code in [200, 201]:
        result = response.json()
        logger.info("\n" + "=" * 70)
        logger.info("✅ 预选成功！")
        logger.info("=" * 70)
        logger.info(f"返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ 预选失败")
        logger.error("=" * 70)
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
