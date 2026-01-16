# Interpark 完整付款流程实现总结

## 📋 项目概述

基于你的 HAR 文件分析，我实现了完整的 Interpark 选座和付款流程。这个实现包含了从座位轮询到支付完成的所有步骤。

---

## 🎯 核心功能

### 1. **轮询选座**（基于真实座位状态）

- **接口 1**: `GET /onestop/api/seats/block-data`
  - 获取所有区域代码（26 个区域）

- **接口 2**: `GET /onestop/api/seatMeta`
  - 获取真实座位状态
  - **关键字段**: `isExposable`（true = 可售）
  - 替代之前不准确的 `remainCount`

### 2. **完整付款流程**（5 个步骤）

#### 步骤 1: 预选座位
```
POST /onestop/api/seats/preselect
```
**功能**: 通过 WebSocket 锁定座位

**请求体**:
```json
{
  "blockKey": "001:401",
  "goodsCode": "25018223",
  "placeCode": "25001698",
  "playSeq": "001",
  "seatInfoId": "25018223:25001698:001:2500",
  "sessionId": "25018223_M0000000755191768541435"
}
```

#### 步骤 2: 确认选座
```
POST /onestop/api/seats/select
```
**功能**: 确认座位选择

**请求体**:
```json
{
  "goodsCode": "25018223",
  "placeCode": "25001698",
  "playSeq": "001",
  "seatType": "DEFAULT",
  "seats": [
    {
      "seatGrade": "1",
      "seatInfoId": "25018223:25001698:001:2500"
    }
  ],
  "seatCount": 1,
  "sessionId": "25018223_M0000000755191768541435"
}
```

#### 步骤 3: 准备付款
```
POST /onestop/api/payment/ready/25018223
```
**功能**: 生成购物车 ID（cartID + cartIDSeq）

**关键字段**:
- `paymentInfo`: 支付方式（信用卡: 22003, Eximbay: VN005）
- `deliveryInfo`: 配送信息（取票人姓名、手机、邮箱）
- `priceInfo`: 价格信息（价格等级、票价）
- `seatInfo`: 座位信息

**响应**:
```json
{
  "cartID": "20260116",
  "cartIDSeq": "3Q950"
}
```

#### 步骤 4: 请求支付
```
POST /onestop/api/payment/method/eximbay/request
```
**功能**: 获取支付加密密钥（fgkey）

**关键参数**:
- `correlationId`: cartID + cartIDSeq（如: "202601163Q950"）
- `amount`: 总金额（含手续费）
- `payMethod`: "CARD_ONESTOP"

**响应**:
```json
{
  "fgkey": "D18BAC9477322E0D3849CAC8134D96E7A85DFC5D80C152B156EA2506530680B6",
  "payment": {
    "order_id": "O19bc54aa59617de"
  }
}
```

#### 步骤 5: 生成支付链接
```
返回支付链接: https://tickets.interpark.com/onestop/payment/eximbay?fgkey={fgkey}
```

---

## 📁 新增文件

### 1. `src/payment_flow.py`
完整的付款流程实现类 `InterparkPaymentFlow`

**主要方法**:
- `preselect_seat()`: 预选座位
- `select_seat()`: 确认选座
- `ready_payment()`: 准备付款
- `request_eximbay_payment()`: 请求支付
- `get_payment_url()`: 生成支付链接
- `execute_full_flow()`: 执行完整流程

### 2. `src/test_full_payment_flow.py`
测试脚本，演示完整的付款流程

### 3. `/Users/shihaotian/Downloads/interpark_api_params.json`
所有 API 的完整参数模板（从 HAR 文件提取）

---

## 🔧 修改的文件

### `src/polling_seat_selector.py`

**新增方法**:
- `get_block_keys()`: 获取所有区域代码
- `get_real_seat_availability()`: 获取真实座位状态（基于 seatMeta）

**更新方法**:
- `poll_and_select()`: 使用 seatMeta 接口进行轮询
- `quick_purchase()`: 集成完整付款流程

**删除方法**:
- `reserve_seat()`: 旧的预留方法（已被完整流程替代）

---

## 🚀 使用方法

### 方式 1: 使用轮询选座器（推荐）

