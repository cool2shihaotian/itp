# ITP 自动购票程序 - 测试指南

## 当前进度

### ✅ 已完成
1. 项目基础结构搭建
2. 登录模块实现（基于 Firebase Authentication）
3. eKYC token 获取
4. Session 和 Cookie 管理

### ⏳ 待实现
1. Cloudflare Turnstile 验证（难点）
2. 获取活动/场次信息接口
3. 排队等待逻辑
4. 座位选择逻辑
5. 订单提交和支付接口

---

## 快速开始

### 1. 安装依赖
```bash
cd ~/Desktop/edison/itp
pip3 install -r requirements.txt
```

### 2. 配置账号信息
编辑 `config.yaml`，填入你的账号信息：
```yaml
account:
  username: "your_email@example.com"
  password: "your_password"
```

### 3. 测试登录功能
```bash
cd ~/Desktop/edison/itp/src
python3 test_login.py
```

**注意**：目前跳过了 Cloudflare 验证，直接调用 Firebase 登录接口。

---

## 关于 Cloudflare 验证

### 当前状态
登录前需要完成 Cloudflare Turnstile 验证，这是一个反机器人验证系统。

### 临时方案
我们可以尝试：
1. **手动完成一次验证**，然后保存所有 cookies
2. **使用保存的 cookies** 直接调用 Firebase 登录
3. **测试 cookies 的有效期**，看看是否能维持一段时间

### 下一步选择
请告诉我你希望：
- **A. 先测试 Firebase 登录**（跳过 Cloudflare，看是否需要）
- **B. 集成 Cloudflare 解决方案**（需要第三方服务，如 Capsolver）
- **C. 提供更多接口信息**（活动列表、座位选择等），先实现其他功能

---

## 需要的更多信息

为了继续实现购票功能，我还需要以下接口的抓包数据：

### 1. 活动列表
- URL: 获取所有可用活动的接口
- Method: GET/POST
- 返回数据格式

### 2. 场次信息
- URL: 获取具体场次信息的接口
- 参数: event_code, schedule_code

### 3. 座位图
- URL: 获取座位图的接口
- 返回数据格式

### 4. 检查可用性
- URL: 检查座位是否可用的接口
- 参数格式

### 5. 预留座位
- URL: 预留座位的接口
- 请求参数和响应格式

### 6. 提交订单
- URL: 提交订单的接口
- 护照信息、支付信息的格式

### 7. 支付
- URL: 支付接口
- 支付流程

---

## 项目文件说明

- `src/api_config.py`: API 配置和常量
- `src/client.py`: HTTP 客户端封装
- `src/auth.py`: 登录和认证模块
- `src/test_login.py`: 登录测试脚本
- `src/ticket.py`: 购票核心逻辑（待实现）
- `src/seat.py`: 座位选择模块（待实现）
- `src/payment.py`: 支付模块（待实现）

---

## 下一步

请告诉我：
1. 你想先测试登录功能吗？
2. 你有更多接口的抓包数据吗？
3. 关于 Cloudflare，你倾向于哪种解决方案？
