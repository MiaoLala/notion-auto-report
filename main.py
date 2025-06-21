import os
from datetime import datetime
from notion_client import Client

# 初始化 Notion
notion = Client(auth=os.environ["NOTION_TOKEN"])

# 設定資料庫 ID（請替換成你的）
UPDATE_DB_ID = "2182a91a405d80fe82ebc3bf47bfe625"
BULLETIN_DB_ID = "2192a91a405d80eeaaede0b964e6b751"

# 今日日期
# 取得台灣現在時間
tz = pytz.timezone("Asia/Taipei")
now_taipei = datetime.now(tz)
today_str = now_taipei.strftime("%Y-%m-%d")

# 查詢尚未完成的項目
response = notion.databases.query(
    **{
        "database_id": UPDATE_DB_ID,
        "filter": {
            "property": "完成",
            "checkbox": {"equals": False}
        }
    }
)

# 整理系統與更新內容
systems = {}  # ex: {"團體系統": ["修正錯誤", "新增功能"]}

for row in response["results"]:
    title = row["properties"]["更新說明"]["title"][0]["text"]["content"]
    system_rels = row["properties"]["系統"]["relation"]

    for sys in system_rels:
        system_page = notion.pages.retrieve(sys["id"])
        system_name = system_page["properties"]["名稱"]["title"][0]["text"]["content"]
        # 將子系統歸入 EBS 分類（若有多平台可擴充）
        systems.setdefault(system_name, []).append(title)

# 若沒有任何未完成項目就不新增公告
if not systems:
    print("✅ 沒有未完成項目，不需新增佈告。")
    exit()

# 整理成公告格式
grouped = {}

for system_name in systems:
    # 假設命名都是 EBS－XXX
    if "－" in system_name:
        main, sub = system_name.split("－", 1)
    else:
        main, sub = "其他", system_name
    grouped.setdefault(main, {}).setdefault(sub, []).extend(systems[system_name])

# 排版內容
content_lines = []
for main in grouped:
    content_lines.append(f"【{main}】")
    for sub in grouped[main]:
        content_lines.append(sub)
        for idx, item in enumerate(grouped[main][sub], 1):
            content_lines.append(f"{idx}. {item}")
        content_lines.append("")  # 分隔空行

bulletin_text = "\n".join(content_lines)

# 建立佈告頁面
notion.pages.create(
    parent={"database_id": BULLETIN_DB_ID},
    properties={
        "標題": {
            "title": [
                {
                    "text": {"content": today_str}
                }
            ]
        }
    },
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": bulletin_text}
                }]
            }
        }
    ]
)

print("✅ 成功新增一則更新佈告。")