```python
from src.polling_seat_selector import PollingSeatSelector

# 初始化
polling_selector = PollingSeatSelector(client, config, logger)

# 开始轮询
selected_seat = polling_selector.poll_and_select(
    onestop=onestop,
    play_date='20260212',
    session_id=session_id,
    member_info=member_info,
    poll_interval=3,  # 每 3 秒轮询一次
    timeout=300,      # 最多轮询 5 分钟
    max_price=150000  # 最高价格 150,000 韩元
)

# 执行完整付款流程
if selected_seat:
    payment_url = polling_selector.quick_purchase(
        selected_seat=selected_seat,
        session_id=session_id,
        member_info=member_info,
        use_full_flow=True  # 使用完整付款流程
    )

    print(f"支付链接: {payment_url}")
```

### 方式 2: 直接使用付款流程

```python
from src.payment_flow import InterparkPaymentFlow

# 初始化
payment_flow = InterparkPaymentFlow(client, config, logger)

# 执行完整流程
payment_url = payment_flow.execute_full_flow(
    selected_seat=selected_seat,
    session_id=session_id,
    member_info=member_info
)

print(f"支付链接: {payment_url}")
```

### 方式 3: 运行测试脚本

```bash
cd /Users/shihaotian/Desktop/edison/itp
python src/test_full_payment_flow.py
```

---

## 📊 数据流关键点

### 1. **seatInfoId**（座位唯一标识）
```
格式: {goodsCode}:{placeCode}:{playSeq}:{seatCode}
示例: 25018223:25001698:001:2500
```

### 2. **sessionId**（会话 ID）
```
格式: {goodsCode}_{memberNo}
示例: 25018223_M0000000755191768541435

⚠️ 在整个流程中必须保持不变
```

### 3. **correlationId**（关联 ID）
```
格式: {cartID}{cartIDSeq}
生成: 从 payment/ready 响应中获取
用途: 关联支付订单
```

### 4. **fgkey**（支付密钥）
```
来源: eximbay/request 响应
用途: 传递给 Eximbay 支付网关
```

### 5. **金额计算**
```
totalFee = salesPrice + commissionFee
示例: 143000 + 8000 = 151000 韩元
```

---

## ⚠️ 重要注意事项

### 1. **参数格式**
- `seatInfoId` 格式必须正确
- `sessionId` 在整个流程中保持一致
- `traceId` 每次请求都需要新生成

### 2. **金额一致性**
- `totalFee` 必须等于 `salesPrice + commissionFee`
- 所有支付相关 API 的金额必须一致

### 3. **时序要求**
- `preselect` → `select` 应快速连续（间隔 < 2 秒）
- 座位锁定有时间限制，需尽快完成支付

### 4. **错误处理**
- 如果 `preselect` 失败，可能座位已被售出
- 如果 `select` 失败，可能座位被其他人抢走
- 需要重新轮询获取新的可售座位

---

## 🎯 下一步建议

### 1. **测试轮询功能**
```bash
python src/test_polling_seat.py
```

### 2. **测试完整付款流程**
```bash
python src/test_full_payment_flow.py
```

### 3. **监控和日志**
- 所有操作都有详细日志记录
- 日志文件位于 `/Users/shihaotian/Desktop/edison/itp/logs/`

### 4. **配置文件**
确保 `config.yaml` 包含正确的账号信息：
```yaml
interpark:
  username: your_email@example.com
  password: your_password
```

---

## 📝 代码文件结构

```
itp/
├── src/
│   ├── payment_flow.py              # ⭐ 新增：完整付款流程
│   ├── polling_seat_selector.py     # ✏️ 更新：集成付款流程
│   ├── test_full_payment_flow.py    # ⭐ 新增：测试脚本
│   ├── auth.py
│   ├── client.py
│   ├── onestop.py
│   └── ...
└── IMPLEMENTATION_SUMMARY.md        # 本文档
```

---

## ✅ 完成状态

- [x] 分析 HAR 文件，提取所有 API 参数
- [x] 创建 InterparkPaymentFlow 类
- [x] 实现 5 个步骤的完整付款流程
- [x] 更新 PollingSeatSelector 集成付款流程
- [x] 创建测试脚本
- [x] 文档编写

---

## 🎉 总结

现在你有了一个完整的 Interpark 轮询选座和付款系统！

**核心优势**:
1. ✅ 使用真实的 `seatMeta` 接口检测座位状态
2. ✅ 完整的 5 步付款流程（基于 HAR 文件分析）
3. ✅ 自动轮询监控，有票立即锁定
4. ✅ 详细的日志记录和错误处理
5. ✅ 灵活的配置选项

**开始使用**:
```bash
cd /Users/shihaotian/Desktop/edison/itp
python src/test_full_payment_flow.py
```

祝购票顺利！🎫
