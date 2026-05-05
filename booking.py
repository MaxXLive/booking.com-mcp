import sys
import json
import time
import re
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
import urllib.parse

# Persistent browser session
_playwright = None
_browser = None
_page = None

# Filter value mappings for human-readable names
PROPERTY_TYPES = {
    "hotel": "ht_id=204", "apartment": "ht_id=201", "resort": "ht_id=206",
    "villa": "ht_id=213", "holiday_home": "ht_id=220", "bnb": "ht_id=208",
    "guesthouse": "ht_id=216", "entire_home": "privacy_type=3",
}
MEALS = {
    "breakfast": "mealplan=1", "all_inclusive": "mealplan=4",
    "half_board": "mealplan=9", "full_board": "mealplan=3",
    "self_catering": "mealplan=999",
}
FACILITIES = {
    "pool": "hotelfacility=433", "private_pool": "roomfacility=93",
    "parking": "hotelfacility=2", "spa": "hotelfacility=54",
    "wifi": "hotelfacility=107", "jacuzzi": "hotelfacility=63",
    "terrace": "roomfacility=123", "beachfront": "ht_beach=1",
    "pets_allowed": "stay_type=1", "adults_only": "stay_type=2",
}
SORT_OPTIONS = {
    "popularity": "popularity", "price": "price", "price_desc": "price_from_high_to_low",
    "rating_and_price": "review_score_and_price", "rating": "bayesian_review_score",
    "stars_desc": "class", "stars_asc": "class_asc", "distance": "distance_from_search",
    "vacation_homes_first": "upsort_bh",
}


_context = None

def _ensure_browser():
    global _playwright, _browser, _page, _context
    if _browser and _browser.is_connected():
        return _page
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=False,
        args=["--window-size=960,1080", "--window-position=0,0"],
    )
    _context = _browser.new_context(viewport={"width": 960, "height": 960}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    _page = _context.new_page()
    return _page

def _dismiss_popups(page):
    # Cookie first, then sign-in, then cookie again (order matters)
    popups = [
        '#onetrust-accept-btn-handler',
        'button[aria-label="Informationen zur Anmeldung ausblenden."]',
        'button[aria-label="Dismiss sign-in info."]',
        '#onetrust-accept-btn-handler',
    ]
    for selector in popups:
        try:
            page.click(selector, timeout=2000)
            time.sleep(0.5)
        except:
            pass

def _scrape_results(page, checkin=None, checkout=None):
    results = []
    cards = page.query_selector_all('[data-testid="property-card"]')
    for card in cards:
        try:
            title_el = card.query_selector('[data-testid="title"]')
            price_el = card.query_selector('[data-testid="price-and-discounted-price"]')
            rating_el = card.query_selector('[data-testid="review-score"]')
            link_el = card.query_selector('a[data-testid="title-link"]')
            distance_el = card.query_selector('[data-testid="distance"]')
            location_el = card.query_selector('[data-testid="address"]')
            title = title_el.inner_text() if title_el else "Unknown"
            price = price_el.inner_text() if price_el else "No price"
            rating = rating_el.inner_text().split('\n')[0] if rating_el else ""
            link = link_el.get_attribute('href') if link_el else ""
            distance = distance_el.inner_text() if distance_el else ""
            location = location_el.inner_text() if location_el else ""
            entry = {
                "title": title, "price": price, "rating": rating,
                "link": link, "distance": distance, "location": location,
            }
            if checkin and checkout:
                entry["checkin"] = checkin
                entry["checkout"] = checkout
            results.append(entry)
        except:
            continue
    return results

def _build_nflt(property_types=None, min_rating=None, meals=None,
                facilities=None, free_cancellation=False, bedrooms=None,
                max_distance=None):
    """Build the nflt filter string from human-readable params."""
    parts = ["oos=1"]  # Always hide unavailable properties
    if property_types:
        for pt in property_types:
            if pt in PROPERTY_TYPES:
                parts.append(PROPERTY_TYPES[pt])
    if min_rating:
        parts.append(f"review_score={min_rating * 10}")
    if meals:
        for m in meals:
            if m in MEALS:
                parts.append(MEALS[m])
    if facilities:
        for f in facilities:
            if f in FACILITIES:
                parts.append(FACILITIES[f])
    if free_cancellation:
        parts.append("fc=2")
    if bedrooms:
        parts.append(f"entire_place_bedroom_count={bedrooms}")
    if max_distance:
        parts.append(f"distance={max_distance}")
    return ";".join(parts) if parts else None


def _parse_price(price_str):
    """Extract numeric price from string like '€ 1.920' or '€ 2.082'."""
    nums = re.findall(r'[\d.]+', price_str.replace('.', '').replace(',', '.'))
    try:
        return float(nums[0]) if nums else 999999
    except:
        return 999999


def _single_search(page, location, adults, checkin, checkout, nflt, sort, rooms=1):
    """Run a single fixed-date search and return results (with scroll for more)."""
    params = {
        "ss": location,
        "group_adults": str(adults),
        "no_rooms": str(rooms),
        "group_children": "0",
        "checkin": checkin,
        "checkout": checkout,
    }
    if nflt:
        params["nflt"] = nflt
    if sort:
        params["order"] = sort

    url = "https://www.booking.com/searchresults.html?" + urllib.parse.urlencode(params)
    page.goto(url, wait_until="domcontentloaded")
    _dismiss_popups(page)
    try:
        page.wait_for_selector('[data-testid="property-card"]', timeout=12000)
    except:
        return []

    # Only scroll if there are 25 cards (full page = likely more results)
    cards = page.query_selector_all('[data-testid="property-card"]')
    if len(cards) >= 25:
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)

    return _scrape_results(page, checkin=checkin, checkout=checkout)


