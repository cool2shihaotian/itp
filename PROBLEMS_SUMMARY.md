# 🔴 ITP 购票系统问题总结

**测试时间**: 2026-01-16 10:10-10:11
**演出状态**: 开放购买中
**结果**: ✅ 前3阶段成功，❌ 后2阶段失败

---

## ✅ 工作正常的部分（1-3阶段）

### 阶段1: NOL World 登录 ✅ 100%
```
✅ Cloudflare Turnstile (Capsolver) - ~5秒
✅ Firebase Authentication
✅ NOL Token (HS256 JWT)
✅ eKYC Token
```

### 阶段2: 桥接鉴权 ✅ 100%
```
✅ Enter Token 获取
✅ Partner Token Cookie 设置
```

### 阶段3: Gates 预检 ✅ 100%
```
✅ Goods Info API
   - 商品: Sing Again 4 全国巡回演唱会 – 首尔
   - 场馆: 올림픽공원 올림픽홀
   - 演出日期: 20260212-20260215
   - bizCode: 61677
   - reserveBizCode: 10965

✅ Member Info API
   - signature: c336945a0809c89fb1cf...
   - secureData: 1LfF8KdMI0jqXlBoa8JK...
```

---

## ❌ 问题部分（4-5阶段）

### 阶段4: Waiting 排队 ❌

#### 问题4.1: secure-url API 返回 AccessDenied

**请求**:
```http
POST https://ent-waiting-api.interpark.com/waiting/api/secure-url
Content-Type: application/json

{
  "bizCode": "88889",
  "secureData": "1LfF8KdMI0jqXlBoa8JKpKINzbPvj7GNNIjjNtgWg+7dz1vMEacB0gBBuGnhYW26Csjr8h7bMndDHfzYpz7lQY4+/3Egae3c23k9hc/aKz0CkeVwOUoakc6lCB3rfPD4i3Qx/yLgNpoqynanhHTe45/yuwY0vALmwMmU4AMQ0JQ=",
  "signature": "c336945a0809c89fb1cff0a65224af0f013bfa86cb295b6399d7d0aad21be069.1768529498",
  "goodsCode": "25018223"
}
```

**响应**:
```json
400 Bad Request
{
  "error": "AccessDenied"
}
```

**可能原因**:
1. ❌ `bizCode: 88889` 不正确（应该使用 61677？）
2. ❌ 演出不是热门演出，不需要排队
3. ❌ 请求格式不正确
4. ❌ 缺少必要的 headers 或 cookies
5. ❌ Waiting API 只在特定条件下启用

---

### 阶段5: OneStop 选座 ❌

#### 问题5.1: 中间件 set-cookie API 返回 400

**请求**:
```http
POST https://tickets.interpark.com/onestop/middleware/set-cookie
Content-Type: application/json

{
  "bizCode": "88889",
  "goodsCode": "25018223"
}
```

**响应**:
```http
400 Bad Request
"Request body must be a non-empty string."
```

**可能原因**:
1. ❌ Content-Type 应该是 `application/x-www-form-urlencoded`
2. ❌ 请求体格式应该是 form-data 而不是 JSON
3. ❌ 缺少必要的参数
4. ❌ 缺少必要的 headers

#### 问题5.2: play-date API 返回 404

**请求**:
```http
GET https://tickets.interpark.com/onestop/api/play/play-date?bizCode=88889&goodsCode=25018223
```

**响应**:
```json
404 Not Found
{
  "statusCode": 404,
  "timestamp": "2026-01-16T02:10:46.446Z",
  "path": "/v1/play/play-date?bizCode=88889&goodsCode=25018223"
}
```

**可能原因**:
1. ❌ API 路径错误（响应显示 `/v1/play/play-date`）
2. ❌ `bizCode: 88889` 不正确
3. ❌ 必须先完成 Waiting 阶段
4. ❌ 缺少必要的 cookies（如中间件设置的）
5. ❌ goodsCode 不正确或演出不可用

---

## 🎯 关键发现

### 发现1: bizCode 混乱

从 Goods Info API 响应中看到：
```json
{
  "bizCode": "61677",        // ← 实际 bizCode
  "reserveBizCode": "10965"   // ← Gates 使用
}
```

但我们在使用：
```python
biz_code_gates = "10965"      # ✅ 正确
biz_code_waiting = "88889"    # ❌ 可能不正确
biz_code_onestop = "88889"    # ❌ 可能不正确
```

**问题**:
- ❌ 88889 是从哪里来的？
- ✅ Gates 使用 10965 正确
- ❌ Waiting 和 OneStop 应该使用哪个？

### 发现2: Waiting 可能不可用

返回 `AccessDenied` 说明：
- ✅ API 存在（不是 404）
- ❌ 但拒绝访问

