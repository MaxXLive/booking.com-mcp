import sys
import json
import logging
from booking import search_hotels

# Configure logging
logging.basicConfig(filename='mcp_server.log', level=logging.INFO)

def handle_request(req):
    method = req.get("method")
    msg_id = req.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": { "tools": {} },
                "serverInfo": { "name": "hotels-skill", "version": "1.0.0" }
            }
        }
    
    if method == "notifications/initialized":
        return None
        
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [{
                    "name": "search_hotels",
                    "description": "Search for hotels on Booking.com. Returns live pricing and availability.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": { "type": "string", "description": "City or Location (e.g. Bangkok, Paris)" },
                            "checkin": { "type": "string", "description": "Check-in Date (YYYY-MM-DD)" },
                            "checkout": { "type": "string", "description": "Check-out Date (YYYY-MM-DD)" },
                            "adults": { "type": "integer", "description": "Number of adults (default 1)" }
                        },
                        "required": ["location", "checkin", "checkout"]
                    }
                }]
            }
        }
        
    if method == "tools/call":
        params = req.get("params", {})
        if params.get("name") == "search_hotels":
            args = params.get("arguments", {})
            try:
                # Default adults to 1 if not provided
                adults = args.get("adults", 1)
                data = search_hotels(args["location"], args["checkin"], args["checkout"], adults)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{ "type": "text", "text": json.dumps(data, indent=2) }]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": { "code": -32000, "message": str(e) }
                }
        else:
             return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": { "code": -32601, "message": "Method not found" }
            }

    if msg_id is not None:
         return {
            "jsonrpc": "2.0",
            "id": msg_id,
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