def search(location, adults=1, rooms=1, checkin=None, checkout=None,
           nights=None, months=None,
           earliest_date=None, latest_date=None,
           property_types=None, min_rating=None, meals=None,
           facilities=None, free_cancellation=False, bedrooms=None,
           sort=None, max_distance=None):
    """Unified search: fixed dates, flexible (ltfd), or date-range multi-search."""
    page = _ensure_browser()
    rooms = rooms or 1

    nflt = _build_nflt(property_types, min_rating, meals, facilities, free_cancellation, bedrooms, max_distance)
    sort_val = SORT_OPTIONS.get(sort) if sort else None

    # MODE 1: Date range multi-search (best results)
    if nights and earliest_date and latest_date:
        return _multi_date_search(page, location, adults, nights,
                                  earliest_date, latest_date, nflt, sort_val, rooms)

    # MODE 2: Fixed dates
    if checkin and checkout:
        params = {
            "ss": location,
            "group_adults": str(adults),
            "no_rooms": str(rooms),
            "group_children": "0",
            "checkin": checkin,
            "checkout": checkout,
        }
        if nflt:
            params["nflt"] = nflt
        if sort_val:
            params["order"] = sort_val

        url = "https://www.booking.com/searchresults.html?" + urllib.parse.urlencode(params)
        page.goto(url, wait_until="domcontentloaded")
        _dismiss_popups(page)
        try:
            page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
        except:
            return {"error": "Timeout or no results found"}
        cards = page.query_selector_all('[data-testid="property-card"]')
        if len(cards) >= 25:
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
        return {"hotels": _scrape_results(page, checkin=checkin, checkout=checkout)}

    # MODE 3: Flexible (ltfd) - legacy fallback
    if nights and months:
        params = {
            "ss": location,
            "group_adults": str(adults),
            "no_rooms": str(rooms),
            "group_children": "0",
            "ltfd": f"1:{nights}:{'_'.join(months)}:1:1",
        }
        if nflt:
            params["nflt"] = nflt
        if sort_val:
            params["order"] = sort_val

        url = "https://www.booking.com/searchresults.html?" + urllib.parse.urlencode(params)
        page.goto(url, wait_until="domcontentloaded")
        _dismiss_popups(page)
        try:
            page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
        except:
            return {"error": "Timeout or no results found"}
        cards = page.query_selector_all('[data-testid="property-card"]')
        if len(cards) >= 25:
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
        return {"hotels": _scrape_results(page)}

    return {"error": "Provide checkin+checkout, nights+earliest_date+latest_date, or nights+months"}


