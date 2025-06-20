import os
import requests
from datetime import datetime
from notion_client import Client

# 初始化 Notion API 客戶端
notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = "2182a91a-405d-80fe-82eb-c3bf47bfe625"

# LINE Messaging API Token & userId
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_ID = "miaolala_" # os.environ["LINE_USER_ID"]  # 你要發訊息的對象（自己或用戶）

def send_line_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"❌ LINE 發送失敗：{response.status_code}, {response.text}")
    else:
        print("✅ 已透過 LINE 發送成功通知。")

if not database_id:
    print(f"❌ 找不到資料庫")
    exit(1)

# 取得今天日期
today = datetime.now().strftime("%Y-%m-%d")

# 新增一筆資料
notion.pages.create(
    parent={"database_id": database_id},
    properties={
        "日期": {
            "title": [
                {
                    "text": {
                        "content": today + " 測試API"
                    }
                }
            ]
        }
    }
)

# 發送 LINE 成功通知
line_message = f"✅ Notion 已新增資料：{today} 測試API"
send_line_message(LINE_USER_ID, line_message)
