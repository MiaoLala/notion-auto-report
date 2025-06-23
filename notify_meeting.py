import os
from datetime import datetime
from notion_client import Client
from linebot.v3.messaging import Configuration, MessagingApi
from linebot.v3.messaging.models import TextMessage, PushMessageRequest

# 初始化 Notion 與 LINE Messaging API
notion = Client(auth=os.getenv("NOTION_TOKEN"))

line_config = Configuration(access_token=os.getenv("LINE_ACCESS_TOKEN"))
line_bot_api = MessagingApi(configuration=line_config)

MEETING_DB_ID = "cd784a100f784e15b401155bc3313a1f" # 會議database
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325" # userid database

today_str = datetime.now().date().isoformat()
today_display = datetime.now().strftime("%Y/%m/%d")

# 1️⃣ 查詢今天的會議
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

# 2️⃣ 讀取使用者對照資料（Name → userId）
print("🔍 查詢使用者資料...")
user_map = {}
user_meetings = {}

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

# 3️⃣ 根據「相關人員（Person）」比對使用者是否有參與會議
for page in meeting_pages:
    props = page["properties"]
    title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "未命名會議"

    # 日期＋時間
    datetime_str = props["日期"]["date"]["start"]
    date_time = datetime.fromisoformat(datetime_str).strftime("%Y/%m/%d %H:%M")

    # 地點安全擷取
    location = "未填寫"
    location_prop = props.get("地點")
    if location_prop and location_prop.get("select"):
        location = location_prop["select"]["name"]

    # 相關人員（person）
    persons = props.get("相關人員", {}).get("people", [])
    attendee_names = [p["name"] for p in persons]

    for name in attendee_names:
        if name in user_meetings:
            user_meetings[name].append({
                "title": title,
                "datetime": date_time,
                "location": location
            })

# 4️⃣ 傳送 LINE 通知
print("📨 傳送 LINE 通知中...")
for name, meetings in user_meetings.items():
    if not meetings:
        continue

    user_id = user_map.get(name)
    if not user_id:
        print(f"⚠️ 找不到 {name} 的 LINE userId，略過")
        continue

    lines = [f"{today_display} 會議提醒"]
    for idx, m in enumerate(meetings, start=1):
        lines.append(f"{idx}. {m['title']}")
        lines.append(f"－ 時間：{m['datetime']}")
        lines.append(f"－ 地點：{m['location']}")
        lines.append("")

    message_text = "\n".join(lines).strip()

    try:
        request = PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text=message_text)]
        )
        line_bot_api.push_message(request)
        print(f"✅ 已通知 {name}")
    except Exception as e:
        print(f"❌ 發送給 {name}（{user_id}）失敗：{e}")
