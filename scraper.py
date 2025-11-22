import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

# PTT MacShop 版網址
BASE_URL = "https://www.ptt.cc/bbs/MacShop/index.html"
DOMAIN = "https://www.ptt.cc"

# 模擬瀏覽器 Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": "over18=1" 
}

def get_posts(pages=10):
    """ 抓取最近 x 頁的資料 """
    posts = []
    url = BASE_URL

    print(f"Start scraping from: {url}")

    for i in range(pages):
        print(f"Processing page {i+1}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"Failed to fetch {url}, status: {resp.status_code}")
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            divs = soup.find_all("div", class_="r-ent")
            
            for div in divs:
                try:
                    # 抓取標題區塊
                    title_div = div.find("div", class_="title")
                    if not title_div or not title_div.a:
                        continue
                    
                    raw_title = title_div.a.text.strip()
                    link = DOMAIN + title_div.a["href"]
                    date = div.find("div", class_="date").text.strip()
                    
                    # 邏輯：只抓 [販售] 且排除 Re: (回文) 與公告
                    if "[販售]" in raw_title and "Re:" not in raw_title and "公告" not in raw_title:
                        
                        category = classify(raw_title)
                        
                        # 只保留有對應到關鍵字的商品 (若不想顯示 Other 可在此過濾)
                        if category != "Other":
                            posts.append({
                                "title": raw_title,
                                "link": link,
                                "date": date,
                                "category": category,
                                "location": extract_location(raw_title),
                                "price": extract_price(raw_title)
                            })
                except Exception as e:
                    print(f"Error parsing post: {e}")

            # 找出「上一頁」的連結，準備進入下一輪迴圈
            btn = soup.find("a", string="‹ 上頁")
            if btn:
                url = DOMAIN + btn["href"]
            else:
                print("No more pages.")
                break
                
            time.sleep(1) # 禮貌性暫停，避免被 PTT 封鎖
            
        except Exception as e:
            print(f"Error requesting {url}: {e}")
            break
            
    return posts

def classify(title):
    """ 依照你的需求，使用單純的關鍵字比對 (不分大小寫) """
    t = title.lower()
    
    if "iphone" in t: return "iPhone"
    if "ipad" in t: return "iPad"
    if "watch" in t: return "Apple Watch"
    if "homepod" in t: return "HomePod"
    if "airtag" in t: return "AirTag"
    if "macbook" in t: return "MacBook"
    if "airpods" in t: return "AirPods"
    
    return "Other"

def extract_location(title):
    """ 從標題抓取常見地點 """
    # 常見縣市簡寫與全名
    locations = ["台北", "新北", "桃園", "新竹", "苗栗", "台中", "彰化", "雲林", "嘉義", "台南", "高雄", "屏東", "宜蘭", "花蓮", "台東", "基隆", "南投"]
    for loc in locations:
        if loc in title:
            return loc
    return "" # 沒寫就留空

def extract_price(title):
    """ 嘗試從標題抓取價格 (僅供參考，抓取 $ 或 純數字) """
    # 尋找 $15000 或 15000 格式，排除 iPhone 15 這種型號數字
    # 這裡簡單抓取 4-6 位數的數字 (如 5000 ~ 150000)
    match = re.search(r'\$?\s?(\d{1,3}(?:,\d{3})*)', title)
    
    # 進階過濾：如果抓到的數字太小 (例如 14, 15) 可能是型號而非價格
    if match:
        num_str = match.group(1).replace(',', '')
        if num_str.isdigit() and int(num_str) > 500: # 假設價格大於 500 才是錢
            return f"${num_str}"
            
    return "詳內文"

if __name__ == "__main__":
    # 執行爬蟲，抓取最近 10 頁 (可自行調整)
    data = get_posts(pages=10)
    
    # 加上更新時間
    output = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "data": data
    }
    
    # 寫
