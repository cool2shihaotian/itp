# 购票流程接口抓包需求

为了实现非排队模式的购票流程，需要以下接口的抓包数据：

## 1. 获取活动列表

**目的**: 搜索和查找演出活动

**需要的信息**:
- Request URL
- Request Method (GET/POST)
- Request Headers
- Request Parameters/Body
- Response 格式示例

**示例场景**:
- 搜索 BTS 或其他演出
- 获取活动详情
- 获取场次列表

---

## 2. 获取座位图

**目的**: 查看场馆布局和座位分布

**需要的信息**:
- Request URL (包含 schedule_code 或类似参数)
- Request Headers
- Response 格式（座位图数据结构）

**示例场景**:
- 选择场次后查看座位图
- 显示各个区域的价格
- 显示座位是否可售

---

## 3. 检查座位可用性

**目的**: 查询特定座位或区域是否可售

**需要的信息**:
- Request URL
- Request Parameters (seat_id, zone_code 等)
- Request Headers
- Response 格式

---

## 4. 预留座位

**目的**: 锁定选中的座位

**需要的信息**:
- Request URL
- Request Method
- Request Headers (需要认证 token)
- Request Body (选中的座位列表)
- Response 格式 (reservation_id 等)

**关键点**:
- 是否需要一次性传递多个座位
- 预留有效期是多长时间
- 是否需要验证码

---

## 5. 提交订单

**目的**: 创建订单并填写购票人信息

**需要的信息**:
- Request URL
- Request Method
- Request Headers
- Request Body (包含护照信息等)
- Response 格式 (order_id, 支付信息等)

**可能需要的字段**:
- 预留 ID (reservation_id)
- 购票人姓名
- 护照号码
- 联系方式

---

## 6. 支付接口

**目的**: 完成支付

**需要的信息**:
- Request URL
- Request Method
- Request Headers
- Request Body (支付信息)
- Response 格式 (支付成功/失败)

**支付信息**:
- 信用卡卡号
- 有效期
- CVV
- 持卡人姓名

---

## 抓包示例格式

请按照以下格式提供抓包数据：

```bash
# 请求示例
curl 'https://world.nol.com/api/xxx' \
  -H 'accept: */*' \
  -H 'authorization: Bearer xxx' \
  -H 'content-type: application/json' \
  --data-raw '{"key":"value"}'

# 响应示例
{
  "status": "success",
  "data": {...}
}
```

---

## 抓包工具使用指南

### 使用 Chrome DevTools
1. 打开 Chrome 浏览器
2. 按 F12 打开开发者工具
3. 切换到 Network 标签页
4. 勾选 "Preserve log"（保留日志）
5. 进行购票操作
6. 找到相关请求，右键 -> Copy -> Copy as cURL

### 推荐抓包时机
- 在访问活动页面时抓取活动列表
- 在选择座位时抓取座位图接口
- 在点击"下一步"或"确认"时抓取订单提交接口
- 在支付页面抓取支付接口

---

## 优先级

如果暂时无法提供所有接口，请按以下优先级提供：

1. ⭐⭐⭐ **座位图接口** - 核心功能
2. ⭐⭐⭐ **预留座位接口** - 核心功能
3. ⭐⭐ **提交订单接口** - 重要
4. ⭐⭐ **活动列表接口** - 重要
5. ⭐ **支付接口** - 可手动完成
