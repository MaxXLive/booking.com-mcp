import sys
import json
import logging
from booking import search, click_element, scrape_current, close_browser, view_hotel, show_on_map

logging.basicConfig(filename='mcp_server.log', level=logging.INFO)

TOOLS = [
    {
        "name": "search_hotels",
        "description": "Search for hotels on Booking.com. Returns live pricing and availability. Browser stays open for further interaction. Use EITHER fixed dates (checkin+checkout) OR flexible dates (nights+months) OR date-range search (nights+earliest_date+latest_date). Date-range mode searches ALL possible check-in dates and aggregates results with price comparison across dates.\n\nIMPORTANT NOTES FOR AGENT:\n- Unavailable properties are always hidden by default (oos=1 filter).\n- 'beachfront' is a strict tag: only properties DIRECTLY on the beach. Many properties 50-100m away won't appear. If user says 'near the beach', consider omitting beachfront filter and using max_distance instead.\n- 'max_distance' measures from CITY CENTER, not from the beach! A property can be 2km from center but right on the beach. In beach towns, don't rely on distance alone.\n- 'entire_home' is a superset that includes apartments, villas, holiday homes. Prefer this over 'apartment' alone when user wants a vacation rental/Ferienwohnung.\n- 'min_rating' hides new properties without enough reviews. Consider omitting for small/new places.\n- 'sort=price' sorts by cheapest room type which may be a single room unsuitable for groups. For groups, 'popularity' or 'rating_and_price' often gives better results.\n- 'free_cancellation' may hide properties that DO offer free cancellation at a higher price tier but show non-refundable as default.\n- When in doubt about filters, run a broader search first. It's better to show more results than to miss good options. Ask the user to narrow down if too many results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": { "type": "string", "description": "City or Location (e.g. Faliraki Rhodes, Bangkok, Paris)" },
                "adults": { "type": "integer", "description": "Number of adults (default 1)" },
                "rooms": { "type": "integer", "description": "Number of rooms to book (default 1). Use for groups needing multiple rooms/units at same property (e.g. 3 studio apartments). Different from 'bedrooms' which filters for a single large unit." },
                "checkin": { "type": "string", "description": "Fixed check-in date (YYYY-MM-DD). Use with checkout." },
                "checkout": { "type": "string", "description": "Fixed check-out date (YYYY-MM-DD). Use with checkin." },
                "nights": { "type": "integer", "description": "Number of nights for flexible search. Use with months." },
                "months": {
                    "type": "array", "items": { "type": "string" },
                    "description": "Months for flexible search as 'M-YYYY', e.g. ['6-2026', '7-2026']. Up to 3. Use with nights."
                },
                "earliest_date": { "type": "string", "description": "Earliest possible check-in date (YYYY-MM-DD). Use with nights + latest_date for date-range multi-search." },
                "latest_date": { "type": "string", "description": "Latest possible check-out date (YYYY-MM-DD). Use with nights + earliest_date for date-range multi-search." },
                "property_types": {
                    "type": "array", "items": { "type": "string" },
                    "description": "Filter by property type. Options: hotel, apartment, resort, villa, holiday_home, bnb, guesthouse, entire_home. NOTE: 'entire_home' is a superset including apartments, villas, holiday homes. Prefer this when user wants any vacation rental/Ferienwohnung."
                },
                "min_rating": { "type": "integer", "description": "Minimum review score (6, 7, 8, or 9). NOTE: Hides new properties without enough reviews." },
                "meals": {
                    "type": "array", "items": { "type": "string" },
                    "description": "Meal plan filter. Options: breakfast, all_inclusive, half_board, full_board, self_catering"
                },
                "facilities": {
                    "type": "array", "items": { "type": "string" },
                    "description": "Facility filters. Options: pool, private_pool, parking, spa, wifi, jacuzzi, terrace, beachfront, pets_allowed, adults_only. IMPORTANT: 'pool' = shared/hotel pool. 'private_pool' = pool in the room/suite. Some properties only have private pools (not tagged as 'pool'), so they won't appear with just 'pool' filter. Additionally, some properties offer a private pool only in specific room types (e.g. one suite) but are NOT tagged with any pool facility at all. When user wants any kind of pool, consider running a broader search without pool filter and mentioning that some results may not have a pool."
                },
                "free_cancellation": { "type": "boolean", "description": "Only show properties with free cancellation. NOTE: May hide properties that offer free cancellation at a higher price tier but show non-refundable as cheapest." },
                "bedrooms": { "type": "integer", "description": "Minimum number of bedrooms in a SINGLE unit (villa/apartment). Use for finding one large property. Different from 'rooms' which books multiple separate units." },
                "max_distance": { "type": "integer", "description": "Maximum distance from search center in meters (e.g. 1000, 3000, 5000). NOTE: Distance is from CITY CENTER, not from beach/attractions. In beach towns center ≠ beach." },
                "sort": {
                    "type": "string",
                    "description": "Sort order. Options: popularity, price, price_desc, rating_and_price, rating, stars_desc, stars_asc, distance, vacation_homes_first. NOTE: 'price' sorts by cheapest room type which may be a single room unsuitable for groups."
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "click_element",
        "description": "Click an element on the open Booking.com page by CSS selector. Use to apply filters, sort, or navigate. Example selectors: 'button[data-testid=\"sorters-dropdown-trigger\"]', '[data-filters-group=\"price\"] button'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": { "type": "string", "description": "CSS selector of the element to click" }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "scrape_current",
        "description": "Re-scrape hotel results from the currently open Booking.com page. Use after clicking filters or sorting to get updated results.",
        "inputSchema": { "type": "object", "properties": {} }
    },
    {
        "name": "close_browser",
        "description": "Close the Booking.com browser session when done.",
        "inputSchema": { "type": "object", "properties": {} }
    },
    {
        "name": "view_hotel",
        "description": "Open a hotel's detail page in the browser and return key info (description, facilities, room types, prices). Use when the user wants to compare hotels, see photos, or get more details. The browser stays open so the user can browse manually.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": { "type": "string", "description": "The hotel's Booking.com URL (from search results)" }
            },
            "required": ["url"]
        }
    },
    {
        "name": "show_on_map",
        "description": "Switch the current search results to map view so the user can see hotel locations visually. Call after a search to show results on the map.",
        "inputSchema": { "type": "object", "properties": {} }
    }
]

