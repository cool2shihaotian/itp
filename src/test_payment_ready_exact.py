"""测试 payment/ready - 使用完全相同的格式"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logging
from src.client import ITPClient
import json


def main():
    config = load_config()
    logger = setup_logging(config)

    logger.info("\n" + "=" * 70)
    logger.info("测试 payment/ready - 使用完全相同的格式")
    logger.info("=" * 70)

    client = ITPClient(config, logger)

    # 使用成功请求中的完全相同的 URL
    url = "https://tickets.interpark.com/onestop/api/payment/ready/25018223"

    # 成功请求中的完全相同的数据
    data = {
        "autoSeat": False,
        "bizCode": "88889",
        "entMemberCode": "MTo1MzQxMzI6",
        "sessionId": "25018223_M0000000760281768556329",
        "goodsCode": "25018223",
        "placeCode": "25001698",
        "playSeq": "001",
        "playDate": "20260212",
        "ticketCount": 1,
        "totalFee": 151000,
        "totalCommissionFee": 8000,
        "paymentInfo": {
            "settleCount": 1,
            "kindOfPayment": "22003",
            "firstSettleAmount": 151000,
            "useVoucher": False,
            "voucherCodes": [""],
            "voucherSalesPrices": ["0"],
            "pgType": "VN005",
            "cardNo": "",
            "cardPassword": "",
            "cardSsn": "",
            "validInfo": "",
            "cardKind": "12001"
        },
        "deliveryInfo": {
            "deliveryMethod": "WILL_CALL",
            "deliveryAmount": 0,
            "deliveryPackage": "",
            "deliveryPackageAmount": 0,
            "isDelivery": False,
            "name": "USER",
            "birthDate": "9602120",
            "email": "user@example.com",
            "userPhone": "821012345678",
            "recipient": "",
            "addressPhone": "",
            "subAddressPhone": "",
            "address": "undefined | undefined | undefined | undefined",
            "subAddress": "",
            "zipCode": "",
            "bookPassword": ""
        },
        "discountInfo": {
            "cardDiscountNumber": "",
            "cardDiscountType": "",
            "otherDiscountType": "",
            "topingDiscountType": ""
        },
        "priceInfo": [
            {
                "dblDiscountOrNot": "N",
                "discountCode": "00000",
                "groupId": "12133",
                "pgCode": "PG002",
                "priceGrade": "U1",
                "priceGradeName": "일반",
                "salesPrice": "143000.0",
                "seatGrade": "1",
                "seatGradeName": "R석",
                "ticketAmount": "143000.0"
            }
        ],
        "seatInfo": [
            {
                "blockNo": "401",
                "floor": "1층",
                "rowNo": "D1구역 3열",
                "seatGrade": "1",
                "seatNo": "17",
                "seatInfoId": "25018223:25001698:001:2510"
            }
        ],
        "couponInfo": {
            "discountAmount": 0
        },
        "marketingAgree": False,
        "waitingInfo": {},
        "partnerPointInfo": {}
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://tickets.interpark.com',
        'Referer': 'https://tickets.interpark.com/onestop/price',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': '25018223_M0000000760281768556329',
        'x-onestop-trace-id': 'wNdjgj2qRrAcQsKe',
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'KO'
    }

    logger.info(f"\n请求URL: {url}")
    logger.info(f"\n请求参数 (关键信息):")
    logger.info(f"  Session ID: {data['sessionId']}")
    logger.info(f"  座位ID: {data['seatInfo'][0]['seatInfoId']}")
    logger.info(f"  价格: {data['priceInfo'][0]['salesPrice']}")
    logger.info(f"  总价: {data['totalFee']}")

    response = client.post(url, json=data, headers=headers)

    logger.info(f"\n响应状态码: {response.status_code}")

    if response.status_code in [200, 201]:
        result = response.json()
        logger.info("\n" + "=" * 70)
        logger.info("✅ payment/ready 成功！")
        logger.info("=" * 70)
        logger.info(f"返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ payment/ready 失败")
        logger.error("=" * 70)
        logger.error(f"响应: {response.text}")
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
