# seatMeta API 修复总结

## 问题描述

`block-data` 和 `seatMeta` API 返回 400 错误，无法获取座位信息。

## 根本原因

缺少关键的 `userId` cookie！这个 cookie 是 Interpark API 验证用户身份的必需参数。

## 修复方案

### 1. 添加必要的 Cookies

在调用 block-data 和 seatMeta API 之前，必须设置以下 cookies：

```python
# 关键修复：设置 userId cookie
client.session.cookies.set('userId', user_id)
client.session.cookies.set('ent_onestop_channel', 'TRIPLE_KOREA')
```

### 2. 完善请求 Headers

添加完整的 headers 以匹配浏览器请求：

```python
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://tickets.interpark.com/onestop/seat',
    'x-onestop-channel': 'TRIPLE_KOREA',
    'x-onestop-session': session_id,
    'x-onestop-trace-id': str(uuid.uuid4())[:16],  # 添加 trace ID
    'x-requested-with': 'XMLHttpRequest',
    'x-ticket-bff-language': 'ZH'  # 添加语言设置
}
```

### 3. 逐个查询区域

批量查询多个 blockKeys 会导致 500 错误，改为逐个查询：

```python
# 之前：批量查询（会失败）
params = [('goodsCode', '25018223'), ('placeCode', '25001698'), ('playSeq', play_seq)]
for block_key in block_keys:
    params.append(('blockKeys', block_key))

# 现在：逐个查询（成功）
for block_key in block_keys:
    params = {
        'goodsCode': '25018223',
        'placeCode': '25001698',
        'playSeq': play_seq,
        'blockKeys': block_key  # 单个区域
    }
```

## 测试结果

### 测试 1: block-data API

```
✅ 成功！获取到 25 个区域:
  1. 001:001
  2. 001:002
  3. 001:003
  ...
```

### 测试 2: seatMeta API

```
✅ 找到可售座位: 25018223:25001698:001:333
  座位ID: 25018223:25001698:001:333
  价位: R석 (143,000韩元)
  位置: FLOOR - 가구역 6열 - 17
```

## 修改的文件

### 1. `/Users/shihaotian/Desktop/edison/itp/src/polling_seat_selector.py`

**变更：**
- `get_block_keys()`: 添加 `user_id` 参数，设置 userId cookie
- `get_real_seat_availability()`: 添加 `user_id` 参数，设置 userId cookie
- `poll_and_select()`: 添加 `user_id` 参数，传递给子方法
- 完善所有请求的 headers

**关键代码：**
```python
def get_block_keys(self, play_seq: str, session_id: str, user_id: str = None):
    # 设置必要的 cookies
    if user_id:
        self.client.session.cookies.set('userId', user_id)
    self.client.session.cookies.set('ent_onestop_channel', 'TRIPLE_KOREA')

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://tickets.interpark.com/onestop/seat',
        'x-onestop-channel': 'TRIPLE_KOREA',
        'x-onestop-session': session_id,
        'x-onestop-trace-id': str(uuid.uuid4())[:16],
        'x-requested-with': 'XMLHttpRequest',
        'x-ticket-bff-language': 'ZH'
    }
```

## 使用方法

### 测试脚本

运行完整的轮询测试：

```bash
PYTHONPATH=/Users/shihaotian/Desktop/edison/itp/src python3 /Users/shihaotian/Desktop/edison/itp/src/test_polling_with_userid.py
```

### 在实际使用中

确保在调用 `poll_and_select()` 时传递 `user_id`：

```python
# 获取 user_id
user_id = auth.user_id  # 从 AuthManager 获取

# 轮询选座
selected_seat = selector.poll_and_select(
    onestop=onestop,
    play_date='20260212',
    session_id=session_id,
    member_info=member_info,
    user_id=user_id,  # ⚠️ 必须传递 user_id！
    poll_interval=3,
    timeout=300
)
```

## 总结

✅ **问题已解决！**

关键修复：
1. ✅ 设置 `userId` cookie（最重要！）
2. ✅ 设置 `ent_onestop_channel` cookie
3. ✅ 添加完整的 headers
4. ✅ 逐个查询区域而不是批量查询

现在 block-data 和 seatMeta API 都能正常工作了，可以成功获取座位信息并检测可售座位！

---

**创建时间**: 2026-01-16
**修复状态**: ✅ 完成并验证
**测试结果**: ✅ 所有测试通过
