#!/usr/bin/env python3
"""直接测试 block-data 和 seatMeta APIs"""
import requests
import json

def test_blockdata():
    """测试 block-data API"""
    print("=" * 70)
    print("测试 block-data API")
    print("=" * 70)

    url = "https://tickets.interpark.com/onestop/api/seats/block-data"
    params = {
        'goodsCode': '25018223',
        'placeCode': '25001698',
        'playSeq': '001'
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': '25018223_M0000000756841768545933',  # 更新为最新的 session ID
        'x-requested-with': 'XMLHttpRequest'
    }

    print(f"\n请求 URL: {url}")
    print(f"参数: {json.dumps(params, indent=2)}")
    print(f"\n发送请求...")

    response = requests.get(url, params=params, headers=headers, timeout=10)

    print(f"\n状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 成功！获取到 {len(data)} 个区域:")
        for i, block in enumerate(data[:5], 1):
            print(f"  {i}. {block.get('blockKey')} - {block.get('blockName')}")
        if len(data) > 5:
            print(f"  ... 还有 {len(data) - 5} 个区域")
        return data
    else:
        print(f"\n❌ 失败！")
        print(f"响应内容: {response.text[:500]}")
        return None

def test_seatmeta(block_keys):
    """测试 seatMeta API（逐个查询）"""
    print("\n" + "=" * 70)
    print("测试 seatMeta API（逐个查询）")
    print("=" * 70)

    url = "https://tickets.interpark.com/onestop/api/seatMeta"

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': '25018223_M0000000756841768545933',  # 更新为最新的 session ID
        'x-onestop-trace-id': 'test1234567890',
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'ZH'
    }

    # 测试前 3 个区域
    for i, block_key in enumerate(block_keys[:3], 1):
        print(f"\n--- 区域 {i}/{min(3, len(block_keys))}: {block_key} ---")

        params = {
            'goodsCode': '25018223',
            'placeCode': '25001698',
            'playSeq': '001',
            'blockKeys': block_key
        }

        print(f"请求参数: {json.dumps(params, indent=2)}")

        response = requests.get(url, params=params, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ 成功！数据类型: {type(data)}")

                if isinstance(data, list) and len(data) > 0:
                    print(f"返回数组长度: {len(data)}")
                    for block in data:
                        seats = block.get('seats', [])
                        print(f"  区域 {block.get('blockKey')}: {len(seats)} 个座位")

                        # 检查是否有可售座位
                        available = [s for s in seats if s.get('isExposable', False)]
                        if available:
                            print(f"  ✅ 找到 {len(available)} 个可售座位!")
                            seat = available[0]
                            print(f"     示例: ID={seat.get('seatInfoId')}, "
                                  f"等级={seat.get('seatGradeName')}, "
                                  f"价格={seat.get('salesPrice'):,}韩元")
                            return seat
                else:
                    print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            except Exception as e:
                print(f"解析 JSON 失败: {e}")
                print(f"响应内容: {response.text[:500]}")
        elif response.status_code == 500:
            print(f"⚠️ 服务器错误 500，跳过此区域")
        else:
            print(f"❌ 失败！")
            print(f"响应内容: {response.text[:500]}")

    return None

if __name__ == "__main__":
    # 步骤 1: 测试 block-data
    blocks = test_blockdata()

    if blocks:
        block_keys = [block['blockKey'] for block in blocks]

        # 步骤 2: 测试 seatMeta
        seat = test_seatmeta(block_keys)

        if seat:
            print("\n" + "=" * 70)
            print("✅ 成功找到可售座位！")
            print("=" * 70)
            print(json.dumps(seat, indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 70)
            print("ℹ️ 未能找到可售座位（可能当前无票）")
            print("=" * 70)
    else:
        print("\n❌ block-data API 失败，无法继续测试 seatMeta")
