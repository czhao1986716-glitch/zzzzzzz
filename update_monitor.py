import requests
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- 核心配置 ---
RUNE_ID = "927500:732"
PROJECT_NAME = "ZZZZZZZ 持币监控大盘"
DATA_DIR = "data"

def get_current_from_api():
    """从 API 获取原始数据"""
    holders = []
    offset, limit = 0, 60
    while True:
        try:
            url = f"https://api.hiro.so/runes/v1/etchings/{RUNE_ID}/holders?offset={offset}&limit={limit}"
            res = requests.get(url, timeout=20).json()
            results = res.get("results", [])
            if not results: break
            for r in results:
                holders.append({"address": r["address"], "current_amount": float(r["balance"])})
            offset += limit
            if len(results) < limit: break
        except Exception:
            break
    return pd.DataFrame(holders)

def main():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    
    # 1. 加载初始数据
    init_path = os.path.join(DATA_DIR, "initial.json")
    init_df = pd.DataFrame(columns=["address", "initial_amount"])
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            init_df = pd.DataFrame(json.load(f)).rename(columns={"amount": "initial_amount"})

    # 2. 获取实时数据
    today_df = get_current_from_api()
    if today_df.empty:
        print("❌ 无法获取 API 数据")
        return

    # 计算北京时间 (UTC+8)
    beijing_time = datetime.utcnow() + timedelta(hours=8)
    today_str = beijing_time.strftime("%Y-%m-%d")
    full_time_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 保存今日快照
    today_df.to_json(os.path.join(DATA_DIR, f"{today_str}.json"), orient="records")

    # 3. 提取历史趋势与昨日对比
    history_map = {}
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("202") and f.endswith(".json")])
    
    for file in all_files:
        with open(os.path.join(DATA_DIR, file), 'r') as f:
            day_data = json.load(f)
            for item in day_data:
                addr = item['address']
                if addr not in history_map: history_map[addr] = []
                history_map[addr].append(item.get('current_amount', 0))

    yesterday_map = {}
    if len(all_files) >= 2:
        with open(os.path.join(DATA_DIR, all_files[-2]), 'r') as f:
            for item in json.load(f):
                yesterday_map[item['address']] = item['current_amount']

    # 顶部显示：当前余额大于 0 的地址数
    active_holders_count = len(today_df[today_df['current_amount'] > 0])
    
    generate_modern_html(today_df, init_df, yesterday_map, history_map, full_time_str, active_holders_count)

def generate_modern_html(today_df, init_df, yesterday_map, history_map, time_label, active_count):
    table_rows = ""
    # 逻辑排序：按持币量降序
    today_df = today_df.sort_values(by="current_amount", ascending=False)
    
    for _, row in today_df.iterrows():
        addr = row['address']
        curr_amt = row['current_amount']
        
        init_match = init_df[init_df['address'] == addr]
        i_amt = init_match['initial_amount'].values[0] if not init_match.empty else 0
        y_amt = yesterday_map.get(addr, i_amt)
        diff = curr_amt - y_amt
        trend_str = ",".join(map(str, history_map.get(addr, [curr_amt])))

        tag = "🏠 ORIGINAL" if i_amt > 0 else "✨ NEW"
        tag_cls = "tag-orig" if i_amt > 0 else "tag-new"
        
        row_style = "opacity: 0.6; background: #fafafa;" if curr_amt == 0 else ""
        amt_display = f"{curr_amt:,.0f}" if curr_amt > 0 else '<span style="color:#94a3b8">SOLD OUT</span>'
        
        change_cls = "pos" if diff > 0 else ("neg" if diff < 0 else "neutral")
        change_icon = "+" if diff > 0 else ""

        table_rows += f"""
        <tr style="{row_style}">
            <td class="addr-cell" title="{addr}">{addr[:8]}...{addr[-8:]}</td>
            <td><span class="tag {tag_cls}">{tag}</span></td>
            <td class="num">{i_amt:,.0f}</td>
            <td class="num">{y_amt:,.0f}</td>
            <td class="num current" data-order="{curr_amt}"><strong>{amt_display}</strong></td>
            <td class="num {change_cls}" data-order="{diff}">{change_icon}{diff:,.0f}</td>
            <td class="chart-cell"><span class="sparkline">{trend_str}</span></td>
        </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <title>{PROJECT_NAME}</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <style>
            :root {{ --bg: #f8fafc; --card: #ffffff; --primary: #1e293b; --accent: #3b82f6; --pos: #10b981; --neg: #ef4444; }}
            body {{ background: var(--bg); font-family: -apple-system, system-ui, sans-serif; color: var(--primary); margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: var(--card); padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .header-info {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 25px; border-bottom: 1px solid #edf2f7; padding-bottom: 20px; }}
            .stats-box {{ display: flex; gap: 40px; }}
            .stat-item {{ display: flex; flex-direction: column; }}
            .stat-value {{ font-size: 26px; font-weight: 800; color: var(--accent); }}
            .stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 4px; font-weight: 600; }}
            .time-tag {{ font-size: 13px; color: #94a3b8; background: #f1f5f9; padding: 6px 12px; border-radius: 6px; }}
            table.dataTable thead th {{ background: #f8fafc; color: #64748b; font-size: 12px; padding: 15px; border: none !important; }}
            .addr-cell {{ font-family: monospace; color: var(--accent); font-size: 13px; }}
            .num {{ text-align: right !important; font-variant-numeric: tabular-nums; }}
            .tag {{ font-size: 10px; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
            .tag-orig {{ background: #eff6ff; color: #2563eb; }}
            .tag-new {{ background: #ecfdf5; color: #059669; }}
            .pos {{ color: var(--pos); font-weight: 600; }}
            .neg {{ color: var(--neg); font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-info">
                <div class="stats-box">
                    <div class="stat-item"><span class="stat-value">ZZZZZZZ</span><span class="stat-label">Project</span></div>
                    <div class="stat-item"><span class="stat-value" style="color:var(--pos);">{active_count}</span><span class="stat-label">Active Holders</span></div>
                </div>
                <div class="time-tag">⏰ 更新 (北京时间): {time_label}</div>
            </div>
            <table id="holderTable" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>持币地址</th>
                        <th>身份</th>
                        <th>初始数量</th>
                        <th>昨日数量</th>
                        <th>今日实时</th>
                        <th>24H 变化</th>
                        <th>历史趋势</th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jquery-sparkline@2.4.0/jquery.sparkline.min.js"></script>
        <script>
            $(document).ready(function() {{
                $('#holderTable').DataTable({{ 
                    paging: false, 
                    scrollY: '75vh', 
                    scrollCollapse: true, 
                    order: [[4, 'desc']], // 默认按第 5 列（今日实时）降序排序
                    language: {{ search: "搜索地址:" }} 
                }});
                $('.sparkline').sparkline('html', {{ type: 'line', width: '90px', height: '30px', lineColor: '#3b82f6', fillColor: '#dbeafe', lineWidth: 2, spotColor: false, minSpotColor: false, maxSpotColor: false }});
            }});
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)

if __name__ == "__main__": main()
