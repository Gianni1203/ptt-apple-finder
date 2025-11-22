import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

# PTT MacShop 版網址
BASE_URL = "https://www.ptt.cc/bbs/MacShop/index.html"
DOMAIN = "https://www.ptt.cc"

def get_posts(pages=5):
    """ 抓取最近 x 頁的資料 """
    posts = []
    url = BASE_URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": "over18=1" # 雖然 MacShop 不用，但加上以防萬一
    }

    for _ in range(pages):
        print(f"Scraping: {url}")
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 抓取文章列表
            divs = soup.find_all("div", class_="r-ent")
            for div in divs:
                try:
                    title_div = div.find("div", class_="title")
                    if not title_div or not title_div.a:
                        continue
                    
                    title = title_div.a.text.strip()
                    link = DOMAIN + title_div.a["href"]
                    date = div.find("div", class_="date").text.strip()
                    
                    # 過濾：只抓 [販售] 且排除 [徵求]
                    if "[販售]" in title and "[徵求]" not in title and "公告" not in title:
                        posts.append({
                            "title": title,
                            "link": link,
                            "date": date,
                            "category": classify(title),
                            "price": extract_price(title) # 簡易價格抓取
                        })
                except Exception as e:
                    print(f"Error parsing div: {e}")

            # 找出「上一頁」的連結
            btn = soup.find("a", string="‹ 上頁")
            if btn:
                url = DOMAIN + btn["href"]
            else:
                break
                
            time.sleep(1) # 禮貌性暫停
        except Exception as e:
            print(f"Error requesting {url}: {e}")
            break
            
    return posts

def classify(title):
    t = title.lower()
    if "iphone" in t or "i1" in t: return "iPhone"
    if "ipad" in t: return "iPad"
    if "macbook" in t or "mac" in t or "air" in t or "pro" in t: return "MacBook"
    if "watch" in t or "s8" in t or "s9" in t or "ultra" in t: return "Watch"
    if "airpods" in t or "pro 2" in t: return "AirPods"
    if "homepod" in t or "mini" in t: return "HomePod"
    if "tv" in t: return "Apple TV"
    return "Other"

def extract_price(title):
    # 嘗試從標題抓取數字 (例如: $15000, 15000)
    # 這只是簡易版，實際上價格通常在內文，這裡僅供參考
    match = re.search(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?', title)
    if match:
        return match.group(0)
    return "詳內文"

if __name__ == "__main__":
    data = get_posts(pages=10) # 每次更新抓最近 10 頁
    
    # 加上更新時間
    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Done! data.json saved.")
