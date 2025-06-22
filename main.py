import os
import requests
from datetime import datetime
import pytz
from notion_client import Client

# ✅ 環境變數
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
SOURCE_DB_ID = "2182a91a405d80fe82ebc3bf47bfe625" # os.environ["SOURCE_DB_ID"]       # 更新說明的資料庫
ANNOUNCE_DB_ID = "2192a91a405d80eeaaede0b964e6b751" # os.environ["ANNOUNCE_DB_ID"]   # 要寫入佈告的資料庫
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_IDS = os.environ["LINE_USER_IDS"].split(",")  # 多位用逗號分隔

# ✅ 初始化
notion = Client(auth=NOTION_TOKEN)
tz = pytz.timezone("Asia/Taipei")
today = datetime.now(tz).strftime("%Y-%m-%d")

# ✅ 發送 LINE 訊息函式
def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    for user_id in LINE_USER_IDS:
        data = {
            "to": user_id.strip(),
            "messages": [{"type": "text", "text": message}]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"❌ LINE 發送失敗（{user_id}）：{response.status_code}, {response.text}")
        else:
            print(f"✅ 已發送給 {user_id}")

# ✅ 查詢未完成項目
response = notion.databases.query(
    **{
        "database_id": SOURCE_DB_ID,
        "filter": {
            "property": "完成",
            "checkbox": {"equals": False}
        }
    }
)

results = response["results"]

if not results:
    send_line_message("✅ 沒有未完成項目，不需新增佈告。")
    exit(0)

# ✅ 整理系統資料
ebs_system_order = [
    "平台系統", "團體系統", "直售系統", "產品系統", "票務系統", "商務系統", "電子商務系統",
    "自由行系統", "訂房系統", "票券系統", "國內系統", "入境系統", "包團系統",
    "人事行政系統", "帳務系統", "客戶系統"
]

grouped = {}
for page in results:
    props = page["properties"]
    system_names = []
    if "系統" in props and props["系統"]["type"] == "relation":
        system_names = [rel.get("name") for rel in props["系統"]["relation"] if "name" in rel]
    for name in system_names:
        group = "ＥＢＳ" if "ＥＢＳ" in name else name
        subgroup = name.replace("ＥＢＳ－", "") if group == "ＥＢＳ" else name
        grouped.setdefault(group, {}).setdefault(subgroup, []).append(page)

# ✅ 整理 EBS 區塊
ebs_lines = []
for sys in ebs_system_order:
    if sys in grouped.get("ＥＢＳ", {}):
        ebs_lines.append(f"{len(ebs_lines)+1}. {sys}")

content_text = "【ＥＢＳ】\n" + "\n".join(ebs_lines) if ebs_lines else ""

# ✅ 整理非ＥＢＳ（EC）系統內容
non_ebs_grouped = {k: v for k, v in grouped.items() if k != "ＥＢＳ"}
ec_summary_text = """12:00 壓
13:00 放

更新說明如下
--------------------------------------------"""

for system in sorted(non_ebs_grouped.keys()):
    if non_ebs_grouped[system]:
        ec_summary_text += f"\n【{system}】"

# ✅ 組合 blocks 結構
blocks = [
    {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "ＥＣ"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "標題（請自行修改須更新站台）"}}]
        }
    },
    {
        "object": "block",
        "type": "code",
        "code": {
            "language": "html",
            "rich_text": [{
                "type": "text",
                "text": {"content": "今日更新【EC】12:00 壓 13:00放，有問題請通知我，謝謝"}
            }]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "訊息內容（不須更新站台可刪除）"}}]
        }
    },
    {
        "object": "block",
        "type": "code",
        "code": {
            "language": "plain text",
            "rich_text": [{"type": "text", "text": {"content": ec_summary_text}}]
        }
    }
]

# ✅ 加入 EBS block
if content_text:
    blocks.append({
        "object": "block",
        "type": "code",
        "code": {
            "language": "plain text",
            "rich_text": [{"type": "text", "text": {"content": content_text}}]
        }
    })

# ✅ 建立佈告 page
new_page = notion.pages.create(
    parent={"database_id": ANNOUNCE_DB_ID},
    properties={
        "標題": {
            "title": [{"text": {"content": f"{today} 更新佈告"}}]
        }
    },
    children=blocks
)

# ✅ 發送通知
send_line_message(f"✅ 已產出更新佈告\n🔗 {new_page['url']}")
