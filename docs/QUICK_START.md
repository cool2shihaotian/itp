# ITP 自动购票程序 - 快速开始指南

## 安装依赖

```bash
cd ~/Desktop/edison/itp
pip3 install -r requirements.txt
```

## 配置

### 1. 基础配置

编辑 `config.yaml`：

```yaml
account:
  username: "your-email@example.com"  # 你的 Interpark 账号
  password: "your-password"            # 密码

event:
  event_code: ""      # 活动 code（待获取）
  schedule_code: ""   # 场次 code（待获取）

payment:
  passport_number: ""  # 护照号码
  card_number: ""      # 信用卡号（可选）
  expiry_date: ""      # 有效期 MM/YY（可选）
  card_type: "visa"    # visa 或 mastercard

capsolver:
  api_key: ""          # Capsolver API Key（可选）
  enabled: false       # 是否启用自动验证
```

### 2. Cloudflare 验证配置（推荐）

如果要自动处理 Cloudflare 验证：

1. 注册 [Capsolver](https://capsolver.com) 账号
2. 获取 API Key
3. 在 `config.yaml` 中配置：

```yaml
capsolver:
  api_key: "CAP-xxxxxxxxxxxxx"  # 你的 API Key
  enabled: true                  # 启用
```

详细配置见 [Capsolver 配置指南](./CAPSOLVER_SETUP.md)

## 使用

### 测试登录

```bash
cd ~/Desktop/edison/itp/src
python3 test_login.py
```

这将测试登录功能并保存 cookies。

### 完整购票流程

```bash
cd ~/Desktop/edison/itp/src
python3 main.py
```

## 项目结构

```
itp/
├── config.yaml              # 配置文件
├── .env                     # 环境变量（敏感信息）
├── requirements.txt         # Python 依赖
├── src/                     # 源代码
│   ├── main.py             # 主程序入口
│   ├── client.py           # HTTP 客户端
│   ├── auth.py             # 认证模块
│   ├── cloudflare.py       # Cloudflare 验证解决
│   ├── ticket.py           # 购票核心逻辑
│   ├── seat.py             # 座位选择模块
│   ├── payment.py          # 支付模块
│   └── utils.py            # 工具函数
├── logs/                    # 日志文件
├── docs/                    # 文档
└── captures/               # 抓包数据
```

## 开发状态

### ✅ 已完成
- [x] 项目基础结构
- [x] Firebase 登录
- [x] eKYC token 获取
- [x] Cloudflare Turnstile 验证集成（Capsolver）
- [x] Session 和 Cookie 管理
- [x] 日志系统

### 🚧 进行中
- [ ] 获取活动列表接口
- [ ] 获取座位图接口
- [ ] 座位选择逻辑
- [ ] 订单提交接口
- [ ] 支付接口

### ❓ 待确认
- [ ] 活动列表 API
- [ ] 座位图 API
- [ ] 排队机制
- [ ] 订单提交流程

## 下一步

1. **测试登录功能**
   ```bash
   python3 src/test_login.py
   ```

2. **提供更多抓包数据**
   - 活动列表接口
   - 座位图接口
   - 订单提交接口
   - 支付接口

3. **实现剩余功能**
   - 根据抓包数据实现各个模块

## 常见问题

### 1. Capsolver 费用如何？
约 $0.002-0.003/次验证，新用户有免费额度。

### 2. 不使用 Capsolver 可以吗？
可以，设置 `capsolver.enabled: false`，但需要手动处理 Cloudflare 验证。

### 3. 如何获取 event_code？
需要通过活动列表 API 获取，待实现或手动抓包获取。

### 4. 程序会自动选座吗？
是的，根据 `config.yaml` 中配置的座位优先级自动选择。

## 技术支持

遇到问题请查看：
- [Capsolver 配置指南](./CAPSOLVER_SETUP.md)
- [测试指南](./TESTING_GUIDE.md)
- [Cloudflare 解决方案](./CLOUDFLARE_SOLUTIONS.md)
