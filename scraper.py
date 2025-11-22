import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

# PTT MacShop 版網址
BASE_URL = "https://www.ptt.cc/bbs/MacShop/index.html"
DOMAIN = "https://www.ptt.cc"

def get_posts(pages=10):
    """ 抓取最近 x 頁的資料 """
    posts = []
    url = BASE_URL
    
    # 建立一個能繞過 Cloudflare 的 scraper
    scraper = cloudscraper.create_scraper()

    print(f"Start scraping from: {url}")

    for i in range(pages):
        print(f"Processing page {i+1}...")
        try:
            # 改用 scraper.get
            resp = scraper.get(url)
            
            # Debug: 印出狀態碼
            if resp.status_code != 200:
                print(f"Failed to fetch {url}, status: {resp.status_code}")
                # 如果被擋，通常會是 403 或 503
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Debug: 印出網頁標題，確認是否真的進到 PTT
            page_title = soup.title.text if soup.title else "No Title"
            print(f"Page Title: {page_title}")
            
            # 如果標題包含 "Just a moment" 或 "Access denied"，代表還是被擋
            if "Just a moment" in page_title or "Access denied" in page_title:
                print("Blocked by Cloudflare challenge.")
                break

            divs = soup.find_all("div", class_="r-ent")
            
            # Debug: 確認這頁有抓到幾篇文章
            print(f"Found {len(divs)} articles on this page.")

            if len(divs) == 0:
                # 有可能是結構變了，或是抓到了錯誤的頁面
                print("Warning: No articles found. The HTML structure might be different or blocked.")
            
            for div in divs:
                try:
                    title_div = div.find("div", class_="title")
                    if not title_div or not title_div.a:
                        continue
                    
                    raw_title = title_div.a.text.strip()
                    link = DOMAIN + title_div.a["href"]
                    date = div.find("div", class_="date").text.strip()
                    
                    # 邏輯：只抓 [販售] 且排除 Re: (回文) 與公告
                    if "[販售]" in raw_title and "Re:" not in raw_title and "公告" not in raw_title:
                        
                        category = classify(raw_title)
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

            # 找出「上一頁」
            btn = soup.find("a", string="‹ 上頁")
            if btn:
                url = DOMAIN + btn["href"]
            else:
                print("No more pages.")
                break
                
            # 隨機暫停 2~5 秒，模擬人類行為，避免太規律被抓
            time.sleep(3)
            
        except Exception as e:
            print(f"Error requesting {url}: {e}")
            break
            
    return posts

def classify(title):
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
    locations = ["台北", "新北", "桃園", "新竹", "苗栗", "台中", "彰化", "雲林", "嘉義", "台南", "高雄", "屏東", "宜蘭", "花蓮", "台東", "基隆", "南投"]
    for loc in locations:
        if loc in title:
            return loc
    return ""

def extract_price(title):
    match = re.search(r'\$?\s?(\d{1,3}(?:,\d{3})*)', title)
    if match:
        num_str = match.group(1).replace(',', '')
        if num_str.isdigit() and int(num_str) > 500:
            return f"${num_str}"
    return "詳內文"

if __name__ == "__main__":
    data = get_posts(pages=10)
    
    output = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "data": data
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"Done! Scraped {len(data)} items. Saved to data.json.")