def _multi_date_search(page, location, adults, nights, earliest_date, latest_date, nflt, sort_val, rooms=1):
    """Search all valid check-in dates within range and aggregate results."""
    start = date.fromisoformat(earliest_date)
    end = date.fromisoformat(latest_date)
    last_checkin = end - timedelta(days=nights)

    # Generate all valid check-in dates
    checkin_dates = []
    current = start
    while current <= last_checkin:
        checkin_dates.append(current)
        current += timedelta(days=1)

    if not checkin_dates:
        return {"error": f"No valid check-in dates: {nights} nights don't fit between {earliest_date} and {latest_date}"}

    # Search each date combination
    all_results = {}  # keyed by hotel title
    searched_dates = []

    for ci in checkin_dates:
        co = ci + timedelta(days=nights)
        ci_str = ci.isoformat()
        co_str = co.isoformat()
        searched_dates.append(f"{ci_str} → {co_str}")

        results = _single_search(page, location, adults, ci_str, co_str, nflt, sort_val, rooms)

        for hotel in results:
            title = hotel["title"]
            price_num = _parse_price(hotel["price"])

            if title not in all_results:
                all_results[title] = {
                    "title": title,
                    "rating": hotel["rating"],
                    "distance": hotel["distance"],
                    "location": hotel["location"],
                    "link": hotel["link"],
                    "best_price": price_num,
                    "best_price_str": hotel["price"],
                    "best_dates": f"{ci_str} → {co_str}",
                    "available_dates": [f"{ci_str} → {co_str}"],
                    "all_prices": {f"{ci_str}": hotel["price"]},
                }
            else:
                existing = all_results[title]
                existing["available_dates"].append(f"{ci_str} → {co_str}")
                existing["all_prices"][ci_str] = hotel["price"]
                if price_num < existing["best_price"]:
                    existing["best_price"] = price_num
                    existing["best_price_str"] = hotel["price"]
                    existing["best_dates"] = f"{ci_str} → {co_str}"

    # Sort by best price
    sorted_results = sorted(all_results.values(), key=lambda x: x["best_price"])

    # Clean up output
    for r in sorted_results:
        del r["best_price"]  # remove numeric helper
        r["date_flexibility"] = f"{len(r['available_dates'])} of {len(checkin_dates)} possible dates available"

    return {
        "search_summary": {
            "location": location,
            "nights": nights,
            "date_range": f"{earliest_date} to {latest_date}",
            "possible_checkin_dates": len(checkin_dates),
            "searched_periods": searched_dates,
            "total_unique_hotels_found": len(sorted_results),
        },
        "hotels": sorted_results,
    }


def click_element(selector):
    global _page
    if not _page:
        return {"error": "No browser session. Run search first."}
    try:
        _page.click(selector, timeout=5000)
        time.sleep(2)
        return {"status": "clicked", "selector": selector}
    except Exception as e:
        return {"error": f"Click failed: {str(e)}"}

def scrape_current():
    global _page
    if not _page:
        return {"error": "No browser session. Run search first."}
    try:
        _page.wait_for_selector('[data-testid="property-card"]', timeout=10000)
    except:
        return {"error": "No hotel cards found on current page"}
    return {"hotels": _scrape_results(_page)}

def close_browser():
    global _playwright, _browser, _page, _context
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = None
    _context = None
    _page = None
    _playwright = None
    return {"status": "browser closed"}


