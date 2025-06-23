import os
from datetime import datetime
from notion_client import Client
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 初始化
notion = Client(auth=os.getenv("NOTION_TOKEN"))
line_bot_api = LineBotApi(os.getenv("LINE_ACCESS_TOKEN"))

MEETING_DB_ID = "cd784a100f784e15b401155bc3313a1f" # 會議database
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325" # userid database

today_str = datetime.now().date().isoformat()
today_display = datetime.now().strftime("%Y/%m/%d")

# 1️⃣ 查詢今天的所有會議
print("🔍 查詢今天的會議...")
meeting_pages = notion.databases.query(
    database_id=MEETING_DB_ID,
    filter={
        "property": "日期",
        "date": {
            "on_or_after": today_str,
            "on_or_before": today_str
        }
    }
).get("results", [])

if not meeting_pages:
    print("✅ 今天沒有會議")
    exit(0)

# 2️⃣ 載入使用者名稱與 userId 對照表
print("🔍 查詢使用者資料...")
user_map = {}  # name -> userId
user_meetings = {}  # name -> list of meetings

user_pages = notion.databases.query(
    database_id=USERID_DB_ID,
    filter={
        "property": "Name",
        "title": {"is_not_empty": True}
    }
).get("results", [])

for page in user_pages:
    name = page["properties"]["Name"]["title"][0]["text"]["content"]
    user_id = page["properties"]["User ID"]["rich_text"][0]["text"]["content"]
    user_map[name] = user_id
    user_meetings[name] = []

# 3️⃣ 整理今天所有會議，並依與會人員（person）分類
for page in meeting_pages:
    props = page["properties"]
    title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "未命名會議"
    datetime_str = props["日期"]["date"]["start"]
    date_time = datetime.fromisoformat(datetime_str).strftime("%Y/%m/%d %H:%M")
    location = props.get("地點", {}).get("select", {}).get("name", "未填寫")
    persons = props.get("相關人員", {}).get("people", [])

    attendee_names = [p["name"] for p in persons]

    for name in attendee_names:
        if name in user_meetings:
            user_meetings[name].append({
                "title": title,
                "datetime": date_time,
                "location": location
            })

# 4️⃣ 發送通知給各使用者
print("📨 傳送 LINE 通知中...")
for name, meetings in user_meetings.items():
    if not meetings:
        continue

    user_id = user_map[name]
    lines = [f"{today_display} 會議提醒"]

    for idx, m in enumerate(meetings, start=1):
        lines.append(f"{idx}. {m['title']}")
        lines.append(f"－ 時間：{m['datetime']}")
        lines.append(f"－ 地點：{m['location']}")
        lines.append("")

    message = "\n".join(lines).strip()

    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        print(f"✅ 已通知 {name}")
    except Exception as e:
        print(f"❌ 發送失敗：{name}（{user_id}） ➜ {e}")