def handle_request(req):
    method = req.get("method")
    msg_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": { "tools": {} },
                "serverInfo": { "name": "hotels-skill", "version": "2.0.0" }
            }
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return { "jsonrpc": "2.0", "id": msg_id, "result": { "tools": TOOLS } }

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})

        try:
            if name == "search_hotels":
                data = search(
                    location=args["location"],
                    adults=args.get("adults", 1),
                    rooms=args.get("rooms", 1),
                    checkin=args.get("checkin"),
                    checkout=args.get("checkout"),
                    nights=args.get("nights"),
                    months=args.get("months"),
                    earliest_date=args.get("earliest_date"),
                    latest_date=args.get("latest_date"),
                    property_types=args.get("property_types"),
                    min_rating=args.get("min_rating"),
                    meals=args.get("meals"),
                    facilities=args.get("facilities"),
                    free_cancellation=args.get("free_cancellation", False),
                    bedrooms=args.get("bedrooms"),
                    sort=args.get("sort"),
                    max_distance=args.get("max_distance"),
                )
            elif name == "click_element":
                data = click_element(args["selector"])
            elif name == "scrape_current":
                data = scrape_current()
            elif name == "close_browser":
                data = close_browser()
            elif name == "view_hotel":
                data = view_hotel(args["url"])
            elif name == "show_on_map":
                data = show_on_map()
            else:
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": { "code": -32601, "message": f"Unknown tool: {name}" }
                }

            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": { "content": [{ "type": "text", "text": json.dumps(data, indent=2) }] }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": { "code": -32000, "message": str(e) }
            }

    if msg_id is not None:
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": { "code": -32601, "message": "Method not found" }
        }
    return None

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            res = handle_request(req)
            if res:
                print(json.dumps(res))
                sys.stdout.flush()
        except Exception as e:
            logging.critical(f"Critical Loop Error: {e}")

if __name__ == "__main__":
    main()
