# ITP 自动购票程序

## 项目结构
```
itp/
├── config.yaml           # 配置文件
├── .env                  # 环境变量（敏感信息）
├── requirements.txt      # Python 依赖
├── README.md            # 项目说明
├── src/                 # 源代码目录
│   ├── __init__.py
│   ├── main.py          # 主程序入口
│   ├── client.py        # HTTP 客户端封装
│   ├── auth.py          # 登录和认证模块
│   ├── ticket.py        # 购票核心逻辑
│   ├── seat.py          # 座位选择模块
│   ├── payment.py       # 支付模块
│   └── utils.py         # 工具函数
├── logs/                # 日志目录
└── tests/               # 测试文件
```

## 安装依赖
```bash
pip3 install -r requirements.txt
```

## 配置说明
1. 复制 `.env.example` 为 `.env` 并填入账号信息
2. 编辑 `config.yaml` 配置座位优先级和其他设置

## 使用方法
```bash
cd src
python3 main.py
```

## 注意事项
- 本程序仅用于学习和个人使用
- 请遵守网站服务条款
- 建议先在测试环境中验证
