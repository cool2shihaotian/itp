# ITP 购票流程问题分析

**测试时间**: 2026-01-16 10:10
**演出状态**: 开放购买中
**商品代码**: 25018223

---

## ✅ 成功的部分（1-3阶段）

### 阶段1: NOL World 登录 ✅
```
✅ Cloudflare Turnstile 解决成功 (~5s)
✅ Firebase 登录成功
✅ NOL access_token 获取成功
✅ eKYC token 获取成功
用户 ID: _IGl6T2975C7b8f05171faBDd47eD73Bac895758aBf097b6B
```

### 阶段2: 桥接鉴权 ✅
```
✅ Enter token 获取成功
✅ Partner token 已设置为 cookie
```

### 阶段3: Gates 预检 ✅
```
✅ 商品信息获取成功
   - 商品: Sing Again 4 全国巡回演唱会 – 首尔
   - 场馆: 올림픽공원 올림픽홀
   - 演出日期: 20260212 - 20260215
   - bizCode: 61677

✅ 会员信息获取成功
   - Signature: 2c5b2dad53b842db7d2ddfebf293e0...
   - SecureData: 1LfF8KdMI0jqXlBoa8JKpKINzbPvj7...
```

---

## ❌ 问题分析（4-5阶段）

### 问题1: 中间件 Cookie API 失败

**请求**:
```
POST https://tickets.interpark.com/onestop/middleware/set-cookie
Content-Type: application/json

{
  "bizCode": "88889",
  "goodsCode": "25018223"
}
```

**响应**:
```
400 Bad Request
"Request body must be a non-empty string."
```

**分析**:
- ❌ 请求格式可能不正确
- ❌ 可能需要 form data 而不是 JSON
- ❌ 可能需要额外的 headers
- ❌ 可能需要先经过 Waiting 阶段
- ❌ 可能需要特定的 cookie 组合

**可能的解决方案**:
1. 检查实际请求时的 Content-Type
2. 尝试使用 form-data 而不是 JSON
3. 检查是否需要额外的请求头
4. 检查是否需要先调用其他接口

---

### 问题2: 演出日期 API 返回 404

**请求**:
```
GET https://tickets.interpark.com/onestop/api/play/play-date?bizCode=88889&goodsCode=25018223
```

**响应**:
```
404 Not Found
{
  "statusCode": 404,
  "timestamp": "2026-01-16T02:10:46.446Z",
  "path": "/v1/play/play-date?bizCode=88889&goodsCode=25018223"
}
```

**分析**:
- ❌ API 路径可能不正确（响应显示 `/v1/play/play-date`）
- ❌ `bizCode` 可能不正确（使用的是 88889，但 Gates 阶段显示 61677）
- ❌ 可能需要先完成 Waiting 阶段
- ❌ 可能需要特定的 cookie 或 token
- ❌ 可能需要特定的请求顺序

**关键发现**:
```json
// Gates 响应中的 bizCode
"bizCode": "61677"           ← 实际的 bizCode
"reserveBizCode": "10965"    ← Gates 阶段使用的

// 我们尝试使用的
"bizCode": "88889"           ← 可能不正确
```

---

## 🔍 需要的信息

### 1. OneStop API 的实际调用方式

**需要 HAR 文件**，包含：
- OneStop 阶段的完整请求链
- 实际的请求头（headers）
- 实际的请求体格式（JSON vs form-data）
- 实际使用的 API 路径
- 实际的参数值

### 2. bizCode 的使用规则

**问题**:
- Gates 阶段显示多个 bizCode:
  - `bizCode: 61677`
  - `reserveBizCode: 10965`
- OneStop 应该使用哪个？
- Waiting 阶段应该使用哪个？

**需要确认**:
- [ ] 各个阶段的 bizCode 对应关系
- [ ] 是否需要动态获取 bizCode
- [ ] bizCode 的计算规则

### 3. Waiting 阶段的必要性

