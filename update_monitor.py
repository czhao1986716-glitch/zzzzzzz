import requests
import pandas as pd
import json
import os
import webbrowser
from datetime import datetime

# --- 配置 ---
RUNE_ID = "927500:732"
DATA_DIR = "data"

def get_current_from_api():
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
        except: break
    return pd.DataFrame(holders)

def main():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    
    # 1. 加载初始数据
    init_path = os.path.join(DATA_DIR, "initial.json")
    init_df = pd.DataFrame(columns=["address", "initial_amount"])
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            init_df = pd.DataFrame(json.load(f)).rename(columns={"amount": "initial_amount"})

    # 2. 获取实时数据并存快照
    today_df = get_current_from_api()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_df.to_json(os.path.join(DATA_DIR, f"{today_str}.json"), orient="records")

    # 3. 提取历史趋势数据 (以地址为 Key，存储日期序列)
    history_map = {}
    all_files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("202") and f.endswith(".json")])
    
    for file in all_files:
        with open(os.path.join(DATA_DIR, file), 'r') as f:
            day_data = json.load(f)
            for item in day_data:
                addr = item['address']
                amt = item.get('current_amount', 0)
                if addr not in history_map: history_map[addr] = []
                history_map[addr].append(amt)

    # 4. 数据合并
    # 找昨日对比
    yesterday_amount_map = {}
    if len(all_files) >= 2:
        with open(os.path.join(DATA_DIR, all_files[-2]), 'r') as f:
            for item in json.load(f):
                yesterday_amount_map[item['address']] = item['current_amount']

    # 5. 生成 HTML
    generate_modern_html(today_df, init_df, yesterday_amount_map, history_map, today_str)

def generate_modern_html(today_df, init_df, yesterday_map, history_map, date_str):
    table_rows = ""
    # 按当前持币量排序
    today_df = today_df.sort_values(by="current_amount", ascending=False)
    
    for _, row in today_df.iterrows():
        addr = row['address']
        curr_amt = row['current_amount']
        
        # 初始数量
        init_match = init_df[init_df['address'] == addr]
        i_amt = init_match['initial_amount'].values[0] if not init_match.empty else 0
        
        # 昨日变动
        y_amt = yesterday_map.get(addr, i_amt)
        diff = curr_amt - y_amt
        
        # 趋势数据格式化为字符串 "10,20,30"
        trend_list = history_map.get(addr, [curr_amt])
        trend_str = ",".join(map(str, trend_list))

        # 样式逻辑
        tag = "🏠 ORIGINAL" if i_amt > 0 else "✨ NEW"
        tag_cls = "tag-orig" if i_amt > 0 else "tag-new"
        change_cls = "pos" if diff > 0 else ("neg" if diff < 0 else "neutral")
        change_icon = "↑" if diff > 0 else ("↓" if diff < 0 else "-")

        table_rows += f"""
        <tr>
            <td class="addr-cell" title="{addr}">{addr[:8]}...{addr[-8:]}</td>
            <td><span class="tag {tag_cls}">{tag}</span></td>
            <td class="num">{i_amt:,.0f}</td>
            <td class="num">{y_amt:,.0f}</td>
            <td class="num current"><strong>{curr_amt:,.0f}</strong></td>
            <td class="num {change_cls}" data-order="{diff}">{change_icon} {abs(diff):,.0f}</td>
            <td class="chart-cell"><span class="sparkline">{trend_str}</span></td>
        </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <title>ZZZZZZZ Holder Analytics</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <style>
            :root {{ --bg: #f8fafc; --card: #ffffff; --primary: #1e293b; --accent: #3b82f6; --pos: #10b981; --neg: #ef4444; }}
            body {{ background: var(--bg); font-family: 'Inter', -apple-system, sans-serif; color: var(--primary); margin: 0; padding: 40px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: var(--card); padding: 32px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); }}
            header {{ margin-bottom: 32px; border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; }}
            h1 {{ margin: 0; font-size: 24px; letter-spacing: -0.5px; }}
            .status {{ color: #64748b; font-size: 14px; margin-top: 8px; }}
            
            table.dataTable {{ border: none !important; border-collapse: collapse !important; }}
            table.dataTable thead th {{ background: #f1f5f9; color: #475569; font-weight: 600; font-size: 12px; text-transform: uppercase; padding: 12px; border: none !important; }}
            table.dataTable tbody td {{ padding: 16px 12px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
            
            .addr-cell {{ font-family: 'Fira Code', monospace; color: var(--accent); cursor: pointer; }}
            .num {{ font-variant-numeric: tabular-nums; text-align: right !important; }}
            .current {{ background: #f8fafc; }}
            .pos {{ color: var(--pos); font-weight: 600; }}
            .neg {{ color: var(--neg); font-weight: 600; }}
            .neutral {{ color: #94a3b8; }}
            
            .tag {{ font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 6px; }}
            .tag-orig {{ background: #eff6ff; color: #2563eb; }}
            .tag-new {{ background: #ecfdf5; color: #059669; }}
            
            .chart-cell {{ width: 120px; }}
            .sparkline {{ display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 ZZZZZZZ Holder Monitor</h1>
                <div class="status">Last updated: {date_str} | Network: Runes Protocol</div>
            </header>
            <table id="holderTable" class="display">
                <thead>
                    <tr>
                        <th>Address</th>
                        <th>Type</th>
                        <th>Initial</th>
                        <th>Yesterday</th>
                        <th>Current</th>
                        <th>24H Change</th>
                        <th>Trend (Daily)</th>
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
                // 初始化表格：禁用分页，一页显示所有数据
                $('#holderTable').DataTable({{
                    paging: false,
                    scrollY: '70vh',
                    scrollCollapse: true,
                    info: true,
                    order: [[4, 'desc']],
                    language: {{ search: "_INPUT_", searchPlaceholder: "Search address..." }}
                }});

                // 初始化小趋势图
                $('.sparkline').sparkline('html', {{
                    type: 'line',
                    width: '100px',
                    height: '30px',
                    lineColor: '#3b82f6',
                    fillColor: '#dbeafe',
                    spotColor: false,
                    minSpotColor: false,
                    maxSpotColor: false,
                    lineWidth: 2
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    file_path = os.path.abspath("index.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    webbrowser.open(f"file://{file_path}")

if __name__ == "__main__":
    main()