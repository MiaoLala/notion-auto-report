import os
import pytz
from datetime import datetime
from notion_client import Client

# 初始化 Notion API
notion = Client(auth=os.environ["NOTION_TOKEN"])

# 設定資料庫 ID
SOURCE_DB_ID = "2182a91a405d80fe82ebc3bf47bfe625" # os.environ["SOURCE_DB_ID"]       # 更新說明的資料庫
ANNOUNCE_DB_ID = "2192a91a405d80eeaaede0b964e6b751" # os.environ["ANNOUNCE_DB_ID"]   # 要寫入佈告的資料庫

# 設定 EBS 子分類順序
EBS_ORDER = [
    "平台系統", "團體系統", "直售系統", "產品系統", "票務系統",
    "商務系統", "電子商務系統", "自由行系統", "訂房系統", "票券系統",
    "國內系統", "入境系統", "包團系統", "人事行政系統", "帳務系統", "客戶系統"
]

# 設定台灣時間
tz = pytz.timezone("Asia/Taipei")
today = datetime.now(tz).strftime("%Y-%m-%d")

# 查詢尚未完成的項目
response = notion.databases.query(
    database_id=SOURCE_DB_ID,
    filter={
        "property": "完成",
        "checkbox": {"equals": False}
    }
)

results = response["results"]
if not results:
    print("✅ 沒有未完成項目，不需新增佈告。")
    exit(0)

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
        system_page = notion.pages.retrieve(rel["id"])
        system_name = system_page["properties"]["名稱"]["title"][0]["plain_text"]
        systems.setdefault(system_name, []).append(title)

# 分類為 EBS 與非 EBS 系統
grouped = {}

for system_name in systems:
    if "－" in system_name:
        main, sub = system_name.split("－", 1)
    else:
        main, sub = system_name, None

    if main == "ＥＢＳ":
        grouped.setdefault(main, {}).setdefault(sub, []).extend(systems[system_name])
    else:
        grouped.setdefault(main, []).extend(systems[system_name])

# 組裝公告內容
content_lines = []

for main in grouped:
    content_lines.append(f"【{main}】")
    if isinstance(grouped[main], dict):  # ＥＢＳ：有子分類
        subs = list(grouped[main].keys())
        ordered = [s for s in EBS_ORDER if s in subs]
        unordered = [s for s in subs if s not in EBS_ORDER]
        for sub in ordered + unordered:
            content_lines.append(sub)
            for idx, item in enumerate(grouped[main][sub], 1):
                content_lines.append(f"{idx}. {item}")
            content_lines.append("")
    else:  # 非ＥＢＳ系統
        for idx, item in enumerate(grouped[main], 1):
            content_lines.append(f"{idx}. {item}")
        content_lines.append("")

content_text = "\n".join(content_lines)

# 寫入「更新佈告」資料庫
notion.pages.create(
    parent={"database_id": ANNOUNCE_DB_ID},
    properties={
        "標題": {
            "title": [{"text": {"content": f"{today} 更新佈告"}}]
        }
    },
    children= [
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
    ]
)

print("✅ 成功產出更新佈告！")
