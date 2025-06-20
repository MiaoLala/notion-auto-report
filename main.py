import os
import requests
from datetime import datetime
from notion_client import Client

# 初始化 Notion API 客戶端
notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = "2182a91a-405d-80fe-82eb-c3bf47bfe625"

# LINE Messaging API Token
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]

# 🔔 多位接收者的 userId 名單
LINE_USER_IDS = [
    "Ueac062fbefdeffa4bc3a4020db58fff6",  # 你
    "U96c4beeb35625844b76a4d4f56bf5ea1"  # 其他人（可加更多）
]

# 發送 LINE 訊息（支援多位 userId）
def send_line_message(user_ids, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    for user_id in user_ids:
        data = {
            "to": user_id,
            "messages": [{
                "type": "text",
                "text": message
            }]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"❌ 傳送給 {user_id} 失敗：{response.status_code}, {response.text}")
        else:
            print(f"✅ 傳送給 {user_id} 成功！")

# 確保 database ID 存在
if not database_id:
    print(f"❌ 找不到資料庫")
    exit(1)

# 取得今天日期
today = datetime.now().strftime("%Y-%m-%d")

# 新增一筆資料到 Notion
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

# 傳送 LINE 成功通知
line_message = f"✅ Notion 已新增資料：{today} 測試API"
send_line_message(LINE_USER_IDS, line_message)
