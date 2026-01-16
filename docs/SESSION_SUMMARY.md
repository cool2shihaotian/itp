# ITP 自动购票程序 - 项目总结

## 项目概述

**目标**: 开发一个自动购票程序，用于在 Interpark Global (NOL) 购买 BTS 演唱会门票

**用户背景**: 演唱会爱好者，程序小白，有基础代码知识

**技术栈**: Python + 纯 requests 实现（不使用 Selenium）

---

## 项目位置

```
/Users/shihaotian/Desktop/edison/itp
```

---

## 已完成的工作

### 1. 项目基础架构 ✅

**创建的文件结构**:
```
itp/
├── config.yaml              # 配置文件
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
├── README.md               # 项目说明
├── .gitignore              # Git 忽略文件
├── src/                    # 源代码
│   ├── __init__.py
│   ├── main.py            # 主程序入口
│   ├── client.py          # HTTP 客户端封装
│   ├── auth.py            # 登录认证模块
│   ├── cloudflare.py      # Cloudflare 验证解决
│   ├── ticket.py          # 购票核心逻辑（待实现）
│   ├── seat.py            # 座位选择模块（待实现）
│   ├── payment.py         # 支付模块（待实现）
│   ├── api_config.py      # API 配置
│   ├── utils.py           # 工具函数
│   └── test_login.py      # 登录测试脚本
├── docs/                   # 文档
│   ├── QUICK_START.md              # 快速开始指南
│   ├── TESTING_GUIDE.md            # 测试指南
│   ├── CLOUDFLARE_SOLUTIONS.md     # Cloudflare 解决方案
│   ├── CAPSOLVER_SETUP.md          # Capsolver 配置指南
│   └── API_DATA_NEEDED.md          # 接口数据需求
├── logs/                   # 日志目录
├── tests/                  # 测试文件
├── captures/               # 抓包数据存放
└── screenshots/            # 页面截图存放
```

### 2. 购票流程分析 ✅

**ITP 购票流程**:
1. 注册账号
2. 会员认证（WEVERSE membership，预售需要）
3. 排队（热门场次需要）
4. 选择区域和座位
5. 填写护照信息和信用卡
6. 支付

### 3. 登录功能实现 ✅

**已实现的功能**:
- Cloudflare Turnstile 验证（通过 Capsolver）
- Firebase Authentication 登录
- eKYC token 获取
- Session 和 Cookie 管理
- 设备 ID 生成

**关键接口**:
- Cloudflare: `https://challenges.cloudflare.com/cdn-cgi/challenge-platform/...`
- Firebase 登录: `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyDi1DsEgLRDaWDI2aF7WerqKLqcD5HC8V4`
- eKYC token: `https://world.nol.com/api/users/enter/ekyc/token`

**测试结果**: ✅ 登录成功
- 用户 ID: `_IGl6T2975C7b8f05171faBDd47eD73Bac895758aBf097b6B`
- Cloudflare 验证: ~4秒解决
- Capsolver 费用: ~$0.002-0.003/次

### 4. Capsolver 集成 ✅

