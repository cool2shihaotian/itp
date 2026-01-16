# Cloudflare Turnstile 验证解决方案

## 问题描述
登录前需要完成 Cloudflare Turnstile 验证，这是一个反机器人验证系统。

## 当前抓包信息
- 验证 URL: `https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/flow/ov1/...`
- Headers 需要:
  - `cf-chl`: 动态生成的 challenge token
  - `cf-chl-ra`: 通常是 0
- Payload: 加密的验证数据

## 可能的解决方案

### 方案 1: 使用第三方验证服务 ⭐ 推荐
使用专业的人机验证解决服务：
- **2Captcha**: https://2captcha.com
- **Anti-Captcha**: https://anti-captcha.com
- **Capsolver**: https://www.capsolver.com (AI 驱动，更快)

这些服务可以：
1. 自动识别并解决 Cloudflare Turnstile
2. 提供解决后的 token
3. 价格合理（约 $2-3/1000 次验证）

### 方案 2: 浏览器自动化
使用 Playwright/Selenium + undetected-chromedriver：
- 优点：更真实，不容易被检测
- 缺点：速度慢，资源占用大
- 可能与纯 requests 的目标冲突

### 方案 3: Session 复用 ⚠️
如果验证 token 有效期较长：
1. 手动完成一次验证
2. 保存 cookies/tokens
3. 在有效期内复用（需要测试有效期）

### 方案 4: 研究验证算法
研究 Turnstile 的 JavaScript 代码：
- 优点：无需第三方服务
- 缺点：复杂，容易失效
- 不推荐，Cloudflare 会定期更新

## 推荐实施步骤

### 阶段 1: 快速验证（使用方案 3）
1. 手动完成 Cloudflare 验证和登录
2. 抓取所有 cookies
3. 实现其他购票功能
4. 验证核心流程

### 阶段 2: 生产环境（使用方案 1）
1. 集成 Capsolver 或 2Captcha
2. 实现自动验证流程
3. 测试稳定性

## 当前建议
1. **先跳过 Cloudflare**，手动获取 token
2. **专注实现核心购票功能**
3. **其他接口验证通过后**，再解决 Cloudflare

## 下一步
请确认：
- [ ] 是否有现有的有效 cookies/token？
- [ ] Cloudflare 验证是否每次登录都需要？
- [ ] 是否愿意使用第三方验证服务？
