# Capsolver 配置指南

## Capsolver 简介

Capsolver 是一个 AI 驱动的验证码解决服务，支持：
- Cloudflare Turnstile
- reCAPTCHA v2/v3
- hCaptcha
- 等多种验证码类型

## 注册和获取 API Key

1. 访问 [Capsolver 官网](https://capsolver.com)
2. 注册账号（支持邮箱或 Google/GitHub 登录）
3. 登录后进入 Dashboard
4. 复制你的 API Key

## 配置步骤

### 1. 编辑 `config.yaml`

```yaml
capsolver:
  api_key: "CAP-xxxxxxxxxxxxx"  # 替换为你的 API Key
  enabled: true                  # 启用 Capsolver
```

### 2. 或使用环境变量

编辑 `.env` 文件：

```bash
CAPSOLVER_API_KEY=CAP-xxxxxxxxxxxxx
```

## 使用方法

登录时会自动使用 Capsolver 解决 Cloudflare 验证：

```python
from src.auth import AuthManager

# 自动处理 Cloudflare 验证
auth_manager = AuthManager(client, config, logger)
success = auth_manager.login(username, password, skip_cloudflare=False)
```

## 费用说明

- Cloudflare Turnstile: 约 $0.002-0.003/次
- 新用户通常有免费额度
- 查看[定价页面](https://capsolver.com/pricing)获取最新价格

## 测试

Capsolver 提供测试环境，可以在不影响网站的情况下测试：

```python
# 测试模式（不消耗额度）
# 使用 Capsolver 的测试 sitekey
test_url = "https://tests.capsolver.com"
test_key = "test_site_key"
```

## 故障排除

### 1. API Key 无效
- 检查 API Key 是否正确复制
- 确认账号状态正常
- 检查余额是否充足

### 2. 验证失败
- 检查 website_url 是否正确
- 确认 website_key 是否匹配
- 查看日志了解详细错误信息

### 3. 余额不足
- 登录 Capsolver Dashboard 充值
- 最低充值金额通常是 $10

## 注意事项

1. **合法使用**: 仅用于合法的自动化测试，不要用于恶意爬虫
2. **速度**: 通常 10-30 秒解决一个验证
3. **成功率**: 正常情况下 >95%
4. **并发**: 支持，但需要购买更高等级的服务

## 其他替代方案

如果 Capsolver 不可用，可以考虑：
- [2Captcha](https://2captcha.com): 人工验证，速度较慢
- [Anti-Captcha](https://anti-captcha.com): 类似服务
- [YesCaptcha](https://yescaptcha.com): 更便宜的替代方案
