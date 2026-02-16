# Free Booking.com API (MCP Server) 🏨

**The only free, real-time Booking.com scraper for AI Agents, Claude, and Python.**

> ⭐️ **Star this repo** if you want to skip the API fees.

This tool uses a headless browser (Playwright) to scrape **Booking.com** search results in real-time, bypassing the need for expensive commercial APIs. It outputs clean JSON for LLMs.

## 🚀 Features
- **Real-time Pricing**: Scrapes live data from Booking.com.
- **No API Keys**: Runs locally using headless Chrome.
- **AI-Native**: Returns structured JSON optimized for Agents.
- **MCP Compatible**: Works natively with Claude Desktop.

## 📦 Installation

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/Anmoldureha/hotels-skill.git
    cd hotels-skill
    ```

2.  **Set up Python environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install playwright
    playwright install chromium
    ```

## 🛠️ Usage

Run the script directly:

```bash
# python booking.py LOCATION CHECKIN CHECKOUT ADULTS
python booking.py "Bangkok" 2026-03-15 2026-03-22 2
```

**Output:**
```json
{
  "hotels": [
    {
      "title": "Hilton Sukhumvit Bangkok",
      "price": "₹ 110,363",
      "rating": "8.5",
      "link": "https://www.booking.com/..."
    }
  ]
}
```

## 🤖 Agent Integration (MCP)

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hotels": {
      "command": "/absolute/path/to/hotels-skill/venv/bin/python3",
      "args": ["/absolute/path/to/hotels-skill/mcp_server.py"]
    }
  }
}
```

## ⚠️ Note
This uses web scraping. Booking.com may change their DOM structure or block IPs if abused. Use responsibly (add delays between requests).
