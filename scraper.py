import cloudscraper
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import json
import time
import re
import random
from datetime import datetime

# 設定
BASE_URL = "https://www.ptt.cc/bbs/MacShop/index.html"
DOMAIN = "https://www.ptt.cc"
PAGES_TO_SCRAPE = 10 

# 隨機 User-Agent 清單
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def create_robust_session():
    """ 建立一個抗斷線的 Session """
    # 建立 cloudscraper 物件
    session = cloudscraper.create_scraper()
    
    # 設定重試策略：
    # total=5: 最多重試 5 次
    # backoff_factor=1: 每次失敗後等待時間會加倍 (1s, 2s, 4s...)
    # status_forcelist: 遇到 500, 502, 503, 504 錯誤時也要重試
    retries = Retry(
        total=5,
        backoff_factor=2, 
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_posts(pages=10):
    posts = []
    url = BASE_URL
    
    # 取得強化版 Session
    session = create_robust_session()

    print(f"Start scraping from: {url} (Target: {pages} pages)")

    for i in range(pages):
        print(f"Processing list page {i+1}...")
        
        try:
            # 隨機切換 User-Agent
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            # 隨機延遲 (很重要！)
            time.sleep(random.uniform(3, 6))
            
            # 發送請求 (這裡如果有 Connection Reset，adapter 會自動重試)
            resp = session.get(url, headers=headers, timeout=30)
            
            if resp.status_code != 200:
                print(f"  Failed with status {resp.status_code}. Skipping this page.")
                break # 如果真的抓不到，就停止
            
            # --- 解析 HTML ---
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 檢查 Cloudflare 驗證頁面
            if "Just a moment" in soup.title.text if soup.title else "":
                print("Blocked by Cloudflare challenge.")
                break

            divs = soup.find_all("div", class_="r-ent")
            items_to_process = []

            for div in divs:
                try:
                    title_div = div.find("div", class_="title")
                    if not title_div or not title_div.a: continue
                    
                    raw_title = title_div.a.text.strip()
                    link = DOMAIN + title_div.a["href"]
                    date = div.find("div", class_="date").text.strip()
                    
                    if "[販售]" in raw_title and "Re:" not in raw_title and "公告" not in raw_title:
                        category = classify(raw_title)
                        if category != "Other":
                            items_to_process.append({
                                "title": raw_title,
                                "link": link,
                                "date": date,
                                "category": category,
                                "location": extract_location(raw_title)
                            })
                except Exception as e:
                    print(f"Error parsing list item: {e}")

            # 進入內文抓價格
            for item in items_to_process:
                print(f"  Checking price for: {item['title'][:15]}...")
                item['price'] = get_price_from_content(session, item['link']) # 傳入 session
                posts.append(item)
                time.sleep(random.uniform(1.5, 3)) 

            # 翻下一頁
            btn = soup.find("a", string="‹ 上頁")
            if btn:
                url = DOMAIN + btn["href"]
            else:
                print("No previous page button found.")
                break
                
        except Exception as e:
            # 這裡抓到的是 retry 5 次後還是失敗的錯誤
            print(f"Critical Error requesting {url}: {e}")
            break
            
    return posts

def get_price_from_content(session, link):
    """ 進入文章內文，抓取價格 """
    try:
        # 這裡也要用 session 發請求，才能享有重試機制
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = session.get(link, headers=headers, timeout=15)
        
        if resp.status_code != 200: return "詳內文"
        
        soup = BeautifulSoup(resp.text, "html.parser")
        main_content = soup.find(id="main-content")
        
        if not main_content: return "詳內文"
        
        text = main_content.text
        match = re.search(r'\[(?:售價|欲售價格)\](?:[:：])?\s*(\$?\s?[0-9,]+)', text)
        
        if match:
            price_str = match.group(1)
            num_only = re.sub(r'[^\d]', '', price_str)
            if num_only.isdigit() and int(num_only) > 100:
                return f"${num_only}" 
                
    except Exception as e:
        print(f"    Error fetching content: {e}")
        
    return "詳內文"

def classify(title):
    t = title.lower()
    if any(x in t for x in ["iphone", "i12", "i13", "i14", "i15", "i16", "se2", "se3"]): return "iPhone"
    if "ipad" in t: return "iPad"
    if any(x in t for x in ["macbook", "mac book", "mbp", "mba", "mac mini", "mac studio"]): return "MacBook"
    if any(x in t for x in ["watch", "s8", "s9", "s10", "ultra"]): return "Apple Watch"
    if "airpods" in t or "air pods" in t: return "AirPods"
    if "homepod" in t: return "HomePod"
    if "airtag" in t: return "AirTag"
    if "apple tv" in t or "appletv" in t: return "Apple TV"
    return "Other"

def extract_location(title):
    locations = ["台北", "新北", "桃園", "新竹", "苗栗", "台中", "彰化", "雲林", "嘉義", "台南", "高雄", "屏東", "宜蘭", "花蓮", "台東", "基隆", "南投"]
    for loc in locations:
        if loc in title:
            return loc
    return ""

if __name__ == "__main__":
    data = get_posts(pages=PAGES_TO_SCRAPE)
    
    # 只有當真的有抓到資料時，才更新 data.json
    # 避免因為被擋而把空資料覆蓋掉原本的舊資料
    if len(data) > 0:
        output = {
            "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
            "data": data
        }
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Done! Scraped {len(data)} items.")
    else:
        print("Warning: Scraped 0 items. Keeping old data.json to prevent empty site.")
