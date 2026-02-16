import sys
import json
from playwright.sync_api import sync_playwright
import urllib.parse

def search_hotels(location, checkin, checkout, adults):
    with sync_playwright() as p:
        # Launch browser (headless)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # User agent to avoid detection
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        url = f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote(location)}&checkin={checkin}&checkout={checkout}&group_adults={adults}&no_rooms=1&group_children=0"
        
        # print(f"DEBUG: Navigating to {url}", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded")
        
        # Wait for property cards
        try:
            page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
        except:
            return {"error": "Timeout or no results found"}

        # Scrape
        results = []
        cards = page.query_selector_all('[data-testid="property-card"]')
        
        for card in cards[:10]:
            try:
                title_el = card.query_selector('[data-testid="title"]')
                price_el = card.query_selector('[data-testid="price-and-discounted-price"]')
                rating_el = card.query_selector('[data-testid="review-score"]')
                link_el = card.query_selector('a[data-testid="title-link"]')
                
                title = title_el.inner_text() if title_el else "Unknown"
                price = price_el.inner_text() if price_el else "No price"
                rating = rating_el.inner_text().split('\n')[0] if rating_el else ""
                link = link_el.get_attribute('href') if link_el else ""
                
                results.append({
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "link": link
                })
            except:
                continue
                
        browser.close()
        return {"hotels": results}

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(json.dumps({"error": "Usage: booking.py LOCATION CHECKIN CHECKOUT ADULTS"}))
        sys.exit(1)
        
    data = search_hotels(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(json.dumps(data, indent=2))
