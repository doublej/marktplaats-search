#!/usr/bin/env python3
"""
Gradio UI client for MarktplaatsSearch API.

This client provides a user-friendly interface for:
1. Creating new searches
2. Monitoring search results
3. Receiving real-time notifications
4. Managing existing searches

Requirements:
- gradio
- requests
- websockets
"""

import asyncio
import json
import uuid
import time
from datetime import datetime
import threading
import queue
import gradio as gr
import requests
import websockets
from client_example import MarktplaatsSearchClient

# Configure client
API_BASE_URL = "http://localhost:8000"
client = MarktplaatsSearchClient(base_url=API_BASE_URL)

# Global state
active_searches = {}
notification_queue = queue.Queue()
ws_connections = {}
search_results_cache = {}

def format_datetime(dt):
    """Format datetime for display."""
    if not dt:
        return "Never"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")

async def websocket_listener(search_id):
    """Background WebSocket listener for a search."""
    uri = f"ws://localhost:8000/ws/{search_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Store websocket connection
            ws_connections[search_id] = websocket
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Add to notification queue
                    notification_queue.put({
                        "search_id": search_id,
                        "timestamp": datetime.now(),
                        "data": data
                    })
                    
                    # Update active searches info
                    if search_id in active_searches:
                        active_searches[search_id]["last_notification"] = datetime.now()
                        active_searches[search_id]["listings_found"] = data.get("total_found", 0)
                except Exception as e:
                    print(f"Error in websocket listener: {e}")
                    break
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        if search_id in ws_connections:
            del ws_connections[search_id]
            
