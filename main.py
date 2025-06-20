import os
from datetime import datetime
from notion_client import Client

# 初始化 Notion API 客戶端
notion = Client(auth=os.environ["NOTION_TOKEN"])

# 用來尋找資料庫 ID
def find_database_id_by_name(name):
    results = notion.search(filter={"property": "object", "value": "database"})
    for result in results.get("results", []):
        title_prop = result.get("title", [])
        if title_prop:
            db_title = title_prop[0]["plain_text"]
            if db_title == name:
                return result["id"]
    return None

# 取得資料庫 ID（名稱：測試）
database_name = "測試"
database_id = find_database_id_by_name(database_name)

if not database_id:
    print(f"❌ 找不到資料庫：「{database_name}」")
    exit(1)

# 取得今天日期
today = datetime.now().strftime("%Y-%m-%d")

# 新增一筆資料
notion.pages.create(
    parent={"database_id": database_id},
    properties={
        "日期": {  # ← 對應 Notion 資料庫中 Title 欄位的名稱
            "title": [
                {
                    "text": {
                        "content": today
                    }
                }
            ]
        }
    }
)

print(f"✅ 成功新增一筆資料：{today}")
