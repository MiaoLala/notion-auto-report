import os
from datetime import datetime
from notion_client import Client
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging.models import TextMessage, PushMessageRequest

# 初始化 Notion 與 LINE SDK
notion = Client(auth=os.getenv("NOTION_TOKEN"))
line_config = Configuration(access_token=os.getenv("LINE_ACCESS_TOKEN"))

MEETING_DB_ID = "cd784a100f784e15b401155bc3313a1f" # 會議database
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325" # userid database

today_str = datetime.now().date().isoformat()
today_display = datetime.now().strftime("%Y/%m/%d")

# 1️⃣ 查詢今天的會議
print("🔍 查詢今天的會議...")
meeting_pages = notion.databases.query(
    database_id=MEETING_DB_ID,
    filter={
        "and": [
        {
            "property": "日期",
            "date": {
                "on_or_after": today_str,
                "on_or_before": today_str
            }
        },
        {
            "property": "類別",
            "select": {
                "equals": "會議"
            }
        }
    ]
    }
).get("results", [])

for page in meeting_pages:
    print("會議名稱:", page["properties"]["Name"]["title"][0]["text"]["content"])
    print("日期欄位:", page["properties"]["日期"]["date"]["start"])

if not meeting_pages:
    print("✅ 今天沒有會議")
    exit(0)

# 2️⃣ 讀取使用者對照表（Name -> userId）
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

# 3️⃣ 處理每一場會議，分類給每位與會者
for page in meeting_pages:
    props = page["properties"]
    title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "未命名會議"

    # 日期＋時間
    datetime_str = props["日期"]["date"]["start"]
    date_time = datetime.fromisoformat(datetime_str).strftime("%Y/%m/%d %H:%M")

    # 地點（Select）
    # 地點欄位安全擷取
    location_prop = props.get("地點")
    if location_prop and location_prop.get("select"):
        location = location_prop["select"]["name"]
    else:
        location = "未填寫"

    # 相關人員（Person）
    persons = props.get("相關人員", {}).get("people", [])
    attendee_names = [p["name"] for p in persons]
    
    # 將含有該 user_map 的 key（員編）者視為與會
    for attendee in attendee_names:
        for code in user_map.keys():  # 例如 "7701", "1234"
            if code in attendee:
                # 加上判斷：只加入今天的
                if datetime_str[:10] == today_str:
                    user_meetings[code].append({
                        "title": title,
                        "datetime": date_time,
                        "location": location
                    })

print(f"🧾 與會者名稱：{attendee_names}")
print(f"✅ 有符合的使用者 code：{code}")

# 4️⃣ 傳送 LINE 通知（用 LINE SDK v3）
print("📨 傳送 LINE 通知中...")
with ApiClient(line_config) as api_client:
    line_bot_api = MessagingApi(api_client)

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
