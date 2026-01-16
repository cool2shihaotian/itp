# Capmonster AWS WAF 解决配置指南

## 什么是 Capmonster？

Capmonster 是一个验证码解决服务，支持多种类型的验证码，包括：
- AWS WAF (Amazon Web Services Web Application Firewall)
- reCAPTCHA v2/v3
- hCaptcha
- Cloudflare Turnstile
- 等等

## 为什么需要 Capmonster？

在使用 ITP 购票系统时，可能会遇到 AWS WAF 挑战。这是一种反机器人保护机制，需要解决验证后才能继续访问。Capmonster 可以自动解决这些挑战。

---

## 1. 注册 Capmonster 账号

1. 访问 [Capmonster 官网](https://capmonster.com/)
2. 点击 "Sign Up" 注册账号
3. 验证邮箱
4. 登录到控制台

---

## 2. 获取 API Key

1. 登录后，进入控制台
2. 在左侧菜单找到 "API Key" 或 "密钥"
3. 复制你的 API Key（格式类似：`CAP-XXXXXXXXXXXXX`）

---

## 3. 充值余额

Capmonster 是付费服务，按解决次数计费：

1. 在控制台找到 "充值" 或 "Balance"
2. 选择支付方式（信用卡、加密货币等）
3. AWS WAF 解决价格：约 $0.002 - $0.003/次

**建议充值金额**:
- 测试阶段：$5-10
- 正式购票：根据需要，建议 $20+

---

## 4. 配置 config.yaml

打开 `config.yaml` 文件，找到 `capmonster` 配置部分：

```yaml
# Capmonster 配置（用于解决 AWS WAF 验证）
capmonster:
  api_key: "YOUR_CAPMONSTER_API_KEY"  # 替换为你的 API Key
  enabled: true  # 设置为 true 启用
  use_proxy: false  # 是否使用代理（可选）
```

### 配置说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `api_key` | string | 你的 Capmonster API Key | 必填 |
| `enabled` | boolean | 是否启用 Capmonster | `false` |
| `use_proxy` | boolean | 是否使用代理解决 WAF | `false` |

### 代理配置（可选）

如果你的网络环境需要使用代理：

```yaml
capmonster:
  api_key: "YOUR_CAPMONSTER_API_KEY"
  enabled: true
  use_proxy: true

# 同时配置代理
proxy:
  enabled: true
  http_proxy: "http://proxy-server:port"
  https_proxy: "http://proxy-server:port"
```

---

## 5. 任务类型说明

Capmonster 支持两种 AWS WAF 任务类型：

### 5.1 AWSWafTaskProxyLess（推荐）
- **无需代理**
- 速度更快
- 成本更低
- 适合大多数场景

### 5.2 AWSWafTask
- **需要代理**
- 适用于更严格的 WAF 配置
- 需要额外的代理服务

系统会根据 `use_proxy` 配置自动选择任务类型。

---

## 6. 使用示例

### 基本使用

```python
from src.waiting import WaitingQueue

# WaitingQueue 会自动检测 Capmonster 配置
waiting = WaitingQueue(client, config, logger)

# 调用排队流程时，会自动使用 Capmonster 解决 AWS WAF
success = waiting.full_waiting_queue(
    signature=signature,
    secure_data=secure_data,
    goods_code=goods_code
)
```

### 日志输出

启用 Capmonster 后，你会看到类似的日志：

```
2026-01-16 10:00:00 - ITPBot - INFO - ✅ Capmonster AWS WAF 解决器已启用
2026-01-16 10:00:05 - ITPBot - INFO - [排队 2/4] 解决 AWS WAF 挑战
2026-01-16 10:00:05 - ITPBot - INFO - 使用 Capmonster 解决 AWS WAF 挑战...
2026-01-16 10:00:05 - ITPBot - INFO - 创建 Capmonster 任务: https://tickets.interpark.com/
2026-01-16 10:00:06 - ITPBot - INFO - ✅ Capmonster 任务创建成功: 123456789
2026-01-16 10:00:10 - ITPBot - INFO - ✅ Capmonster 任务完成
2026-01-16 10:00:10 - ITPBot - INFO - ✅ AWS WAF 挑战解决成功！
```

---

## 7. 常见问题

### Q1: Capmonster 和 Capsolver 有什么区别？

| 服务 | 用途 | 配置项 |
|------|------|--------|
| **Capsolver** | 解决 Cloudflare Turnstile | `capsolver.api_key` |
| **Capmonster** | 解决 AWS WAF | `capmonster.api_key` |

两个服务可以同时使用，互不冲突。

### Q2: 是否必须使用 Capmonster？

**不是必须的**。根据实际情况：
- 如果购票时没有遇到 AWS WAF 挑战，可以不启用
- 如果遇到 "Access Denied" 或类似错误，建议启用
- 可以设置 `enabled: false` 测试是否需要

### Q3: 如何判断是否遇到 AWS WAF 挑战？

常见的 AWS WAF 挑战表现：
- 返回 403 Forbidden
- 页面显示 "Access Denied"
- 返回包含 "aws" 的错误信息
- 需要完成验证码才能继续

### Q4: Capmonster 余额不足怎么办？

系统会在日志中显示错误：
```
❌ 创建任务失败: No balance (余额不足)
```

解决方法：
1. 登录 Capmonster 控制台充值
2. 重新运行程序

### Q5: AWS WAF 解决失败怎么办？

可能的原因和解决方案：

1. **API Key 错误**
   - 检查 `config.yaml` 中的 `api_key` 是否正确

2. **网络问题**
   - 检查网络连接
   - 考虑使用代理

3. **WAF 挑战过于复杂**
   - 尝试启用代理模式：`use_proxy: true`
   - 联系 Capmonster 技术支持

### Q6: 使用代理有什么好处？

使用代理的优点：
- 绕过 IP 限制
- 提高成功率
- 模拟不同地区的访问

使用代理的缺点：
- 需要额外的代理服务费用
- 配置更复杂
- 速度可能更慢

---

## 8. 费用估算

### AWS WAF 解决成本

- **无代理模式**: ~$0.002/次
- **有代理模式**: ~$0.003/次

### 完整购票流程成本

假设一次购票需要解决 1-2 次 AWS WAF：

| 购票次数 | 预计费用 |
|----------|----------|
| 10 次 | ~$0.02 - $0.06 |
| 50 次 | ~$0.10 - $0.30 |
| 100 次 | ~$0.20 - $0.60 |

**注意**: 这只是 AWS WAF 的费用，不包括 Cloudflare Turnstile（Capsolver）。

---

## 9. 测试配置

配置完成后，运行测试验证：

```bash
# 测试完整流程（会尝试使用 Capmonster）
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_waiting.py
```

如果配置正确，日志会显示：
```
✅ Capmonster AWS WAF 解决器已启用
```

---

## 10. 最佳实践

### 10.1 开发/测试阶段
```yaml
capmonster:
  enabled: false  # 节省费用
```

### 10.2 正式购票
```yaml
capmonster:
  enabled: true
  api_key: "YOUR_KEY"
  use_proxy: false  # 先尝试无代理
```

### 10.3 高需求演出（BTS 等）
```yaml
capmonster:
  enabled: true
  api_key: "YOUR_KEY"
  use_proxy: true  # 使用代理提高成功率

proxy:
  enabled: true
  http_proxy: "your-proxy:port"
  https_proxy: "your-proxy:port"
```

---

## 11. 账户安全

**重要提示**:
- 🔐 不要分享你的 API Key
- 🔐 定期更换 API Key（可在控制台重置）
- 🔐 监控账户余额和使用情况
- 🔐 如有异常，立即联系 Capmonster 客服

---

## 12. 技术支持

### Capmonster 官方资源
- **官网**: https://capmonster.com/
- **文档**: https://capmonster.com/docs/
- **支持**: support@capmonster.com

### 常用 API 端点

```
创建任务: POST https://api.capmonster.cloud/createTask
获取结果: POST https://api.capmonster.cloud/getTaskResult
账户余额: POST https://api.capmonster.cloud/getBalance
```

---

## 13. 故障排除

### 检查 API Key 是否有效

```bash
curl -X POST https://api.capmonster.cloud/getBalance \
  -H "Content-Type: application/json" \
  -d '{"clientKey": "YOUR_API_KEY"}'
```

返回示例：
```json
{
  "errorId": 0,
  "balance": 12.3456,
  "currency": "USD"
}
```

### 查看任务状态

在日志中搜索 `Capmonster`，查看：
- 任务创建是否成功
- 任务解决时间
- 错误信息

---

## 14. 与其他验证码服务的对比

| 服务 | AWS WAF | Cloudflare | 价格 |
|------|---------|------------|------|
| **Capmonster** | ✅ | ✅ | 中等 |
| **Capsolver** | ✅ | ✅ | 中等 |
| **2Captcha** | ✅ | ✅ | 低（慢） |
| **Anti-Captcha** | ✅ | ✅ | 中等 |

**推荐配置**:
- Cloudflare Turnstile → Capsolver（已配置）
- AWS WAF → Capmonster（本文档）

---

## 15. 更新日志

- **2026-01-16**: 初始版本，支持 AWS WAF 解决
- 后续更新将记录在此

---

**祝你购票成功！🎫**
