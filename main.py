import os
import requests
from datetime import datetime
from notion_client import Client

# 初始化 Notion API
notion = Client(auth=os.environ["NOTION_TOKEN"])

# 你更新說明的資料庫 ID
SOURCE_DB_ID = "2182a91a405d80fe82ebc3bf47bfe625"  # os.environ["SOURCE_DB_ID"]
ANNOUNCE_DB_ID = "2192a91a405d80eeaaede0b964e6b751"  # os.environ["ANNOUNCE_DB_ID"]

# LINE 設定
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
LINE_USER_ID = "你要發送的用戶ID"

def send_line_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 200:
        print(f"LINE 發送失敗：{resp.status_code} {resp.text}")
    else:
        print("LINE 發送成功")

def get_unfinished_items():
    results = []
    next_cursor = None
    while True:
        response = notion.databases.query(
            **{
                "database_id": SOURCE_DB_ID,
                "filter": {
                    "property": "完成",
                    "checkbox": {"equals": False}
                },
                "start_cursor": next_cursor
            }
        )
        results.extend(response["results"])
        if not response.get("has_more"):
            break
        next_cursor = response.get("next_cursor")
    return results

def group_items_by_system(items):
    grouped = {}
    for item in items:
        sys_rels = item["properties"].get("系統", {}).get("relation", [])
        for rel in sys_rels:
            sys_name = rel.get("name", "").strip()
            if not sys_name:
                continue
            # 簡化系統大分類，例如 B2C－調整項目 只保留 B2C
            main_sys = sys_name.split("－")[0] if "－" in sys_name else sys_name

            if main_sys not in grouped:
                grouped[main_sys] = {}

            # 對於 EBS 系統，子分類為系統名後半段
            if main_sys == "ＥＢＳ":
                sub_sys = sys_name.split("－")[1] if "－" in sys_name else "未分類"
                if sub_sys not in grouped[main_sys]:
                    grouped[main_sys][sub_sys] = []
                grouped[main_sys][sub_sys].append(item)
            else:
                if "" not in grouped[main_sys]:
                    grouped[main_sys][""] = []
                grouped[main_sys][""].append(item)
    return grouped

def format_update_lines(items):
    lines = []
    for idx, item in enumerate(items, 1):
        title_prop = item["properties"].get("更新說明", {})
        # 取得 title 欄位文字
        title_text = ""
        if title_prop.get("title"):
            title_text = "".join([t.get("plain_text", "") for t in title_prop["title"]])
        lines.append(f"{idx}. {title_text}")
    return lines

def create_notion_announcement_page(grouped_systems):
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"{today} 更新佈告"

    # --- EC 第一段固定格式 ---
    non_ebs_grouped = {k: v for k, v in grouped_systems.items() if k != "ＥＢＳ"}

    ec_summary_text = """12:00 壓
13:00 放

更新說明如下
--------------------------------------------"""

    for system in sorted(non_ebs_grouped.keys()):
        if non_ebs_grouped[system]:
            ec_summary_text += f"\n【{system}】"

    ec_fixed_blocks = [
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

    # --- 第二段：所有系統更新明細 ---
    blocks = []

    ebs_order = [
        "平台系統", "團體系統", "直售系統", "產品系統", "票務系統", "商務系統",
        "電子商務系統", "自由行系統", "訂房系統", "票券系統", "國內系統", "入境系統",
        "包團系統", "人事行政系統", "帳務系統", "客戶系統"
    ]

    for sys_name, subsys_dict in grouped_systems.items():
        # 系統標題區塊
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": [{"type": "text", "text": {"content": f"【{sys_name}】"}}]
        })

        if sys_name == "ＥＢＳ":
            # EBS 有子分類，子分類不編號
            for sub_sys in ebs_order:
                if sub_sys in subsys_dict:
                    # 子分類名稱段落
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": [{"type": "text", "text": {"content": sub_sys}}]
                    })
                    # 該子分類更新項目（編號）
                    lines = format_update_lines(subsys_dict[sub_sys])
                    for line in lines:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": [{"type": "text", "text": {"content": line}}]
                        })
            # 若還有 EBS 但不在順序列表的子分類也列出
            for sub_sys in subsys_dict:
                if sub_sys not in ebs_order:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": [{"type": "text", "text": {"content": sub_sys}}]
                    })
                    lines = format_update_lines(subsys_dict[sub_sys])
                    for line in lines:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": [{"type": "text", "text": {"content": line}}]
                        })
        else:
            # 其他系統：全部合併（子分類 key 是空字串 ""）
            items = subsys_dict.get("", [])
            if items:
                lines = format_update_lines(items)
                for line in lines:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": [{"type": "text", "text": {"content": line}}]
                    })

    # 合併所有區塊
    all_blocks = ec_fixed_blocks + blocks

    # 建立 Notion 頁面
    new_page = notion.pages.create(
        parent={"database_id": ANNOUNCE_DB_ID},
        properties={
            "標題": {
                "title": [
                    {"type": "text", "text": {"content": title}}
                ]
            }
        },
        children=all_blocks
    )
    return new_page

def main():
    items = get_unfinished_items()
    if not items:
        print("✅ 沒有未完成項目，不需新增佈告。")
        return

    grouped = group_items_by_system(items)
    page = create_notion_announcement_page(grouped)

    # 你可以根據需求動態產生發送LINE的訊息內容
    ec_line_message = (
        "今日更新【EC】12:00 壓 13:00放，有問題請通知我，謝謝\n\n"
        "12:00 壓\n"
        "13:00 放\n\n"
        "更新說明如下\n"
        "--------------------------------------------\n"
        "【B2C】\n\n"
        "【B2B】\n\n"
        "【B2E】\n\n"
        "【B2S】"
    )

    send_line_message(LINE_USER_ID, ec_line_message)

    print("Notion 佈告頁面網址:", page["url"])

if __name__ == "__main__":
    main()
