import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import random  # <--- 新增 random 模組
from datetime import datetime

# 設定
BASE_URL = "https://www.ptt.cc/bbs/MacShop/index.html"
DOMAIN = "https://www.ptt.cc"
PAGES_TO_SCRAPE = 10  # <--- 改為爬 10 頁

def get_posts(pages=10):
    """ 抓取最近 x 頁的資料 """
    posts = []
    url = BASE_URL
    
    # 建立 scraper
    scraper = cloudscraper.create_scraper()

    print(f"Start scraping from: {url} (Target: {pages} pages)")

    for i in range(pages):
        print(f"Processing list page {i+1}...")
        try:
            resp = scraper.get(url)
            if resp.status_code != 200:
                print(f"Failed to fetch list {url}")
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            divs = soup.find_all("div", class_="r-ent")
            
            items_to_process = []

            for div in divs:
                try:
                    title_div = div.find("div", class_="title")
                    if not title_div or not title_div.a: continue
                    
                    raw_title = title_div.a.text.strip()
                    link = DOMAIN + title_div.a["href"]
                    date = div.find("div", class_="date").text.strip()
                    
                    # 過濾：只抓 [販售]
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
                print(f"  Checking price for: {item['title'][:20]}...")
                item['price'] = get_price_from_content(scraper, item['link'])
                posts.append(item)
                
                # <--- 重要修改：隨機休息 1.5 ~ 3 秒
                # 這樣看起來更像人類，不容易被擋，且 10 頁跑完約需 5~8 分鐘，非常安全
                sleep_time = random.uniform(1.5, 3)
                time.sleep(sleep_time) 

            # 翻下一頁
            btn = soup.find("a", string="‹ 上頁")
            if btn:
                url = DOMAIN + btn["href"]
            else:
                break
            
            # 翻頁時也隨機休息一下
            time.sleep(random.uniform(1, 2)) 
            
        except Exception as e:
            print(f"Error requesting {url}: {e}")
            break
            
    return posts

def get_price_from_content(scraper, link):
    """ 進入文章內文，抓取 [售價] 後面的數字 """
    try:
        resp = scraper.get(link)
        if resp.status_code != 200: return "詳內文"
        
        soup = BeautifulSoup(resp.text, "html.parser")
        main_content = soup.find(id="main-content")
        
        if not main_content: return "詳內文"
        
        text = main_content.text
        
        # 使用寬鬆規則：抓取數字和逗號
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
    
    output = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "data": data
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"Done! Scraped {len(data)} items.")