**疑问**:
- 当前演出是开放购买状态，是否需要 Waiting 阶段？
- OneStop 的 404 错误是否因为跳过了 Waiting？
- 是否必须先通过 Waiting 才能调用 OneStop APIs？

**需要测试**:
- [ ] 尝试调用 Waiting 的 secure-url API
- [ ] 查看 Waiting 阶段返回什么
- [ ] 确认是否必须经过 Waiting

### 4. Cookie 和 Token 的要求

**当前设置的 Cookie**:
```
- access_token (NOL)
- partner_token (Interpark)
- kint5-web-device-id
- refresh_token
- tk-language
```

**OneStop 可能需要的额外 Cookie**:
- [ ] awswaf-token (如需 WAF)
- [ ] session-id
- [ ] 其他中间件设置的 cookie

---

## 💡 建议的调试步骤

### 步骤1: 获取 OneStop HAR 文件
```
在浏览器中：
1. 打开开发者工具 (F12)
2. Network 标签
3. 手动完成从 Gates 到 OneStop 的完整流程
4. 保存 HAR 文件
5. 分享给我分析
```

### 步骤2: 测试 Waiting API
```bash
# 运行 waiting 测试，看看 Waiting 阶段的行为
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_waiting.py
```

### 步骤3: 尝试不同的 bizCode
```python
# 尝试使用 Gates 返回的实际 bizCode
bizCodes = ["61677", "10965", "88889"]
for code in bizCodes:
    # 测试使用不同的 bizCode
    ...
```

### 步骤4: 检查请求格式
```python
# 尝试不同的 Content-Type
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'  # 而不是 application/json
}

# 或者尝试混合格式
headers = {
    'Content-Type': 'multipart/form-data'
}
```

---

## 📊 商品信息详情

从 Gates API 获取的完整商品信息：

```json
{
  "goodsCode": "25018223",
  "goodsName": "Sing Again 4 全国巡回演唱会 – 首尔",
  "goodsStatus": "Y",
  "placeName": "올림픽공원 올림픽홀",
  "playStartDate": "20260212",
  "playEndDate": "20260215",
  "reservedOrNot": "Y",
  "ticketOpenDate": "202512241400",
  "bookingEndDate": "202602141100",
  "goodsQualityList": "Q2033,Q2034,C5015,C5021,C5025,C5025,C5025,C5027",
  "certifyGoodsYN": "Y",
  "bizCode": "61677",              // ← 注意这个
  "reserveBizCode": "10965"        // ← 和这个
}
```

---

## 🎯 关键疑问

### Q1: 是否必须经过 Waiting 阶段？
即使演出是开放购买状态，是否仍需调用 Waiting APIs？

### Q2: OneStop API 的正确路径是什么？
- 当前: `/onestop/api/play/play-date`
- 响应显示: `/v1/play/play-date`
- 正确的是哪个？

### Q3: bizCode 应该使用哪个？
- `61677` (bizCode)
- `10965` (reserveBizCode, Gates使用)
- `88889` (我们假设的 OneStop/Wating code)

### Q4: 中间件 set-cookie 的请求格式
- 当前: JSON 格式
- 错误: "Request body must be a non-empty string"
- 正确格式是什么？

---

## 📝 下一步行动

### 立即可做:
1. ✅ 提供 OneStop 阶段的 HAR 文件
2. ✅ 确认是否需要经过 Waiting 阶段
3. ✅ 提供正确的 bizCode 列表

### 需要调查:
4. 🔲 分析 OneStop API 的实际调用方式
5. 🔲 确认请求格式（JSON vs form-data）
6. 🔲 确认必需的 headers 和 cookies

### 可以尝试:
7. 🔲 运行 test_waiting.py 查看 Waiting 阶段
8. 🔲 尝试使用不同的 bizCode
9. 🔲 尝试不同的请求格式

---

**总结**: 前3个阶段完全正常，OneStop 阶段需要更多的实际流程信息来调试。最需要的是 OneStop 阶段的 HAR 文件，这样可以准确地了解正确的 API 调用方式。
