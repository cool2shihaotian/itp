"""快速测试多个座位ID，找到可用的"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
import json


def test_seat(client, seat_info_id, session_id):
    """测试单个座位"""
    url = "https://tickets.interpark.com/onestop/api/seats/preselect"

    data = {
        "blockKey": "001:401",
        "goodsCode": "25018223",
        "placeCode": "25001698",
        "playSeq": "001",
        "seatInfoId": seat_info_id,
        "sessionId": session_id
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://tickets.interpark.com',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': 'test',
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'KO'
    }

    response = client.post(url, json=data, headers=headers)

    if response.status_code in [200, 201]:
        result = response.json()
        if result.get('isSuccess'):
            return True, result
        else:
            return False, result
    else:
        return False, response.json()


def main():
    config = load_config()
    logger = setup_logging(config)

    client = ITPClient(config, logger)

    # 使用一个固定的 session ID（需要新鲜的）
    session_id = "25018223_M0000000761021768557720"  # 从上次测试获取的

    # 测试多个座位ID
    test_seats = [
        "25018223:25001698:001:2570",
        "25018223:25001698:001:2569",
        "25018223:25001698:001:2568",
        "25018223:25001698:001:2571",
        "25018223:25001698:001:2572",
        "25018223:25001698:001:2600",
        "25018223:25001698:001:2601",
        "25018223:25001698:001:2500",
        "25018223:25001698:001:2501",
        "25018223:25001698:001:2502",
    ]

    logger.info(f"\n使用 Session ID: {session_id}")
    logger.info("测试多个座位...")

    for seat_id in test_seats:
        success, result = test_seat(client, seat_id, session_id)
        status = "✅ 可用" if success else "❌ 占用"
        logger.info(f"{status} - {seat_id}")

        if success:
            logger.info(f"\n✅✅✅ 找到可用座位: {seat_id} ✅✅✅")
            logger.info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return seat_id

    logger.info("\n❌ 没有找到可用座位")
    return None


if __name__ == "__main__":
    try:
        seat = main()
        if seat:
            print(f"\n可用座位: {seat}")
        sys.exit(0 if seat else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
