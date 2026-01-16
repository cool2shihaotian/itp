# ITP 购票系统实现状态

**更新时间**: 2026-01-16
**项目**: Interpark Global BTS 演唱会自动购票系统

---

## 📊 总体进度

### ✅ 已完成并可用的模块

| 阶段 | 状态 | 说明 |
|------|------|------|
| **1. NOL World 登录** | ✅ 完成 | Cloudflare → Firebase → NOL Token → eKYC |
| **2. 桥接鉴权** | ✅ 完成 | NOL → Interpark partner_token 获取 |
| **3. Gates 预检** | ✅ 完成 | 商品信息 + 会员信息获取 |
| **4. Waiting 排队** | 🟡 已实现 | 待售票期间测试 (AccessDenied) |
| **5. OneStop 选座** | 🟡 已实现 | 待售票期间测试 (部分接口 404) |

---

## 🎯 已实现的接口清单

### 1. NOL World 阶段 (world.nol.com)

#### 认证流程 ✅
- **Cloudflare Turnstile 验证**
  - 使用 Capsolver API 自动解决
  - 文件: `src/cloudflare.py`
  - 状态: ✅ 测试通过

- **Firebase 身份认证**
  - Endpoint: `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword`
  - 文件: `src/auth.py:67`
  - 状态: ✅ 测试通过

- **NOL Token 获取**
  - Endpoint: `https://auth-web.nol.com/api/users/auth/login/web`
  - 需要参数: `fbToken`, `turnstileToken`
  - 返回: NOL access_token (HS256 JWT)
  - 文件: `src/auth.py:123`
  - 状态: ✅ 测试通过

- **eKYC Token 获取**
  - Endpoint: `https://world.nol.com/api/users/enter/ekyc/token`
  - 文件: `src/auth.py:165`
  - 状态: ✅ 测试通过

#### 商品信息 ✅
- **发售信息获取**
  - Endpoint: `https://world.nol.com/api/ent-channel-out/v1/goods/salesinfo`
  - 文件: `src/event.py:17`
  - 状态: ✅ 测试通过

- **用户入场验证**
  - Endpoint: `https://world.nol.com/api/users/enter`
  - 文件: `src/event.py:48`
  - 状态: ✅ 测试通过

---

### 2. 桥接鉴权阶段 (Bridge)

#### Enter Token 获取 ✅
- **Enter Token API**
  - Endpoint: `https://world.nol.com/api/users/enter/token`
  - 参数: `goods_code`, `place_code`
  - 返回: `access_token` (用作 partner_token)
  - 文件: `src/bridge.py:17`
  - 状态: ✅ 测试通过
  - **关键**: 将 token 设置为 cookie 后才能调用 Gates APIs

#### Token 验证 ⚠️
- **Token Verify API**
  - Endpoint: `https://ent-bridge.interpark.com/x13_02/v1/bridge/tokenVerify`
  - 状态: ❌ 返回 401 (但可跳过，不影响后续流程)

---

### 3. Gates 预检阶段 (tickets.interpark.com)

#### 商品信息 ✅
- **Goods Info API**
  - Endpoint: `https://tickets.interpark.com/api/ticket/v2/reserve-gate/goods-info`
  - 参数: `bizCode`, `goodsCode`, `placeCode`
  - 返回: 商品名称、演出日期、票价信息等
  - 文件: `src/booking.py:24`
  - 状态: ✅ 测试通过
  - 示例响应:
    ```json
    {
      "goodsName": "Sing Again 4 全国巡回演唱会 – 首尔",
      "playDates": [...],
      "goodsQualityList": [...]
    }
    ```

#### 会员信息 ✅
- **Member Info API**
  - Endpoint: `https://tickets.interpark.com/api/ticket/v2/reserve-gate/member-info`
  - 参数: `goodsCode`, `channelCode`
  - 返回: `memberCode`, `signature`, `secureData`, `encMemberCode`
  - 文件: `src/booking.py:78`
  - 状态: ✅ 测试通过
  - **关键参数**:
    - `signature`: 用于 waiting 阶段的签名
    - `secureData`: 用于 waiting 阶段的安全数据
  - 示例响应:
    ```json
    {
      "memberCode": "7PR+QyEAT66qMa3YMmRO8w==",
      "email": "anitasterling759@usualtickets.com",
      "signature": "43643fedd0b1be73fc77...1768527932",
      "secureData": "1LfF8KdMI0jqXlBoa8JKpKINzbPvj7..."
    }
    ```

#### eKYC 认证 ✅
- **eKYC Auth API**
  - Endpoint: `https://tickets.interpark.com/api/ticket/v2/ekyc/auth`
  - 文件: `src/booking.py:117`
  - 状态: ✅ 测试通过

---

### 4. Waiting 排队阶段 (ent-waiting-api.interpark.com) 🟡

> **注意**: 此阶段可能在非售票期间不可用，测试时返回 "AccessDenied"

#### Secure URL 获取 ⚠️
- **Secure URL API**
  - Endpoint: `https://ent-waiting-api.interpark.com/waiting/api/secure-url`
  - 参数: `bizCode`, `secureData`, `signature`
  - 返回: `secureUrl`, `key`
  - 文件: `src/waiting.py:18`
  - 状态: ⚠️ 返回 400 AccessDenied (非售票期间)

