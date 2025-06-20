import os
import requests
from datetime import datetime
from notion_client import Client

# === 初始化 ===
notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = "2182a91a-405d-80fe-82eb-c3bf47bfe625"
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_IDS = ["Ueac062fbefdeffa4bc3a4020db58fff6"]

# === LINE 發送封裝 ===
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

# === 1. 找出 Miao 的 Notion user_id ===
def get_user_id_by_name(target_name):
    users = notion.users.list()
    for user in users["results"]:
        if user.get("name") == target_name:
            return user["id"]
    return None

miao_user_id = get_user_id_by_name("Miao")
if not miao_user_id:
    print("❌ 找不到使用者 Miao")
    exit(1)

# === 2. 建立 Notion 資料 ===
tz = pytz.timezone("Asia/Taipei")
today = datetime.now(tz).strftime("%Y-%m-%d")
new_page = notion.pages.create(
    parent={"database_id": database_id},
    properties={
        "日期": {
            "title": [{
                "text": {
                    "content": today + " 會議紀錄"
                }
            }]
        },
        "時間": {
            "date": {
                "start": today
            }
        },
        "與會人": {
            "people": [
                {"id": miao_user_id}
                # 你可以加更多與會人
            ]
        }
    }
)

# === 3. 判斷與會人是否包含 Miao，發送通知 ===
attendees = new_page["properties"]["與會人"]["people"]
attendee_ids = [p["id"] for p in attendees]

if miao_user_id in attendee_ids:
    msg = f"📅 會議提醒：Miao 您今日有會議（{today}），請準時參與。"
    send_line_message(LINE_USER_IDS, msg)
else:
    print("⚠️ Miao 不在與會人中，略過通知")