**可能性**:
1. 演出不是热门演出，不需要排队
2. 当前时段不需要排队
3. 排队未开启
4. 请求参数不正确

### 发现3: OneStop 依赖关系

OneStop APIs 失败可能是因为：
1. ❌ 没有完成 Waiting 阶段
2. ❌ 没有 set-cookie 中间件
3. ❌ bizCode 不正确
4. ❌ 请求格式不正确

---

## 🔍 需要您提供的信息

### 优先级1: HAR 文件（最重要）

**需要的 HAR 文件**:
```
1. Gates → OneStop 的完整流程 HAR
   - 包含所有 OneStop API 调用
   - 包含请求和响应的完整格式

2. Waiting 阶段 HAR（如果有排队）
   - 包含 secure-url 调用
   - 包含 line-up 调用
```

**如何获取**:
```
1. Chrome 浏览器打开购票页面
2. F12 → Network 标签
3. 勾选 "Preserve log"
4. 完成一次手动购票流程
5. 右键 → Save all as HAR
```

### 优先级2: bizCode 信息

**问题**:
- [ ] 各个阶段使用的 bizCode 分别是什么？
- [ ] 是否需要从 API 响应中动态获取？
- [ ] 88889 这个值是从哪里来的？

**已知信息**:
```python
Gates 阶段:      bizCode = "10965"  (reserveBizCode) ✅
Goods Info:      bizCode = "61677"  (bizCode)
Waiting 阶段:    bizCode = "88889"  (???)
OneStop 阶段:    bizCode = "88889"  (???)
```

### 优先级3: 请求格式确认

**需要确认**:
```
1. OneStop APIs 使用 JSON 还是 form-data？
2. set-cookie API 的正确请求格式是什么？
3. 是否需要特殊的 headers？
4. 是否需要特定的 cookies？
```

---

## 💡 建议的调查方向

### 方向1: 使用正确的 bizCode

**尝试**:
```python
# 在 test_onestop.py 中尝试
bizCodes = ["61677", "10965", "88889"]

for code in bizCodes:
    print(f"测试 bizCode: {code}")
    # 尝试调用 OneStop APIs
```

### 方向2: 检查是否必须经过 Waiting

**尝试**:
```bash
# 手动在浏览器中查看：
1. 该演出是否有排队？
2. 是否直接进入 OneStop？
3. Waiting 是否只在特定时段启用？
```

### 方向3: 分析 OneStop 请求格式

**尝试**:
```python
# 修改 onestop.py 中的请求格式
# 1. 尝试 form-data 而不是 JSON
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

# 2. 尝试不同的参数格式
data = f"bizCode={biz_code}&goodsCode={goods_code}"
```

### 方向4: 查看实际流程

**建议**:
```
手动在浏览器中完成一次选座流程：
1. 观察 Network 面板
2. 记录所有 API 调用
3. 查看请求和响应格式
4. 特别注意：
   - bizCode 的值
   - Content-Type
   - 请求体格式
   - Cookie 的变化
```

---

## 📊 当前系统状态

### 可以正常使用的功能 ✅
- ✅ 自动登录（NOL + Firebase + Cloudflare）
- ✅ 桥接鉴权（获取 partner_token）
- ✅ 商品信息查询
- ✅ 会员信息查询
- ✅ Signature 和 SecureData 获取

### 需要修复的功能 ❌
- ❌ Waiting 排队系统
- ❌ OneStop 选座系统
- ❌ 座位预留
- ❌ 订单提交

---

## 🎯 下一步行动

### 您需要做的:
1. 🔲 **提供 OneStop HAR 文件**（最重要）
2. 🔲 **确认 bizCode 的正确值**
3. 🔲 **确认是否必须经过 Waiting**
4. 🔲 **提供一次手动购票的 Network 日志**

### 我可以做的:
1. 🔲 分析 HAR 文件，找出正确的 API 格式
2. 🔲 根据实际流程调整代码
3. 🔲 尝试不同的 bizCode 组合
4. 🔲 测试不同的请求格式

---

## ❓ 疑问清单

### 关于 bizCode:
- [Q1] 88889 这个值是从哪里获取的？
- [Q2] OneStop 应该使用 61677 还是 10965？
- [Q3] 是否需要从 API 响应中动态获取？

### 关于流程:
- [Q4] 开放购买状态下是否需要 Waiting？
- [Q5] Waiting 只在特定条件下启用吗？
- [Q6] OneStop 是否依赖 Waiting 的结果？

### 关于格式:
- [Q7] set-cookie API 的正确格式是什么？
- [Q8] OneStop APIs 使用 JSON 还是 form-data？
- [Q9] 是否需要额外的 headers 或 cookies？

---

**总结**: 核心问题在于缺少 OneStop 阶段的实际 API 调用信息。最紧急需要的是 OneStop 流程的 HAR 文件，这样我可以准确地修复 API 调用格式。
