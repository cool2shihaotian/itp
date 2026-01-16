"""API 配置和常量"""

# Cloudflare Turnstile 配置
CLOUDFLARE_BASE_URL = "https://challenges.cloudflare.com"

# Firebase 配置
FIREBASE_CONFIG = {
    "api_key": "AIzaSyDi1DsEgLRDaWDI2aF7WerqKLqcD5HC8V4",
    "signin_url": "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
    "gmp_id": "1:182595350393:web:0a10fb747ba6a5922d89a8",
    "client_version": "Chrome/JsCore/11.10.0/FirebaseCore-web",
    "browser_year": "2026",
}

# NOL/Interpark Global API 配置
NOL_API = {
    "base_url": "https://world.nol.com",
    "ekyc_token_url": "https://world.nol.com/api/users/enter/ekyc/token",
    "salesinfo_url": "https://world.nol.com/api/ent-channel-out/v1/goods/salesinfo",
    "enter_url": "https://world.nol.com/api/users/enter",
    "service_origin": "global",
}

# Tickets Interpark API 配置（座位和预订）
TICKETS_API = {
    "base_url": "https://tickets.interpark.com",
    "goods_info_url": "https://tickets.interpark.com/api/ticket/v2/reserve-gate/goods-info",
    "member_info_url": "https://tickets.interpark.com/api/ticket/v2/reserve-gate/member-info",
    "ekyc_auth_url": "https://tickets.interpark.com/api/ticket/v2/ekyc/auth",
}

# Headers 常量
COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6,ru;q=0.5,la;q=0.4,th;q=0.3',
    'Origin': 'https://world.nol.com',
    'Referer': 'https://world.nol.com/',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
}

# Cookie 名称
COOKIE_NAMES = {
    'access_token': 'access_token',
    'refresh_token': 'refresh_token',
    'device_id': 'kint5-web-device-id',
    'language': 'tk-language',
}
