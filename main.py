import os
from datetime import datetime
from notion_client import Client

# 初始化 Notion API 客戶端
notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["NOTION_DATABASE_ID"]

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