**配置信息**:
- 服务商: Capsolver (https://capsolver.com)
- API Key: `CAP-CDE2A2417E7D3BBBED64716B48C16CFA`
- 已启用: true

**代码实现**:
- `src/cloudflare.py` - Capsolver 客户端和 Cloudflare solver
- 集成到 `src/auth.py` 登录流程中

### 5. 配置文件 ✅

**当前配置** (`config.yaml`):
```yaml
account:
  username: "AnitaSterling759@usualtickets.com"
  password: "Aa123490@"

event:
  event_code: ""      # 待获取
  schedule_code: ""   # 待获取

capsolver:
  api_key: "CAP-CDE2A2417E7D3BBBED64716B48C16CFA"
  enabled: true

payment:
  passport_number: ""
  card_number: ""
  expiry_date: ""
  card_type: "visa"
```

---

## 待实现的功能

### 优先级 1: 核心购票功能 ⭐⭐⭐

**需要以下接口的抓包数据**:

1. **获取座位图接口**
   - 查看场馆布局
   - 获取区域和座位信息
   - 获取价格信息

2. **预留座位接口**
   - 锁定选中的座位
   - 获取 reservation_id

3. **提交订单接口**
   - 填写购票人信息
   - 生成订单号

### 优先级 2: 辅助功能 ⭐⭐

4. **获取活动列表接口**
   - 搜索演出活动
   - 获取场次信息

5. **支付接口**
   - 完成支付
   - 获取支付结果

### 优先级 3: 增强功能 ⭐

6. **排队逻辑**（可选，当前先实现非排队模式）
7. **会员认证**（WEVERSE membership，预售需要）
8. **多账号支持**
9. **定时抢票**

---

## 关键技术点

### 1. 认证机制

**Firebase Authentication**
- API Key: `AIzaSyDi1DsEgLRDaWDI2aF7WerqKLqcD5HC8V4`
- 返回: idToken (access_token), refreshToken, localId (user_id)

**Cloudflare Turnstile**
- 验证方式: Capsolver AI 解决
- 费用: ~$0.002-0.003/次
- 响应时间: 10-30秒

**eKYC Token**
- 用途: 可能用于会员认证或支付验证
- 当前状态: 获取失败（401），需要进一步调查

### 2. 关键 Headers

```python
# Firebase 登录
'Content-Type': 'application/json'
'Origin': 'https://world.nol.com'
'x-browser-year': '2026'
'x-client-version': 'Chrome/JsCore/11.10.0/FirebaseCore-web'
'x-firebase-gmpid': '1:182595350393:web:0a10fb747ba6a5922d89a8'

# NOL API
'x-service-origin': 'global'
```

### 3. Cookie 管理

**重要 Cookies**:
- `access_token`: JWT token，用于 API 认证
- `refresh_token`: 刷新 token
- `kint5-web-device-id`: 设备 ID
- `tk-language`: 语言设置

---

## 下次沟通的重点

### 1. 提供抓包数据

**最关键的三个接口**:
1. 获取座位图 (seat map)
2. 预留座位 (reserve seats)
3. 提交订单 (submit order)

**抓包方法**:
```bash
# Chrome DevTools
1. F12 打开开发者工具
2. Network 标签
3. 勾选 "Preserve log"
4. 进行购票操作
5. 右键请求 → Copy → Copy as cURL
```

### 2. 确认功能需求

- 是否需要实现排队模式？
- 是否需要 WEVERSE membership 认证？
- 支付是自动完成还是手动操作？
- 座位选择策略（优先区域/价格）？

### 3. 测试计划

- 当前登录功能已测试通过
- 需要真实的活动数据进行完整流程测试

---

## 已知问题

### 1. eKYC Token 获取失败 ⚠️

**错误**: 401 Unauthorized - "token invalid"

**可能原因**:
- 需要额外的会员认证
- Token 验证逻辑需要调整
- 需要特殊的用户权限

**影响**: 目前不影响登录，可能影响后续操作

### 2. Cloudflare SiteKey

**当前值**: `0x4AAAAAABGU_tHsh_LkPT_k`

**说明**: 从抓包数据中提取，可能需要动态获取

---

## 文件索引

### 代码文件
- `src/main.py` - 主程序入口
- `src/auth.py` - 认证模块（已完成）
- `src/cloudflare.py` - Cloudflare 解决器（已完成）
- `src/client.py` - HTTP 客户端
- `src/api_config.py` - API 配置
- `src/utils.py` - 工具函数

### 配置文件
- `config.yaml` - 主配置文件
- `.env.example` - 环境变量模板
- `requirements.txt` - Python 依赖

### 文档文件
- `README.md` - 项目说明
- `docs/QUICK_START.md` - 快速开始指南
- `docs/TESTING_GUIDE.md` - 测试指南
- `docs/CLOUDFLARE_SOLUTIONS.md` - Cloudflare 解决方案
- `docs/CAPSOLVER_SETUP.md` - Capsolver 配置指南
- `docs/API_DATA_NEEDED.md` - 接口数据需求（新增）

---

## 快速命令参考

### 测试登录
```bash
cd ~/Desktop/edison/itp
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_login.py
```

### 运行主程序（待实现完整功能）
```bash
cd ~/Desktop/edison/itp
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/main.py
```

### 查看日志
```bash
tail -f ~/Desktop/edison/itp/logs/itp_bot.log
```

---

## 联系和备注

**项目特点**:
- 纯 requests 实现（无浏览器自动化）
- 集成 Capsolver 解决 Cloudflare
- 配置驱动的座位选择
- 完整的日志系统

**注意事项**:
- Capsolver 需要付费（新用户有免费额度）
- 合法使用，仅用于个人购票
- 遵守网站服务条款

**下次沟通建议**:
1. 提供座位图、预留座位、提交订单的抓包数据
2. 确认是否需要实现排队功能
3. 讨论座位选择的具体策略
