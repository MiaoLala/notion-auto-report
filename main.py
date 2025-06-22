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
ec_summary_lines = []  # for EC 訊息內容

for main_system, system_data in grouped.items():
    content_lines.append(f"【{main_system}】")

    # 若非 EBS，記錄系統標題到 EC 區塊
    if main_system != "ＥＢＳ":
        ec_summary_lines.append(f"【{main_system}】")

    if isinstance(system_data, dict):  # EBS 有子分類
        subs = list(system_data.keys())
        ordered = [s for s in EBS_ORDER if s in subs]
        unordered = [s for s in subs if s not in EBS_ORDER]

        for sub in ordered + unordered:
            content_lines.append(sub)
            for idx, item in enumerate(system_data[sub], 1):
                content_lines.append(f"{idx}. {item}")
            content_lines.append("")  # 空行隔開
    else:  # 非 EBS 系統
        for idx, item in enumerate(system_data, 1):
            content_lines.append(f"{idx}. {item}")
            ec_summary_lines.append(f"{idx}. {item}")
        content_lines.append("")

# Notion content 組成
content_text = "\n".join(content_lines)

# EC summary block 組成
ec_summary_text = (
    "12:00 壓\n"
    "13:00 放\n\n"
    "更新說明如下\n"
    "--------------------------------------------\n" +
    "\n".join(ec_summary_lines)
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
notion.pages.create(
    parent={"database_id": ANNOUNCE_DB_ID},
    properties={
        "標題": {
            "title": [{"text": {"content": f"{today} 更新佈告"}}]
        }
    },
    children= ebs_blocks + blocks
)

print("✅ 成功產出更新佈告！")