def show_on_map():
    """Open current search results in map view in a new tab."""
    global _page, _context
    if not _page:
        return {"error": "No browser session. Run search first."}
    try:
        current_url = _page.url
        if 'map=1' not in current_url:
            separator = '&' if '?' in current_url else '?'
            map_url = current_url + separator + 'map=1'
        else:
            map_url = current_url
        map_page = _context.new_page()
        map_page.goto(map_url, wait_until="domcontentloaded")
        _dismiss_popups(map_page)
        time.sleep(3)
        return {"status": "Map view opened in new tab. User can browse hotels on the map."}
    except Exception as e:
        return {"error": f"Could not open map: {str(e)}"}


def view_hotel(url):
    """Open hotel detail page in a new tab and scrape key information."""
    global _browser
    _ensure_browser()
    hotel_page = _context.new_page()
    hotel_page.goto(url, wait_until="domcontentloaded")
    _dismiss_popups(hotel_page)
    time.sleep(3)

    info = {"url": url}

    # Hotel name
    try:
        name_el = hotel_page.query_selector('h2.pp-header__title') or hotel_page.query_selector('[data-testid="title"]')
        if name_el:
            info["name"] = name_el.inner_text().strip()
    except:
        pass

    # Rating
    try:
        rating_el = hotel_page.query_selector('[data-testid="review-score-component"]')
        if rating_el:
            info["rating"] = rating_el.inner_text().strip().replace('\n', ' ')
    except:
        pass

    # Address
    try:
        addr_el = hotel_page.query_selector('[data-node_tt_id="location_score_tooltip"]') or hotel_page.query_selector('.hp_address_subtitle')
        if addr_el:
            info["address"] = addr_el.inner_text().strip()
    except:
        pass

    # Description
    try:
        desc_el = hotel_page.query_selector('[data-testid="property-description"]') or hotel_page.query_selector('#property_description_content')
        if desc_el:
            info["description"] = desc_el.inner_text().strip()[:500]
    except:
        pass

    # Facilities
    try:
        facility_els = hotel_page.query_selector_all('[data-testid="property-most-popular-facilities-wrapper"] span')
        if facility_els:
            facilities = list(dict.fromkeys(f.inner_text().strip() for f in facility_els if f.inner_text().strip()))
            info["top_facilities"] = facilities
    except:
        pass

    # Room types and prices (scroll to table)
    try:
        hotel_page.evaluate("document.querySelector('#hprt-table')?.scrollIntoView()")
        time.sleep(1)
        room_rows = hotel_page.query_selector_all('tr.js-rt-block-row, [data-testid="availability-row"]')
        rooms = []
        seen = set()
        for row in room_rows[:10]:
            try:
                room_name_el = row.query_selector('.hprt-roomtype-icon-link, [data-testid="room-type-link"]')
                price_el = row.query_selector('.bui-price-display__value, [data-testid="price-and-discounted-price"]')
                room_name = room_name_el.inner_text().strip() if room_name_el else None
                price = price_el.inner_text().strip() if price_el else None
                if room_name and room_name not in seen:
                    seen.add(room_name)
                    room_info = {"room_type": room_name}
                    if price:
                        room_info["price"] = price
                    occupancy_el = row.query_selector('.hprt-occupancy-occupancy-info, [data-testid="occupancy"]')
                    if occupancy_el:
                        room_info["occupancy"] = occupancy_el.inner_text().strip()
                    rooms.append(room_info)
            except:
                continue
        if rooms:
            info["rooms"] = rooms
    except:
        pass

    info["note"] = "Browser is open on the hotel page. User can browse photos, rooms, and map manually."
    return info

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(json.dumps({"error": "Usage: booking.py LOCATION CHECKIN CHECKOUT ADULTS"}))
        sys.exit(1)
    data = search(sys.argv[1], int(sys.argv[4]), checkin=sys.argv[2], checkout=sys.argv[3])
    print(json.dumps(data, indent=2))
