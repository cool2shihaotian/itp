"""解析 HAR 文件，提取关键 API 信息"""
import json

har_file = "/Users/shihaotian/Downloads/tickets.interpark.com.har"

with open(har_file, 'r', encoding='utf-8') as f:
    har_data = json.load(f)

# 查找关键 API
target_apis = [
    'ent-waiting-api.interpark.com/waiting/api/secure-url',
    'ent-waiting-api.interpark.com/waiting/api/line-up',
    'tickets.interpark.com/onestop/api/play/play-date',
    'tickets.interpark.com/onestop/api/session-check',
]

entries = har_data['log']['entries']

for entry in entries:
    url = entry['request']['url']

    # 检查是否是目标 API
    if any(api in url for api in target_apis):
        print(f"\n{'='*80}")
        print(f"URL: {url}")
        print(f"Method: {entry['request']['method']}")
        print(f"{'='*80}")

        # Headers
        print("\n[Request Headers]")
        for header in entry['request']['headers']:
            if header['name'] in ['Content-Type', 'Authorization', 'Origin', 'Referer', 'Cookie']:
                print(f"  {header['name']}: {header['value'][:100] if len(header['value']) > 100 else header['value']}")

        # Request Body (POST)
        if entry['request']['method'] == 'POST':
            print("\n[Request Body]")
            try:
                body = entry['request']['postData']['text']
                print(f"  {body[:500]}")
            except:
                print("  (No body data)")

        # Response
        status = entry['response']['status']
        print(f"\n[Response Status: {status}]")
        try:
            response_text = entry['response']['content']['text']
            print(f"[Response Body (first 500 chars)]")
            print(f"  {response_text[:500]}")
        except:
            pass

print("\n" + "="*80)
print("解析完成")
