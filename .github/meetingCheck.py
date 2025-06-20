import os
import requests
from datetime import datetime, timedelta
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = "2182a91a-405d-80fe-82eb-c3bf47bfe625"
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_IDS = ["Ueac062fbefdeffa4bc3a4020db58fff6"]

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

def get_user_id_by_name(name):
    users = notion.users.list()
    for user in users["results"]:
        if user.get("name") == name:
            return user["id"]
    return None

miao_user_id = get_user_id_by_name("Miao")
if not miao_user_id:
    print("❌ 找不到 Miao 的 Notion user ID")
    exit(1)

# 今天日期（ISO 格式）
today = datetime.utcnow() + timedelta(hours=8)  # 調整為台灣時間
today_str = today.date().isoformat()

# 查詢今天的會議（時間欄位 = 今天）
response = notion.databases.query(
    database_id=database_id,
    filter={
        "property": "時間",
        "date": {
            "equals": today_str
        }
    }
)

found = False
for page in response["results"]:
    attendees = page["properties"]["與會人"]["people"]
    attendee_ids = [p["id"] for p in attendees]

    if miao_user_id in attendee_ids:
        title = page["properties"]["日期"]["title"][0]["text"]["content"]
        msg = f"📅 Miao，您今日有會議：{title}"
        send_line_message(LINE_USER_IDS, msg)
        found = True

if not found:
    print("📭 今日無會議需要提醒")
