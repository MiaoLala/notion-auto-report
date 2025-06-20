import os
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["NOTION_DATABASE_ID"]

response = notion.databases.query(
    database_id=database_id,
    filter={
        "property": "完成",
        "checkbox": {"equals": True}
    }
)

grouped = {}
for page in response["results"]:
    props = page["properties"]
    system = props["系統分類"]["select"]["name"]
    update = props["更新說明"]["rich_text"][0]["plain_text"]
    grouped.setdefault(system, []).append(update)

print("【ＥＢＳ】\n")
for group in [
    "團體系統", "直售系統", "產品系統", "票務系統", "商務系統", "電子商務系統", "自由行系統",
    "全球訂房系統", "票券系統", "國內系統", "入境系統", "包團系統", "財務系統", "人事行政系統",
    "客戶系統", "帳務系統"
]:
    print(f"### {group}")
    if group in grouped:
        for note in grouped[group]:
            print(f"- {note}")
    else:
        print("- 無")
    print()
