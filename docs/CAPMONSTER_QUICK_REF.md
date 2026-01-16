# Capmonster AWS WAF 快速参考

## 快速开始

### 1. 注册并获取 API Key
```
1. 访问 https://capmonster.com/
2. 注册账号并验证邮箱
3. 在控制台获取 API Key
4. 充值余额（建议 $5-10 测试）
```

### 2. 配置 config.yaml
```yaml
capmonster:
  api_key: "CAP-XXXXXXXXXXXXX"  # 你的 API Key
  enabled: true                  # 启用 Capmonster
  use_proxy: false               # 是否使用代理
```

### 3. 验证配置
```bash
# 测试配置是否正确
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_capmonster.py

# 测试 API 连接（需要余额）
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_capmonster.py --test-api
```

### 4. 运行购票流程
```bash
# 完整流程（会自动使用 Capmonster）
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 src/test_full_flow.py
```

---

## 工作原理

```
Waiting Queue 流程:
1. 获取 secure-url (需要 signature + secureData)
2. 解决 AWS WAF 挑战 ← Capmonster 在这里工作
3. 进入排队 (line-up)
4. 轮询位置 (rank)
```

**Capmonster 的作用**:
- 自动解决 AWS WAF 验证
- 返回 WAF token
- 自动设置为 cookie
- 允许继续排队流程

---

## 两种任务类型

### AWSWafTaskProxyLess（推荐）
```yaml
capmonster:
  use_proxy: false  # 无需代理
```
- ✅ 速度快（~3-10秒）
- ✅ 成本低（~$0.002/次）
- ✅ 适合大多数场景

### AWSWafTask
```yaml
capmonster:
  use_proxy: true   # 需要代理
```
- ⚠️ 需要额外代理服务
- ⚠️ 成本稍高（~$0.003/次）
- ✅ 适合严格 WAF 环境

---

## 费用估算

| 场景 | 次数 | 预计费用 |
|------|------|----------|
| 测试 | 10 次 | ~$0.02 |
| 正常购票 | 50 次 | ~$0.10 |
| 高需求（BTS） | 100 次 | ~$0.20 |

---

## 日志示例

**成功**:
```
✅ Capmonster AWS WAF 解决器已启用
[排队 2/4] 解决 AWS WAF 挑战
使用 Capmonster 解决 AWS WAF 挑战...
创建 Capmonster 任务: https://tickets.interpark.com/
✅ Capmonster 任务创建成功: 123456789
✅ Capmonster 任务完成
✅ AWS WAF 挑战解决成功！
WAF token 已设置为 cookie
```

**失败**:
```
❌ Capmonster WAF 解决失败
⚠️ Capmonster WAF 解决失败，但继续尝试 line-up
```

---

## 常见问题

### Q: 是否必须启用？
**A**: 不是。如果购票时没有遇到 AWS WAF，可以不启用。

### Q: 如何判断是否需要？
**A**: 如果看到 "Access Denied" 或 403 错误，可能需要启用。

### Q: 余额不足会怎样？
**A**: 日志会显示 "No balance" 错误，需要充值后重试。

### Q: 和 Capsolver 有什么区别？
**A**:
- Capsolver → Cloudflare Turnstile（登录阶段）
- Capmonster → AWS WAF（排队阶段）

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/aws_waf.py` | Capmonster 客户端实现 |
| `src/waiting.py` | 排队系统（已集成） |
| `src/test_capmonster.py` | 配置测试脚本 |
| `docs/CAPMONSTER_SETUP.md` | 详细配置指南 |

---

## 技术支持

- Capmonster 文档: https://capmonster.com/docs/
- Capmonster 支持: support@capmonster.com
- 问题反馈: 项目 Issues

---

**提示**: 建议在正式购票前先测试配置，确保 API Key 和余额充足。