#### AWS WAF 挑战 🔧
- **WAF Token 解决**
  - 文件: `src/waiting.py:93`
  - 状态: 🔧 待实现 (某些情况下可能不需要)

#### 排队进入 ⚠️
- **Line Up API**
  - Endpoint: `https://ent-waiting-api.interpark.com/waiting/api/line-up`
  - 参数: `bizCode`, `key`, `platform`
  - 返回: `waitingId`
  - 文件: `src/waiting.py:123`
  - 状态: ⚠️ 待售票期间测试

#### 排队轮询 ⚠️
- **Rank API**
  - Endpoint: `https://ent-waiting-api.interpark.com/waiting/api/rank`
  - 参数: `bizCode`, `waitingId`
  - 返回: `status`, `rank`
  - 文件: `src/waiting.py:175`
  - 状态: ⚠️ 待售票期间测试

---

### 5. OneStop 选座阶段 (tickets.interpark.com) 🟡

> **注意**: 部分接口在非售票期间返回 404

#### 中间件 Cookie ⚠️
- **Set Cookie API**
  - Endpoint: `https://tickets.interpark.com/onestop/middleware/set-cookie`
  - 参数: `bizCode`, `goodsCode`
  - 文件: `src/onestop.py:18`
  - 状态: ⚠️ 返回 400 "Request body must be a non-empty string"
  - 可能原因: Content-Type 或请求格式问题

#### 演出日期 ⚠️
- **Play Date API**
  - Endpoint: `https://tickets.interpark.com/onestop/api/play/play-date`
  - 参数: `bizCode`, `goodsCode`
  - 返回: 演出日期列表
  - 文件: `src/onestop.py:61`
  - 状态: ⚠️ 返回 404 (活动可能未开始售票)

#### 会话检查 🔧
- **Session Check API**
  - Endpoint: `https://tickets.interpark.com/onestop/api/session-check`
  - 参数: `bizCode`, `goodsCode`, `playSeq`
  - 文件: `src/onestop.py:93`
  - 状态: 🔧 待售票期间测试

#### 座位信息 🔧
- **Play Seats API**
  - Endpoint: `https://tickets.interpark.com/onestop/api/play-seq/play/{goodsCode}/{playSeq}`
  - 参数: `bizCode`
  - 返回: 座位图数据
  - 文件: `src/onestop.py:133`
  - 状态: 🔧 待售票期间测试

#### 座位预留 🔧
- **Reserve Seats API**
  - Endpoint: `https://tickets.interpark.com/onestop/api/seat/reserve`
  - 参数: `bizCode`, `goodsCode`, `seats`
  - 返回: 预留结果
  - 文件: `src/onestop.py:173`
  - 状态: 🔧 待售票期间测试

---

## 🧪 测试脚本

| 文件 | 功能 | 状态 |
|------|------|------|
| `src/test_login.py` | 测试 NOL 登录流程 | ✅ 通过 |
| `src/test_event.py` | 测试 NOL 商品和用户信息 | ✅ 通过 |
| `src/test_bridge.py` | 测试桥接鉴权 + Gates APIs | ✅ 通过 |
| `src/test_booking.py` | 测试 Gates 预检接口 | ✅ 通过 |
| `src/test_waiting.py` | 测试排队系统 | ⚠️ 待售票期间 |
| `src/test_full_flow.py` | 完整流程测试 | ✅ 前3阶段通过 |

---

## 📁 项目结构

```
itp/
├── config.yaml              # 配置文件
├── src/
│   ├── __init__.py
│   ├── api_config.py        # API 配置
│   ├── client.py            # HTTP 客户端
│   ├── utils.py             # 工具函数
│   ├── cloudflare.py        # Cloudflare Turnstile 验证 (Capsolver)
│   ├── aws_waf.py           # AWS WAF 验证 (Capmonster) 🆕
│   ├── auth.py              # 认证管理
│   ├── event.py             # NOL 事件接口
│   ├── bridge.py            # 桥接鉴权
│   ├── booking.py           # Gates 预检
│   ├── waiting.py           # 排队系统 (已集成 Capmonster)
│   ├── onestop.py           # 选座系统
│   ├── test_login.py        # 登录测试
│   ├── test_event.py        # 事件测试
│   ├── test_bridge.py       # 桥接测试
│   ├── test_booking.py      # 预订测试
│   ├── test_waiting.py      # 排队测试
│   └── test_full_flow.py    # 完整流程测试
└── docs/
    ├── QUICK_START.md
    ├── CAPSOLVER_SETUP.md
    ├── CAPMONSTER_SETUP.md   # Capmonster 配置指南 🆕
    ├── TESTING_GUIDE.md
    └── API_DATA_NEEDED.md
```

---

## ⚙️ 配置说明

### config.yaml

