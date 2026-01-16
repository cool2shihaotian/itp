# ITP 购票系统 - 选座逻辑详解

**更新时间**: 2026-01-16
**版本**: v1.0

---

## 📋 目录

1. [选座流程概览](#选座流程概览)
2. [当前实现逻辑](#当前实现逻辑)
3. [完整API调用顺序](#完整api调用顺序)
4. [数据结构说明](#数据结构说明)
5. [选座策略](#选座策略)
6. [WebSocket座位选择](#websocket座位选择)

---

## 🎯 选座流程概览

### 整体流程图

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 获取演出日期列表 (play-date API)                            │
│     输入: goodsCode, placeCode                                   │
│     输出: ["20260212", "20260213", "20260214", "20260215"]       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 选择日期                                                    │
│     策略: 默认第一个日期，或根据用户配置选择                     │
│     示例: 20260212                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 获取场次和座位信息 (play-seq API)                           │
│     输入: goodsCode, placeCode, playDate                         │
│     输出:场次列表，每个场次包含座位等级和价格                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 选择场次和价位                                              │
│     策略: 第一个场次，第一个有座位的价位                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 获取座位等级详情 (seats/grades API)                         │
│     输入: goodsCode, placeCode, playSeq                         │
│     输出: 所有座位等级的详细信息（颜色、余票等）                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 初始化座位 (seats/init API)                                 │
│     输入: goodsCode, placeCode, playSeq, sessionId              │
│     输出: WebSocket连接信息                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. WebSocket 座位选择                                          │
│     连接 WebSocket 获取实时座位图                                │
│     选择具体座位号                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. 支付初始化                                                  │
│     init-essential: 获取支付方式、银行列表                       │
│     init-additional: 获取折扣、优惠券信息                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. 生成付款链接                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 当前实现逻辑

### 步骤 1: 获取演出日期列表

**API**: `/onestop/api/play/play-date/{goodsCode}`

**请求参数**:
```python
params = {
    'placeCode': '25001698',
    'bizCode': '88889',
    'sessionId': session_id,
    'entMemberCode': enc_member_code
}
```

**响应**:
```json
{
  "playDate": ["20260212", "20260213", "20260214", "20260215"],
  "nextPlayDate": ""
}
```

**当前逻辑**:
```python
# 获取所有可用日期
available_dates = play_dates.get('playDate', [])

# 策略: 选择第一个日期
selected_date = available_dates[0]  # 20260212
```

**可选优化**:
- 根据用户配置选择特定日期
- 过滤周末/工作日
- 选择余票最多的日期

---

### 步骤 2: 获取场次和座位信息

**API**: `/onestop/api/play-seq/play/{goodsCode}`

**请求参数**:
```python
params = {
    'placeCode': '25001698',
    'playDate': selected_date,  # 20260212
    'sessionId': session_id,
    'entMemberCode': enc_member_code,
    'bizCode': '88889'
}
```

**响应**:
```json
[
  {
    "playDate": "20260212",
    "playSeq": "001",
    "playTime": "7:00 PM",
    "onlineDepositEndTime": "20260208",
    "noOfTime": 1,
    "isSeatRemain": "N",  // 是否有余票
    "isRemainSeatVisible": false,
    "cancelableEndDate": "202602111700",
    "goodsCode": "25018223",
    "placeCode": "25001698",
    "onlineAccountYn": "Y",
    "seats": [
      {
        "seatExternalType": 0,
        "seatGrade": "1",           // 座位等级代码
        "seatGradeName": "R석",     // 座位等级名称
        "remainCount": 0,           // 剩余票数
        "salesPrice": 143000,       // 票价（韩元）
        "isSacToday": "N",
        "isVisibleSeatCount": false
      },
      {
        "seatExternalType": 0,
        "seatGrade": "2",
        "seatGradeName": "S석",
        "remainCount": 0,
        "salesPrice": 132000,
        "isSacToday": "N",
        "isVisibleSeatCount": false
      }
    ],
    "casting": [],
    "bookWait": false,
    "bookingEndDate": "202602111700"
  }
]
```

**关键字段说明**:

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `playSeq` | String | 场次编号 | "001", "002", "003" |
| `playTime` | String | 演出时间 | "7:00 PM", "2:00 PM" |
| `seatGrade` | String | 座位等级代码 | "1", "2", "3" |
| `seatGradeName` | String | 座位等级名称 | "R석", "S석", "A석" |
| `remainCount` | Integer | 剩余票数 | 0, 1, 2, ... |
| `salesPrice` | Integer | 票价（韩元） | 143000 |
| `isSeatRemain` | String | 是否有余票 | "Y", "N" |

**当前逻辑**:
```python
# 获取所有场次信息
seats_info = onestop.get_play_seats(...)

# 策略1: 选择第一个场次
selected_play = seats_info[0]
selected_play_seq = selected_play.get('playSeq')  # "001"

# 获取该场次的座位等级列表
available_seats = selected_play.get('seats', [])

# 策略2: 选择第一个有座位的价位
for seat in available_seats:
    if seat.get('remainCount', 0) > 0:  # 如果有余票
        selected_seat = seat
        break
else:
    # 如果都没有余票，选择第一个（用于测试）
    selected_seat = available_seats[0]

seat_grade = selected_seat.get('seatGrade')        # "1"
seat_grade_name = selected_seat.get('seatGradeName')  # "R석"
price_grade = "U1"  # 根据 seatGrade 映射（需要映射表）
```

**seatGrade 到 priceGrade 的映射**:
```python
# 根据 HAR 文件和测试结果
PRICE_GRADE_MAP = {
    "1": "U1",  # R석
    "2": "U1",  # S석
    "3": "U2",  # A석
    "4": "U2",  # B석
    # ... 更多映射
}
```

---

### 步骤 3: 获取座位等级详情

**API**: `/onestop/api/seats/grades`

**请求参数**:
```python
params = {
    'goodsCode': '25018223',
    'placeCode': '25001698',
    'playSeq': selected_play_seq,  # "001"
    'bizCode': '88889'
}
```

**响应**:
```json
[
  {
    "seatExternalType": 0,
    "seatGrade": "1",
    "seatGradeName": "R석",
    "remainCount": 0,
    "salesPrice": 143000,
    "isSacToday": "N",
    "isVisibleSeatCount": false,
    "salesColor": "#7c68ee"  // 座位图颜色
  },
  {
    "seatExternalType": 0,
    "seatGrade": "2",
    "seatGradeName": "S석",
    "remainCount": 0,
    "salesPrice": 132000,
    "isSacToday": "N",
    "isVisibleSeatCount": false,
    "salesColor": "#1ca814"
  }
]
```

**用途**:
- 获取座位等级的颜色信息（用于座位图显示）
- 确认余票数量
- 获取票价信息

---

### 步骤 4: 初始化座位

**API**: `/onestop/api/seats/init/{goodsCode}`

**请求参数**:
```python
params = {
    'goodsGenreType': '1',
    'placeCode': '25001698',
    'playSeq': selected_play_seq,  # "001"
    'seatGrade': '',  // 空字符串表示所有等级
    'bizCode': '88889',
    'seatRenderType': 'D2003',  // 座位渲染类型
    'reserved': 'true',
    'entMemberCode': enc_member_code,
    'sessionId': session_id,
    'kindOfGoods': '01003'  // 商品类型
}
```

**响应**:
```json
{
  "ticketMaxCount": 10,  // 每单最多购买票数
  "isInterlocking": false,
  "connectionMode": "WEBSOCKET"  // 连接模式
}
```

**说明**:
- `ticketMaxCount`: 每单最多可以购买的票数
- `connectionMode: "WEBSOCKET"`: 需要通过 WebSocket 连接获取实时座位图

---

### 步骤 5: WebSocket 座位选择

**WebSocket URL**:
```
wss://tickets.interpark.com/onestop/api/seats/connect/{goodsCode}
```

**连接参数**:
```python
params = {
    'placeCode': '25001698',
    'playSeq': '001',
    'seatGrade': '1',
    'bizCode': '88889',
    'sessionId': session_id,
    'entMemberCode': enc_member_code
}
```

**WebSocket 消息格式**:

1. **订阅座位更新**:
```json
{
  "type": "SUBSCRIBE",
  "topic": "seat:update",
  "playSeq": "001"
}
```

2. **接收座位数据**:
```json
{
  "type": "SEAT_DATA",
  "seats": [
    {
      "seatNo": "A-1-01",      // 座位号
      "seatGrade": "1",        // 座位等级
      "seatGradeName": "R석",  // 座位名称
      "floor": "1층",          // 楼层
      "section": "A구역",       // 区域
      "row": "1열",            // 排
      "number": "1",           // 号
      "price": 143000,         // 价格
      "status": "AVAILABLE",   // 状态: AVAILABLE, SOLD, RESERVED
      "x": 100,                // 座位图 X 坐标
      "y": 200                 // 座位图 Y 坐标
    }
  ]
}
```

3. **选择座位**:
```json
{
  "type": "SELECT_SEAT",
  "seats": [
    {
      "seatNo": "A-1-01",
      "seatGrade": "1",
      "price": 143000
    }
  ]
}
```

---

## 📊 数据结构说明

### 座位数据结构

```python
class SeatInfo:
    """座位信息"""
    play_date: str           # 演出日期 "20260212"
    play_seq: str            # 场次编号 "001"
    play_time: str           # 演出时间 "7:00 PM"

    seat_grade: str          # 座位等级代码 "1"
    seat_grade_name: str     # 座位等级名称 "R석"
    price_grade: str         # 价格等级 "U1"
    price: int               # 价格（韩元） 143000

    remain_count: int        # 剩余数量 0
    is_available: bool       # 是否可用 False

    # 具体座位信息（通过 WebSocket 获取）
    seat_no: str = None      # 座位号 "A-1-01"
    floor: str = None        # 楼层 "1층"
    section: str = None      # 区域 "A구역"
    row: str = None          # 排 "1열"
    number: str = None       # 号 "1"
    status: str = None       # 状态 "AVAILABLE"
```

---

## 🎲 选座策略

### 策略 1: 默认策略（当前实现）

```python
def select_seat_default(seats_info):
    """
    默认选座策略

    规则:
    1. 选择第一个场次
    2. 选择第一个价位（不论是否有余票）
    """
    # 选择第一个场次
    selected_play = seats_info[0]

    # 选择第一个价位
    selected_seat = selected_play['seats'][0]

    return {
        'play_date': selected_play['playDate'],
        'play_seq': selected_play['playSeq'],
        'play_time': selected_play['playTime'],
        'seat_grade': selected_seat['seatGrade'],
        'seat_grade_name': selected_seat['seatGradeName'],
        'price': selected_seat['salesPrice'],
        'remain_count': selected_seat['remainCount']
    }
```

### 策略 2: 优先有余票的座位

```python
def select_seat_available_first(seats_info):
    """
    优先选择有余票的座位

    规则:
    1. 遍历所有场次
    2. 找到第一个有余票的场次
    3. 选择该场次中第一个有余票的价位
    """
    for play in seats_info:
        for seat in play['seats']:
            if seat.get('remainCount', 0) > 0:
                return {
                    'play_date': play['playDate'],
                    'play_seq': play['playSeq'],
                    'play_time': play['playTime'],
                    'seat_grade': seat['seatGrade'],
                    'seat_grade_name': seat['seatGradeName'],
                    'price': seat['salesPrice'],
                    'remain_count': seat['remainCount']
                }

    # 如果都没有余票，返回第一个
    return select_seat_default(seats_info)
```

### 策略 3: 价格优先

```python
def select_seat_price_priority(seats_info, prefer='cheapest'):
    """
    价格优先策略

    Args:
        prefer: 'cheapest' (最便宜) 或 'expensive' (最贵)
    """
    all_seats = []

    for play in seats_info:
        for seat in play['seats']:
            all_seats.append({
                'play': play,
                'seat': seat,
                'price': seat['salesPrice']
            })

    # 按价格排序
    if prefer == 'cheapest':
        all_seats.sort(key=lambda x: x['price'])
    else:  # expensive
        all_seats.sort(key=lambda x: -x['price'])

    # 选择第一个有票的
    for item in all_seats:
        if item['seat']['remainCount'] > 0:
            play = item['play']
            seat = item['seat']
            return {
                'play_date': play['playDate'],
                'play_seq': play['playSeq'],
                'play_time': play['playTime'],
                'seat_grade': seat['seatGrade'],
                'seat_grade_name': seat['seatGradeName'],
                'price': seat['salesPrice'],
                'remain_count': seat['remainCount']
            }

    return None
```

### 策略 4: 用户配置

```python
def select_seat_custom(seats_info, config):
    """
    根据用户配置选择

    Config 示例:
    {
        'preferred_date': '20260212',      # 优先日期
        'preferred_time': '7:00 PM',       # 优先时间
        'preferred_grade': 'R석',          # 优先座位等级
        'max_price': 150000,               # 最高价格
        'min_remain': 1                    # 最少余票
    }
    """
    filtered_plays = []

    for play in seats_info:
        # 过滤日期
        if config.get('preferred_date') and play['playDate'] != config['preferred_date']:
            continue

        # 过滤时间
        if config.get('preferred_time') and play['playTime'] != config['preferred_time']:
            continue

        for seat in play['seats']:
            # 过滤座位等级
            if config.get('preferred_grade') and seat['seatGradeName'] != config['preferred_grade']:
                continue

            # 过滤价格
            if config.get('max_price') and seat['salesPrice'] > config['max_price']:
                continue

            # 过滤余票
            if config.get('min_remain') and seat['remainCount'] < config['min_remain']:
                continue

            filtered_plays.append({
                'play': play,
                'seat': seat
            })

    if filtered_plays:
        selected = filtered_plays[0]
        play = selected['play']
        seat = selected['seat']
        return {
            'play_date': play['playDate'],
            'play_seq': play['playSeq'],
            'play_time': play['playTime'],
            'seat_grade': seat['seatGrade'],
            'seat_grade_name': seat['seatGradeName'],
            'price': seat['salesPrice'],
            'remain_count': seat['remainCount']
        }

    return None
```

---

## 🔌 WebSocket 座位选择

### 连接 WebSocket

```python
import websocket
import json

def connect_seat_websocket(session_id, play_seq, seat_grade, ent_member_code):
    """
    连接座位 WebSocket

    Returns:
        WebSocket 连接对象
    """
    url = f"wss://tickets.interpark.com/onestop/api/seats/connect/25018223"

    params = {
        'placeCode': '25001698',
        'playSeq': play_seq,
        'seatGrade': seat_grade,
        'bizCode': '88889',
        'sessionId': session_id,
        'entMemberCode': ent_member_code
    }

    # 构建完整的 WebSocket URL
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    ws_url = f"{url}?{query_string}"

    # 创建 WebSocket 连接
    ws = websocket.create_connection(ws_url)

    return ws
```

### 订阅座位更新

```python
def subscribe_seat_updates(ws):
    """
    订阅座位更新
    """
    message = {
        "type": "SUBSCRIBE",
        "topic": "seat:update",
        "playSeq": "001"
    }

    ws.send(json.dumps(message))
```

### 接收座位数据

```python
def receive_seat_data(ws):
    """
    接收座位数据

    Returns:
        座位列表
    """
    message = ws.recv()
    data = json.loads(message)

    if data['type'] == 'SEAT_DATA':
        return data['seats']

    return []
```

### 选择座位

```python
def select_seats(ws, seat_list, count=1):
    """
    选择座位

    Args:
        ws: WebSocket 连接
        seat_list: 可选座位列表
        count: 需要选择的座位数量

    Returns:
        选中的座位列表
    """
    # 过滤可用座位
    available_seats = [s for s in seat_list if s['status'] == 'AVAILABLE']

    if len(available_seats) < count:
        raise Exception(f"可用座位不足: 需要 {count}, 可用 {len(available_seats)}")

    # 选择前 N 个座位
    selected = available_seats[:count]

    # 发送选择请求
    message = {
        "type": "SELECT_SEAT",
        "seats": [
            {
                "seatNo": s['seatNo'],
                "seatGrade": s['seatGrade'],
                "price": s['price']
            }
            for s in selected
        ]
    }

    ws.send(json.dumps(message))

    # 接收确认
    response = ws.recv()
    response_data = json.loads(response)

    if response_data.get('status') == 'SUCCESS':
        return selected
    else:
        raise Exception(f"选座失败: {response_data}")
```

---

## 📝 完整API调用顺序

### 标准流程

```
1. GET /onestop/api/play/play-date/{goodsCode}
   → 获取演出日期列表

2. GET /onestop/api/play-seq/play/{goodsCode}
   → 获取场次和座位等级信息

3. GET /onestop/api/seats/grades
   → 获取座位等级详情（颜色、余票）

4. GET /onestop/api/seats/init/{goodsCode}
   → 初始化座位，获取 WebSocket 信息

5. WebSocket Connect
   → 连接 WebSocket，获取实时座位图

6. WebSocket Message (SUBSCRIBE)
   → 订阅座位更新

7. WebSocket Message (SELECT_SEAT)
   → 选择具体座位

8. GET /onestop/api/payment/init-essential/{goodsCode}
   → 初始化支付（获取支付方式、银行列表）

9. GET /onestop/api/payment/init-additional/{goodsCode}
   → 获取额外支付信息（折扣、优惠券）

10. GET /onestop/api/payment/method/interpark-pay/pay-list
    → 获取支付方式列表

11. POST /onestop/api/order/submit
    → 提交订单

12. POST /onestop/api/payment/process
    → 处理支付
```

---

## 🎯 当前实现的选座逻辑总结

### 已实现部分

✅ **步骤 1-4**: API调用流程
- 获取演出日期
- 获取场次和座位信息
- 获取座位等级详情
- 初始化座位

✅ **步骤 8-10**: 支付流程
- 支付初始化
- 获取支付方式
- 生成付款链接

⚠️ **步骤 5-7**: WebSocket选座
- WebSocket连接（未实现）
- 实时座位图获取（未实现）
- 具体座位选择（未实现）

### 当前选座策略

```python
# 简化的选座逻辑（不需要WebSocket）
1. 选择第一个日期: 20260212
2. 选择第一个场次: 001 (7:00 PM)
3. 选择第一个价位: R석 (143,000韩元)
4. 生成付款链接（让用户在网页上具体选座）
```

**优点**:
- 流程简单
- 不需要WebSocket
- 快速生成付款链接

**缺点**:
- 无法预先选择具体座位号
- 用户需要在网页上手动选择座位
- 无法检查具体座位的可用性

### 完整选座逻辑（需要实现）

```python
# 完整的选座逻辑（需要WebSocket）
1. 连接WebSocket
2. 获取实时座位图
3. 根据策略选择具体座位:
   - 优先选择中间位置
   - 避免边缘位置
   - 连续座位优先
4. 锁定座位
5. 进入支付流程
```

---

## 🚀 优化建议

### 1. 增加选座策略配置

```yaml
# config.yaml
seat_selection:
  strategy: "price_priority"  # default, available_first, price_priority, custom

  # 价格优先配置
  price_priority:
    prefer: "cheapest"  # cheapest, expensive

  # 自定义配置
  custom:
    preferred_date: "20260212"
    preferred_time: "7:00 PM"
    preferred_grade: "R석"
    max_price: 150000
    min_remain: 1

  # 座位偏好（WebSocket选座）
  seat_preference:
    priority: "center"  # center, front, back, avoid_edges
    min_distance: 3     # 与边缘的最小距离
    require_contiguous: true  # 是否需要连续座位
```

### 2. 实现WebSocket选座

```python
# 需要实现的功能
1. WebSocket连接管理
2. 座位图解析和显示
3. 智能选座算法
4. 座位锁定和确认
```

### 3. 增加余票监控

```python
def monitor_seat_availability(seats_info, threshold=1):
    """
    监控余票数量

    当余票数量 >= threshold 时发送通知
    """
    for play in seats_info:
        for seat in play['seats']:
            if seat['remainCount'] >= threshold:
                send_notification({
                    'date': play['playDate'],
                    'time': play['playTime'],
                    'grade': seat['seatGradeName'],
                    'price': seat['salesPrice'],
                    'remain': seat['remainCount']
                })
```

---

## 📊 数据流图

```
用户请求
    │
    ▼
获取演出日期 (play-date API)
    │
    ├─→ ["20260212", "20260213", "20260214", "20260215"]
    │
    ▼
选择日期 (配置或默认)
    │
    ▼
获取场次信息 (play-seq API)
    │
    ├─→ 场次001 (7:00 PM)
    │   ├─ R석: 143,000韩元 (余0)
    │   └─ S석: 132,000韩元 (余0)
    │
    ├─→ 场次002 (2:00 PM)
    │   └─ ...
    │
    ▼
选择场次和价位 (策略)
    │
    ▼
初始化座位 (seats/init API)
    │
    ├─→ ticketMaxCount: 10
    ├─→ connectionMode: WEBSOCKET
    │
    ▼
【分支】
    │
    ├─→ 简化模式（当前实现）
    │   │
    │   ▼
    │   生成付款链接
    │   (用户在网页上选择具体座位)
    │
    └─→ 完整模式（需要实现）
        │
        ▼
        WebSocket 连接
        │
        ▼
        获取实时座位图
        │
        ▼
        选择具体座位
        │
        ▼
        锁定座位
        │
        ▼
        进入支付
```

---

## 🎓 总结

### 当前选座逻辑特点

1. **简化流程**: 不使用WebSocket，快速生成付款链接
2. **固定策略**: 默认选择第一个日期、第一个场次、第一个价位
3. **灵活配置**: 可以根据用户需求配置选座策略
4. **实用性强**: 适用于快速抢票场景

### 适用场景

✅ **适合**:
- 快速抢票（速度优先）
- 不在乎具体座位号
- 有余票的情况下

⚠️ **不适合**:
- 需要指定具体座位号
- 需要实时座位图
- 需要智能选座（避开遮挡等）

### 未来优化方向

1. 实现WebSocket选座
2. 增加智能选座算法
3. 支持多座位连选
4. 增加座位偏好配置
5. 实现余票监控和通知

---

**最后更新**: 2026-01-16
**维护者**: ITP Bot Team
