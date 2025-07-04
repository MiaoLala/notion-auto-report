import os
import time
import pytz
import requests
from datetime import datetime
from notion_client import Client
import threading

# === Retry 機制 ===
def with_retry(func, max_attempts=3, delay=5, allowed_exceptions=(Exception,)):
    for attempt in range(max_attempts):
        try:
            return func()
        except allowed_exceptions as e:
            print(f"Retry {attempt + 1}/{max_attempts} failed: {e}")
            time.sleep(delay)
    raise RuntimeError("Failed after max retries")

# 初始化 Notion API
notion = Client(auth=os.environ["NOTION_TOKEN"])

# 設定LINE變數
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_IDS = [
    "Ueac062fbefdeffa4bc3a4020db58fff6",  # 使用者
    # 依需要可再增加
]
# 設定資料庫 ID
SOURCE_DB_ID = "211d8d0b09f1809fb9aee315fd27fc8e" # os.environ["SOURCE_DB_ID"]       # 更新說明的資料庫
ANNOUNCE_DB_ID = "211d8d0b09f18048bfa1dfae66ded144" # os.environ["ANNOUNCE_DB_ID"]   # 要寫入佈告的資料庫
NOTION_LOG_PAGE_ID = "21dd8d0b09f180f2a909eb135c627f9b"  # LOG Page ID

# 設定 EBS 子分類順序
EBS_ORDER = [
    "平台", "團體系統", "直售系統", "產品系統", "票務系統",
    "商務系統", "電子商務系統", "自由行系統", "訂房系統", "票券系統",
    "國內系統", "入境系統", "包團系統", "財務系統", "人事行政系統", "帳務系統", "客戶系統"
]

# 設定非 EBS 分類順序
NON_EBS_ORDER = [
    "Ｂ２Ｃ", "Ｂ２Ｂ", "Ｂ２Ｅ", "Ｂ２Ｓ",
    "ＣｏｌａＡＰＩ", "ＷｅｂＡＰＩ", "前端", "ＢＢＣ", "ＳＵＲＬ"
]

# 限定要整理的系統
TARGET_SYSTEMS = ["ＥＢＳ", "Ｂ２Ｃ", "Ｂ２Ｂ", "Ｂ２Ｅ", "Ｂ２Ｓ"]

# 設定台灣時間
tz = pytz.timezone("Asia/Taipei")
now = datetime.now(tz)
today = datetime.now(tz).strftime("%Y/%m/%d")


def log_to_notion_title(text: str):
    print(text)  # 保留原本 console print
    # 寫入 Notion page 的 title
    notion.pages.update(
        page_id=NOTION_LOG_PAGE_ID,
        properties={
            "標題": {
                "title": [{
                    "text": {"content": text[:200]}  # Notion title 長度限制
                }]
            }
        }
    )

    # 啟動一個 background thread，1 分鐘後清空 title
    def clear_title():
        time.sleep(10)
        notion.pages.update(
            page_id=NOTION_LOG_PAGE_ID,
            properties={
                "標題": {
                    "title": [{
                        "text": {"content": "---"} 
                    }]
                }
            }
        )
    threading.Thread(target=clear_title, daemon=True).start()
    
# line 發送訊息

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
            print(f"❌ LINE 發送失敗 → {user_id}：{response.status_code} {response.text}")

def get_today_announcement_title():
    today = datetime.now().strftime("%Y/%m/%d")
    return f"{today} 更新佈告"

def has_today_announcement():
    today_title = get_today_announcement_title()
    
    response = notion.databases.query(
        database_id=ANNOUNCE_DB_ID,
        filter={
            "property": "標題",
            "title": {
                "equals": today_title
            }
        }
    )
    return len(response["results"]) > 0

# ✅ 加入防重送與「非週二不執行」邏輯
if now.weekday() != 1:
    print("⛔ 今天不是週二，不執行更新佈告產出流程。")
    log_to_notion_title("⛔ 今天不是週二，不執行更新佈告產出流程。")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        time.sleep(65)
    exit(0)

# ✅ 防重送判斷（直接執行）
if has_today_announcement():
    print("⛔ 今日已產生過更新佈告，流程中止")
    log_to_notion_title("⛔ 今日已產生過更新佈告，流程中止")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        time.sleep(65)
    exit(0)

print("🚀 尚未產生，準備建立新佈告...")

# 查詢尚未完成的項目
response = with_retry(lambda: notion.databases.query(
     database_id=SOURCE_DB_ID,
    filter={
        "property": "完成",
        "checkbox": {"equals": False}
    },
    sorts=[
        {
            "property": "更新日期",  # 你在 Notion database 裡的欄位名稱（類型需為日期或時間戳）
            "direction": "ascending"  # 正序排列，可用 "descending" 表示反序
        }
    ]
))

results = response["results"]
if not results:
    print("⛔ 沒有更新說明項目，不需新增佈告。")
    log_to_notion_title("⛔ 沒有更新說明項目，不需新增佈告。")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        time.sleep(65)
    exit(0)

log_to_notion_title("⚠️ 佈告產生中，請耐心等待．．．")

# 整理資料
systems = {}
for row in results:
    props = row["properties"]
    title = props["更新說明"]["title"][0]["plain_text"] if props["更新說明"]["title"] else "（無標題）"
    relations = props["系統"]["relation"]
    if not relations:
        system_name = "未指定系統"
        systems.setdefault(system_name, []).append(title)
        continue

    for rel in relations:
        system_page = with_retry(lambda: notion.pages.retrieve(rel["id"]))
        system_name = system_page["properties"]["系統名稱"]["title"][0]["plain_text"]
        systems.setdefault(system_name, []).append(title)