```yaml
account:
  username: "your@email.com"
  password: "yourpassword"

# Cloudflare Turnstile 验证（NOL 登录）
capsolver:
  enabled: true
  api_key: "CAP-CDE2A2417E7D3BBBED64716B48C16CFA"

# AWS WAF 验证（Waiting 排队阶段）
capmonster:
  enabled: false  # 根据需要启用
  api_key: ""  # 从 https://capmonster.com 获取
  use_proxy: false

event:
  goods_code: "25018223"
  place_code: "25001698"
  biz_code_gates: "10965"
  biz_code_onestop: "88889"

seat_preferences:
  ticket_count: 2
  priority_sections:
    - "VIP"
    - "R"
    - "S"
  max_price: 200000
```

### 验证码服务配置

#### Capsolver（Cloudflare Turnstile）
- **用途**: 解决 NOL World 登录时的 Cloudflare 验证
- **获取**: https://capsolver.com
- **文档**: `docs/CAPSOLVER_SETUP.md`
- **费用**: ~$0.0008/次
- **配置**: `capsolver.api_key`

#### Capmonster（AWS WAF）
- **用途**: 解决 Waiting 阶段的 AWS WAF 挑战
- **获取**: https://capmonster.com
- **文档**: `docs/CAPMONSTER_SETUP.md`
- **费用**: ~$0.002/次
- **配置**: `capmonster.api_key`
- **状态**: 🆕 新增功能

---

## 🔑 关键发现和解决方案

### 1. NOL Token 格式
**问题**: 使用 Firebase token 调用 NOL API 返回 401
**解决**: 发现需要专门的登录接口 (`auth-web/api/users/auth/login/web`)，传入 `fbToken` 和 `turnstileToken` 获取 NOL access_token

### 2. Partner Token Cookie
**问题**: 调用 Gates APIs 返回 401
**解决**: 必须将 bridge 获取的 `partner_token` 设置为 cookie: `client.set_cookie('partner_token', token)`

### 3. Signature 和 SecureData
**问题**: Waiting 和 OneStop 阶段需要额外认证参数
**解决**: 从 `member-info` API 响应中提取:
- `signature`: 格式 `"hash.timestamp"`
- `secureData`: Base64 编码的安全数据

### 4. 非售票期间的 API 行为
**问题**: Waiting 和 OneStop APIs 在非售票期间返回错误
**说明**:
- Waiting API: 返回 `400 AccessDenied`
- OneStop APIs: 部分返回 `404 Not Found`
- 这属于正常行为，实际售票时应可正常调用

---

## 🚀 下一步工作

### 需要在实际售票期间测试

1. **Waiting 排队系统**
   - 测试 `secure-url` API
   - 实现 AWS WAF 挑战解决（如需要）
   - 测试 `line-up` 和 `rank` 轮询

2. **OneStop 选座系统**
   - 修复 `set-cookie` API 的请求格式问题
   - 获取实际的演出日期和场次
   - 解析座位图数据
   - 实现自动选座逻辑
   - 测试座位预留功能

3. **订单和支付**
   - 实现订单提交 API
   - 填写购票人信息
   - 实现支付接口（或保留手动支付）

### 代码优化

1. **错误处理**
   - 添加更详细的错误信息
   - 实现重试机制
   - 添加超时控制

2. **配置化**
   - 将 API endpoints 完全配置化
   - 支持多商品配置
   - 添加环境变量支持

3. **日志和监控**
   - 添加请求/响应日志
   - 实现性能监控
   - 添加统计功能

---

## 📝 测试命令

```bash
# 测试登录
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_login.py

# 测试桥接鉴权
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_bridge.py

# 测试完整流程
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_full_flow.py
```

---

## ✅ 成功标志

当前已成功实现并测试:
- ✅ 完整的 NOL World 登录流程
- ✅ NOL → Interpark 桥接鉴权
- ✅ Gates 预检阶段（商品信息、会员信息、eKYC）
- ✅ 获取签名和安全数据（用于后续阶段）
- ✅ Waiting 和 OneStop 模块代码实现
- ✅ AWS WAF 解决模块（Capmonster 集成）🆕

**待售票期间验证**:
- ⏳ Waiting 排队系统实际调用（已集成 Capmonster）
- ⏳ OneStop 选座系统实际调用
- ⏳ 座位预留和订单提交流程

---

## 🆕 更新日志

### 2026-01-16 - Capmonster 集成
- ✅ 添加 Capmonster AWS WAF 解决支持
- ✅ 创建 `src/aws_waf.py` 模块
- ✅ 更新 `src/waiting.py` 集成 Capmonster
- ✅ 更新 `config.yaml` 添加 capmonster 配置项
- ✅ 创建 `docs/CAPMONSTER_SETUP.md` 配置指南
- ✅ 支持 AWSWafTaskProxyLess 和 AWSWafTask 两种任务类型
- ✅ 自动设置 WAF token cookie

**使用方法**:
1. 注册 Capmonster 账号并获取 API Key
2. 在 `config.yaml` 中设置 `capmonster.enabled: true`
3. 配置 `capmonster.api_key`
4. 运行测试或完整流程，系统会自动使用 Capmonster 解决 AWS WAF

---

**备注**: 当前实现已完成核心架构和前3个阶段的测试，第4、5阶段的代码已实现但需要在实际售票期间进行验证。
