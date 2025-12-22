from playwright.sync_api import sync_playwright
import json
import os
import re

def scrape_satsman():
    with sync_playwright() as p:
        print("🚀 启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("🔗 正在打开页面...")
        page.goto("https://www.satsman.fun/launch/ZZZZZZZ", wait_until="networkidle", timeout=60000)
        
        print("\n📢 重要指示：")
        print("1. 请在浏览器中点击 'Load More' 直到按钮彻底消失。")
        print("2. 确认看到第 552 号地址出现后，回到这里。")
        input("⏳ 加载完成后，按【回车】开始最终抓取...")

        # 关键改进：在抓取前强制让页面向下滚动并等待，确保所有 DOM 节点都已挂载
        print("正在强制刷新页面缓存...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000) # 额外多等 3 秒给内存反应时间
        page.evaluate("window.scrollTo(0, 0)")

        print("🔍 正在执行全量深度扫描...")
        
        # 改进提取逻辑：直接扫描所有单元格
        holders_dict = {}
        rows = page.locator("tr").all()

        for row in rows:
            # 拿到整行的文本和源码
            row_text = row.inner_text()
            row_html = row.inner_html()
            
            # 1. 提取地址：寻找 bc1p 开头的完整地址字符串
            # 扩展正则：包含可能出现在 href 里的完整地址
            addr_match = re.search(r'bc1p[a-z0-9]{30,}', row_html + row_text)
            
            if addr_match:
                address = addr_match.group(0)
                
                # 2. 提取 Received Tokens：锁定这一行最后出现的数字单位
                # 匹配如 9.51M, 500K, 1234 等
                tokens = re.findall(r'(\d+(?:\.\d+)?[MK]?)', row_text)
                if tokens:
                    raw_amt = tokens[-1] # 取最后一个数字
                    amount = 0
                    try:
                        if 'M' in raw_amt:
                            amount = float(raw_amt.replace('M', '')) * 1_000_000
                        elif 'K' in raw_amt:
                            amount = float(raw_amt.replace('K', '')) * 1_000
                        else:
                            amount = float(raw_amt.replace(',', ''))
                        
                        if amount > 0:
                            holders_dict[address] = amount
                    except:
                        continue

        final_list = [{"address": k, "amount": v} for k, v in holders_dict.items()]

        print(f"\n--- 最终抓取报告 ---")
        print(f"📊 实际提取到唯一地址: {len(final_list)} 个")
        
        if len(final_list) > 0:
            if not os.path.exists("data"): os.makedirs("data")
            with open("data/initial.json", "w", encoding="utf-8") as f:
                json.dump(final_list, f, indent=4)
            print(f"✅ 数据已更新至 data/initial.json (当前数量: {len(final_list)})")
        else:
            print("❌ 未抓取到数据。")
            
        browser.close()

if __name__ == "__main__":
    scrape_satsman()