def start_websocket_listener(search_id):
    """Start a WebSocket listener for a search."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_listener(search_id))
    
def notification_processor():
    """Process notifications from the queue."""
    while True:
        try:
            # Check if there are any notifications
            notification = notification_queue.get(block=True, timeout=1)
            
            # Process the notification
            print(f"Received notification: {notification}")
            
        except queue.Empty:
            # No notifications in queue
            time.sleep(0.1)
        except Exception as e:
            print(f"Error processing notification: {e}")
            time.sleep(1)

# Start notification processor in a background thread
threading.Thread(target=notification_processor, daemon=True).start()

def create_search(query, price_from, price_to, interval_minutes, limit):
    """Create a new search."""
    try:
        # Input validation
        if not query.strip():
            return "Error: Query cannot be empty", None
            
        price_from = int(price_from) if price_from else None
        price_to = int(price_to) if price_to else None
        interval_minutes = max(5, int(interval_minutes))  # Minimum 5 minutes
        limit = min(25, max(1, int(limit)))  # Between 1 and 25
        
        # Create search
        search_params = {
            "query": query,
            "interval_minutes": interval_minutes,
            "limit": limit
        }
        
        if price_from is not None:
            search_params["price_from"] = price_from
        if price_to is not None:
            search_params["price_to"] = price_to
            
        response = client.create_search(**search_params)
        
        search_id = response["search_id"]
        status = response["status"]
        
        # Store in active searches
        active_searches[search_id] = {
            "query": query,
            "price_from": price_from,
            "price_to": price_to,
            "interval_minutes": interval_minutes,
            "created_at": datetime.now(),
            "active": True,
            "last_run": status.get("last_run"),
            "next_run": status.get("next_run"),
            "listings_found": status.get("listings_found", 0),
            "last_notification": None
        }
        
        # Start WebSocket listener
        start_websocket_listener(search_id)
        
        return f"Search created successfully with ID: {search_id}", get_active_searches_table()
        
    except Exception as e:
        return f"Error creating search: {e}", None

def get_search_results(search_id):
    """Get results for a search."""
    if search_id == "Select a search":
        return "Please select a search first", ""
    
    try:
        # Call API to get results
        response = requests.get(f"{API_BASE_URL}/search/{search_id}/results")
        response.raise_for_status()
        results = response.json()
        
        # Cache results
        search_results_cache[search_id] = results
        
        # Format HTML
        html = ["<h3>Search Results</h3>"]
        html.append("<table style='width:100%; border-collapse: collapse;'>")
        html.append("<tr style='background-color: #f2f2f2;'>")
        html.append("<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Title</th>")
        html.append("<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Price</th>")
        html.append("<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Location</th>")
        html.append("<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Date</th>")
        html.append("<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Link</th>")
        html.append("</tr>")
        
        if not results:
            html.append("<tr><td colspan='5' style='border: 1px solid #ddd; padding: 8px;'>No results found</td></tr>")
        else:
            for listing in results:
                html.append("<tr>")
                html.append(f"<td style='border: 1px solid #ddd; padding: 8px;'>{listing.get('title', '')}</td>")
                html.append(f"<td style='border: 1px solid #ddd; padding: 8px;'>€{listing.get('price', 0)}</td>")
                
                location = listing.get('location', {})
                location_str = f"{location.get('city', '')}, {location.get('region', '')}"
                html.append(f"<td style='border: 1px solid #ddd; padding: 8px;'>{location_str}</td>")
                
                date = listing.get('date_published', '')
                html.append(f"<td style='border: 1px solid #ddd; padding: 8px;'>{date}</td>")
                
                url = listing.get('url', '#')
                html.append(f"<td style='border: 1px solid #ddd; padding: 8px;'><a href='{url}' target='_blank'>View</a></td>")
                html.append("</tr>")
                
        html.append("</table>")
        
        return f"Found {len(results)} results", "\n".join(html)
    except Exception as e:
        return f"Error getting results: {e}", ""

def stop_search(search_id):
    """Stop a search."""
    if search_id == "Select a search":
        return "Please select a search first", ""
    
    try:
        # Call API to stop search
        response = requests.post(f"{API_BASE_URL}/search/{search_id}/stop")
        response.raise_for_status()
        
        # Update active searches
        if search_id in active_searches:
            active_searches[search_id]["active"] = False
            
        return f"Search {search_id} stopped", get_active_searches_table()
    except Exception as e:
        return f"Error stopping search: {e}", ""

def delete_search(search_id):
    """Delete a search."""
    if search_id == "Select a search":
        return "Please select a search first", ""
    
    try:
        # Call API to delete search
        response = requests.delete(f"{API_BASE_URL}/search/{search_id}")
        response.raise_for_status()
        
        # Remove from active searches
        if search_id in active_searches:
            del active_searches[search_id]
            
        return f"Search {search_id} deleted", get_active_searches_table()
    except Exception as e:
        return f"Error deleting search: {e}", ""

def run_search_now(search_id):
    """Run a search immediately."""
    if search_id == "Select a search":
        return "Please select a search first", ""
    
    try:
        # Call API to run search now
        response = requests.post(f"{API_BASE_URL}/search/{search_id}/run")
        response.raise_for_status()
        
        # Update UI
        return f"Search {search_id} started", get_active_searches_table()
    except Exception as e:
        return f"Error running search: {e}", ""

def get_active_searches_table():
    """Generate HTML table of active searches."""
    if not active_searches:
        return "<p>No active searches. Create one using the form.</p>"
    
    html = ["<table style='width:100%; border-collapse: collapse;'>"]
    html.append("<tr><th>ID</th><th>Query</th><th>Status</th><th>Last Run</th><th>Next Run</th><th>Found</th></tr>")
    
    for search_id, info in active_searches.items():
        status = "Active" if info.get("active", False) else "Stopped"
        last_run = format_datetime(info.get("last_run"))
        next_run = format_datetime(info.get("next_run"))
        
        html.append(f"""
        <tr>
            <td>{search_id}</td>
            <td>{info.get('query', '')}</td>
            <td>{status}</td>
            <td>{last_run}</td>
            <td>{next_run}</td>
            <td>{info.get('listings_found', 0)}</td>
        </tr>
        """)
        
    html.append("</table>")
    
    return "\n".join(html)

def get_search_dropdown():
    """Get dropdown options for search selection."""
    try:
        options = ["Select a search"]
        if active_searches:
            options.extend(list(active_searches.keys()))
        return {"choices": options, "value": "Select a search"}
    except Exception as e:
        print(f"Error getting search dropdown: {e}")
        return {"choices": ["Select a search"], "value": "Select a search"}

def load_searches():
    """Load existing searches from the API."""
    return refresh_searches()

def refresh_searches():
    """Refresh the list of active searches."""
    try:
        # Clear and rebuild active searches
        global active_searches
        active_searches = {}
        
        # Get search data from API
        search_statuses = client.get_all_searches()
        
        for status in search_statuses:
            search_id = str(status["search_id"])
            active_searches[search_id] = {
                "query": status["query"],
                "price_from": status["search_params"].get("price_from"),
                "price_to": status["search_params"].get("price_to"),
                "interval_minutes": status["interval_minutes"],
                "active": status["active"],
                "limit": status["search_params"].get("limit", 25),
                "created_at": datetime.now(),  # API doesn't provide creation time
                "last_run": status["last_run"],
                "next_run": status["next_run"],
                "listings_found": status["listings_found"],
                "last_notification": None
            }
            
            # Start WebSocket connection if search is active
            if status["active"] and search_id not in ws_connections:
                threading.Thread(target=start_websocket_listener, args=(search_id,), daemon=True).start()
        
        # Update UI components        
        table = get_active_searches_table()
        dropdown = get_search_dropdown()
        return table, dropdown
        
    except Exception as e:
        print(f"Error refreshing searches: {e}")
        # Return empty but valid components
        return get_active_searches_table(), get_search_dropdown()

# Create Gradio interface
with gr.Blocks(css="""
    .search-results {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
    }
    .listing-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    tr:hover {background-color: #f5f5f5;}
""") as app:
    gr.Markdown("# Marktplaats Search Client")
    
    with gr.Tabs(elem_id="main_tabs") as tabs:
        # New Search Tab
        with gr.TabItem("Create Search", elem_id="create_tab"):
            with gr.Row():
                with gr.Column():
                    query_input = gr.Textbox(label="Search Query", placeholder="e.g. macbook pro")
                    
                    with gr.Row():
                        price_from = gr.Textbox(label="Min Price (€)", placeholder="Optional")
                        price_to = gr.Textbox(label="Max Price (€)", placeholder="Optional")
                    
                    with gr.Row():
                        interval = gr.Slider(minimum=5, maximum=120, value=60, step=5, label="Check Interval (minutes)")
                        limit = gr.Slider(minimum=1, maximum=25, value=10, step=1, label="Results Limit")
                    
                    create_btn = gr.Button("Create Search", variant="primary")
                    create_output = gr.Textbox(label="Status")
                
                with gr.Column():
                    gr.Markdown("### Active Searches")
                    searches_table = gr.HTML()
                    refresh_btn = gr.Button("Refresh")
        
        # Manage Searches Tab
        with gr.TabItem("Manage Searches", elem_id="manage_tab"):
            with gr.Row():
                with gr.Column():
                    search_dropdown = gr.Dropdown(choices=[], value=None, label="Select Search")
                    
                    with gr.Row():
                        run_now_btn = gr.Button("Run Now")
                        stop_btn = gr.Button("Stop Search")
                        delete_btn = gr.Button("Delete Search")
                    
                    manage_output = gr.Textbox(label="Status")
                
                with gr.Column():
                    searches_table_manage = gr.HTML()
        
        # View Results Tab
        with gr.TabItem("View Results", elem_id="results_tab"):
            with gr.Row():
                with gr.Column():
                    results_dropdown = gr.Dropdown(choices=[], value=None, label="Select Search")
                    get_results_btn = gr.Button("Get Results", variant="primary")
                    results_status = gr.Textbox(label="Status")
                
            results_display = gr.HTML()
    
    # Event handlers
    create_btn.click(
        create_search, 
        inputs=[query_input, price_from, price_to, interval, limit], 
        outputs=[create_output, searches_table]
    )
    
    refresh_btn.click(
        refresh_searches,
        outputs=[searches_table, search_dropdown]
    )
    
    run_now_btn.click(
        run_search_now,
        inputs=[search_dropdown],
        outputs=[manage_output, searches_table_manage]
    )
    
    stop_btn.click(
        stop_search,
        inputs=[search_dropdown],
        outputs=[manage_output, searches_table_manage]
    )
    
    delete_btn.click(
        delete_search,
        inputs=[search_dropdown],
        outputs=[manage_output, searches_table_manage]
    )
    
    get_results_btn.click(
        get_search_results,
        inputs=[results_dropdown],
        outputs=[results_status, results_display]
    )
    
    # Keep dropdowns in sync
    search_dropdown.change(
        lambda x: x if x != "Select a search" else "Select a search",
        inputs=[search_dropdown],
        outputs=[results_dropdown]
    )
    results_dropdown.change(
        lambda x: x if x != "Select a search" else "Select a search",
        inputs=[results_dropdown],
        outputs=[search_dropdown]
    )
    
    # Wrapper function for loading searches on app start
    def init_load():
        return refresh_searches()
    
    # Load searches on start
    app.load(init_load, outputs=[searches_table, search_dropdown])
    
    # Refresh tables periodically (without calling any function)
    app.load(lambda: {"every": 10}, outputs=[refresh_btn])

# Launch the app
if __name__ == "__main__":
    print("Starting Marktplaats Search Gradio UI...")
    print(f"Connecting to API at {API_BASE_URL}")
    app.queue().launch(share=False, inbrowser=True) 