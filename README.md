# Booking.com MCP Server 🏨

**Free, real-time Booking.com search for AI agents via MCP (Model Context Protocol).**

A headful browser (Playwright + Chromium) scrapes live Booking.com search results and returns structured JSON. Supports comprehensive filters, multi-date availability search, and intelligent result aggregation.

## 🚀 Features

- **3 Search Modes**: Fixed dates, flexible dates, or date-range multi-search
- **Date-Range Search**: Searches ALL possible check-in dates within a range and aggregates results with price comparison
- **Comprehensive Filters**: Property types, meals, facilities, distance, rating, free cancellation
- **Intelligent Pagination**: Infinite scroll scraping (~50-75 results per search)
- **Persistent Browser**: Browser stays open between searches for fast follow-up queries
- **Automatic Popup Dismissal**: Handles cookie banners and sign-in overlays
- **Rich Metadata**: Distance, rating, price per date, availability across dates
- **Agent-Friendly**: Detailed tool descriptions with caveats and recommendations

## 📦 Installation

```bash
git clone https://github.com/MaxXLive/booking.com-mcp.git
cd booking.com-mcp
python3 -m venv venv
source venv/bin/activate
pip install playwright
playwright install chromium
```

## 🤖 MCP Integration

### GitHub Copilot CLI

Add to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "hotels": {
      "command": "/absolute/path/to/booking.com-mcp/venv/bin/python3",
      "args": ["/absolute/path/to/booking.com-mcp/mcp_server.py"],
      "cwd": "/absolute/path/to/booking.com-mcp"
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hotels": {
      "command": "/absolute/path/to/booking.com-mcp/venv/bin/python3",
      "args": ["/absolute/path/to/booking.com-mcp/mcp_server.py"],
      "cwd": "/absolute/path/to/booking.com-mcp"
    }
  }
}
```

## 🛠️ Tools

### `search_hotels`

Main search tool with these parameters:

| Parameter | Description |
|-----------|-------------|
| `location` | City or area (e.g. "Faliraki Rhodes") |
| `adults` | Number of adults (default 1) |
| `rooms` | Number of separate rooms/units to book |
| `checkin` / `checkout` | Fixed dates (YYYY-MM-DD) |
| `nights` + `months` | Flexible date search |
| `nights` + `earliest_date` + `latest_date` | Date-range multi-search |
| `property_types` | hotel, apartment, resort, villa, holiday_home, bnb, guesthouse, entire_home |
| `facilities` | pool, private_pool, parking, spa, wifi, jacuzzi, terrace, beachfront, pets_allowed, adults_only |
| `meals` | breakfast, all_inclusive, half_board, full_board, self_catering |
| `min_rating` | Minimum review score (6, 7, 8, or 9) |
| `max_distance` | Max meters from city center |
| `free_cancellation` | Only free cancellation properties |
| `bedrooms` | Min bedrooms in a single unit (villa/apartment) |
| `sort` | popularity, price, rating_and_price, rating, distance, etc. |

### `click_element`

Click any element on the open page by CSS selector.

### `scrape_current`

Re-scrape results from the currently open page (after manual filter changes).

### `close_browser`

Close the browser session.

## 📋 Search Modes

### Fixed Dates
```
location: "Bangkok", checkin: "2026-07-01", checkout: "2026-07-10"
```

### Flexible Dates
```
location: "Rhodes", nights: 7, months: ["7-2026", "8-2026"]
```

### Date-Range Multi-Search (recommended)
```
location: "Faliraki Rhodes", nights: 10, earliest_date: "2026-06-01", latest_date: "2026-06-16"
```
This searches all 6 possible check-in dates (June 1-6), aggregates results, tracks best prices, and shows availability across dates.

## ⚠️ Important Notes for Agents

- **`pool` vs `private_pool`**: Some properties have a private pool only in one room type but aren't tagged with any pool facility. Consider searching without pool filter.
- **`beachfront`**: Strict tag – only properties directly on the beach. Properties 50m away won't appear.
- **`max_distance`**: Measures from city center, not from beach/attractions.
- **`entire_home`**: Superset that includes apartments, villas, holiday homes. Prefer over `apartment` alone.
- **`rooms` vs `bedrooms`**: `rooms=3` books 3 separate units; `bedrooms=3` finds one large unit with 3 bedrooms.
- **`min_rating`**: Hides new properties without enough reviews.

## ⚠️ Disclaimer

This uses web scraping. Booking.com may change their DOM structure. Use responsibly.