# 分類為 EBS 與非 EBS 系統
grouped = {}

for system_name in systems:
    if "－" in system_name:
        main_name, sub = system_name.split("－", 1)
    else:
        main_name, sub = system_name, None

    if main_name == "ＥＢＳ":
        grouped.setdefault(main_name, {}).setdefault(sub, []).extend(systems[system_name])
    else:
        grouped.setdefault(main_name, []).extend(systems[system_name])

# 組裝公告內容
content_lines = []
ec_summary_lines = []

# 1. 處理 EBS 區塊
if "ＥＢＳ" in grouped:
    content_lines.append("【ＥＢＳ】")
    ebs_data = grouped["ＥＢＳ"]
    subs = list(ebs_data.keys())
    ordered = [s for s in EBS_ORDER if s in subs]
    unordered = [s for s in subs if s not in EBS_ORDER]

    for sub in ordered + unordered:
        content_lines.append(sub)
        for idx, item in enumerate(ebs_data[sub], 1):
            content_lines.append(f"{idx}. {item}")
        content_lines.append("")

# 2. 處理 NON-EBS 區塊
for sys in NON_EBS_ORDER:
    if sys in grouped:
        sys_items_dict = grouped[sys]
        
        # 判斷是 dict（預期格式）還是直接 list（兼容其他來源）
        if isinstance(sys_items_dict, dict):
            items = sys_items_dict.get("", [])
        else:
            items = sys_items_dict
        
        if not items:
            continue

        # 對 content_lines：只處理 B2X
        if sys in ["Ｂ２Ｃ", "Ｂ２Ｂ", "Ｂ２Ｅ", "Ｂ２Ｓ"]:
            content_lines.append(f"【{sys}】")
            for idx, item in enumerate(items, 1):
                content_lines.append(f"{idx}. {item}")
            content_lines.append("")

        # 對 ec_summary_lines：所有 NON_EBS_ORDER 皆處理
        ec_summary_lines.append(f"【{sys}】")
        for idx, item in enumerate(items, 1):
            ec_summary_lines.append(f"{idx}. {item}")
        ec_summary_lines.append("")
        
# Notion content 組成
content_text = "\n".join(content_lines).strip()
content_text += "\n\n\n****** 如欲了解更新詳細內容，請聯絡需求窗口 ******"
ec_summary_text_children = "\n".join(ec_summary_lines).strip()

# EC summary block 組成
ec_summary_text = (
    "12:00 壓\n"
    "13:00 放\n\n"
    "更新說明如下\n"
    "--------------------------------------------\n" + ec_summary_text_children
)

# 組合EBS固定文字

# 訊息發送 summary block 組成
ebs_summary_text = (
    "12:00 壓\n"
    "13:00 放\n\n"
    "更新說明如下\n"
    "--------------------------------------------\n"
    "【EBSB】\n\n"
    "【EBSC】"
)

ebs_blocks = [
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "訊息發送"}}]
        }
    },
    {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "ＥＢＳ"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "標題"}}]
        }
    },
    {
        "object": "block",
        "type": "code",
        "code": {
            "language": "html",
            "rich_text": [{
                "type": "text",
                "text": {"content": "今日更新【EBS】12:00 壓 13:00放，有問題請通知我，謝謝"}
            }]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "訊息內容（請自行查閱A00C004目前在B或C上的程式）"}}]
        }
    },
    {
        "object": "block",
        "type": "code",
        "code": {
            "language": "plain text",
            "rich_text": [{"type": "text", "text": {"content": ebs_summary_text}}]
        }
    }
]

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

callout_text = """佈告發送說明：
1. 主題類別：資訊─程式功能更新
2. 張貼天數：7天
3. 佈告欄：可樂佈告欄
4. 主旨：本周各系統程式更新公告
5. 「勾」重要公告，「不勾」允許列印
6. 張貼內容請用文字標題區分各網站，例如【ＥＢＳ】【Ｂ２Ｃ】...，各系統文字請用"藍色"表示
7. 文末請將下方文字改為紅字
****** 如欲了解更新詳細內容，請聯絡需求窗口 ******
8. 請將需求窗口連結到user（請善用編輯器功能）"""

# ✅ 加入 EBS block
if content_text:
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "更新佈告"}}]
            }
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {
                    "type": "emoji",
                    "emoji": "📢"
                },
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": callout_text
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "標題"}}]
            }
        },
        {
            "object": "block",
            "type": "code",
            "code": {
                "language": "html",
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "本周各系統程式更新公告"}
                }]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "佈告內容"}}]
            }
        },
        {
            "object": "block",
            "type": "code",
            "code": {
                "language": "plain text",
                "rich_text": [{
                    "type": "text",
                    "text": {"content": content_text}
                }]
            }
        }
    ])


# 寫入「更新佈告」資料庫
new_page = with_retry(lambda: notion.pages.create(
    parent={"database_id": ANNOUNCE_DB_ID},
    properties={
        "標題": {
            "title": [{"text": {"content": f"{today} 更新佈告"}}]
        },
        "時間":{
            "date": {
                "start": datetime.now().strftime("%Y-%m-%d")
            }
        }
    },
    children= ebs_blocks + blocks,
    icon={
        "type": "emoji",
        "emoji": "⭐"
    }
))

print("✅ 成功產出更新佈告！")
log_to_notion_title("✅ 成功產出更新佈告！")
if os.environ.get("GITHUB_ACTIONS") == "true":
    time.sleep(20)

# ✅ 發送通知
# send_line_message(LINE_USER_IDS, f"✅ 已產出更新佈告\n🔗 {new_page['url']}")

