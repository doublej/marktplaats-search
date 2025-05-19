#!/usr/bin/env python3
"""
Simple client example for integrating with the MarktplaatsSearch API.

This example demonstrates:
1. Creating a new search
2. Getting search status
3. Receiving real-time notifications via WebSocket
4. Managing searches (stop, run now, delete)

Requirements:
- requests
- websockets
"""

import asyncio
import json
import uuid
import sys
from datetime import datetime
import requests
import websockets


class MarktplaatsSearchClient:
    """Client for interacting with the MarktplaatsSearch API."""
    
    def __init__(self, base_url="http://localhost:8000"):
        """Initialize the client with the API base URL."""
        self.base_url = base_url
        self.api_url = f"{base_url}/search"
        self.ws_url = f"ws://{base_url.replace('http://', '')}/ws"
    
    def create_search(self, query, **kwargs):
        """
        Create a new search with the given parameters.
        
        Args:
            query (str): The search query
            **kwargs: Additional search parameters like:
                - price_from (float): Minimum price
                - price_to (float): Maximum price
                - interval_minutes (int): How often to check for new listings
                - limit (int): Maximum number of results per search
                
        Returns:
            dict: The search response with search_id and status
        """
        payload = {"query": query, **kwargs}
        response = requests.post(self.api_url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_all_searches(self):
        """Get all active searches."""
        response = requests.get(self.api_url)
        response.raise_for_status()
        return response.json()
    
    def get_search_status(self, search_id):
        """Get the status of a search by ID."""
        response = requests.get(f"{self.api_url}/{search_id}")
        response.raise_for_status()
        return response.json()
    
    def get_search_results(self, search_id):
        """Get the results of a search by ID."""
        response = requests.get(f"{self.api_url}/{search_id}/results")
        response.raise_for_status()
        return response.json()
    
    def run_search_now(self, search_id):
        """Run a search immediately and return the results."""
        response = requests.post(f"{self.api_url}/{search_id}/run")
        response.raise_for_status()
        return response.json()
    
    def stop_search(self, search_id):
        """Stop an active search."""
        response = requests.post(f"{self.api_url}/{search_id}/stop")
        response.raise_for_status()
        return response.json()
    
    def delete_search(self, search_id):
        """Delete a search."""
        response = requests.delete(f"{self.api_url}/{search_id}")
        response.raise_for_status()
        return response.json()
    
    async def listen_for_notifications(self, search_id, callback=None):
        """
        Connect to WebSocket and listen for real-time notifications.
        
        Args:
            search_id (str): The search ID to listen for
            callback (callable): A callback function that takes a notification message
                                as its argument, called when a notification is received
        """
        uri = f"{self.ws_url}/{search_id}"
        
        # Default callback function
        if callback is None:
            def default_callback(msg):
                msg_type = msg.get("type")
                data = msg.get("data", {})
                
                if msg_type == "status":
                    print(f"Search status: {data}")
                elif msg_type == "notification":
                    print(f"\n🔔 New listings found for query '{data.get('query')}'!")
                    print(f"New listings: {len(data.get('new_listings', []))}")
                    print(f"Total listings: {data.get('total_listings')}")
                    
                    # Print details of new listings
                    for i, listing in enumerate(data.get('new_listings', []), 1):
                        print(f"\n--- Listing {i} ---")
                        print(f"Title: {listing.get('title')}")
                        print(f"Price: €{listing.get('price')}")
                        if listing.get('link'):
                            print(f"Link: {listing.get('link')}")
                elif msg_type == "error":
                    print(f"Error: {data.get('message')}")
                elif msg_type == "pong":
                    print("Pong received (connection alive)")
            
            callback = default_callback
        
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to WebSocket for search ID {search_id}")
                
                # Set up a ping task to keep the connection alive
                async def ping():
                    while True:
                        await asyncio.sleep(30)
                        await websocket.send("ping")
                
                ping_task = asyncio.create_task(ping())
                
                try:
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        callback(data)
                except Exception as e:
                    print(f"WebSocket error: {e}")
                finally:
                    ping_task.cancel()
        
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")


async def example_usage():
    """Example usage of the MarktplaatsSearchClient."""
    client = MarktplaatsSearchClient()
    
    # 1. Create a new search
    search_query = "macbook pro"
    try:
        print(f"Creating search for '{search_query}'...")
        search_response = client.create_search(
            query=search_query,
            interval_minutes=15,  # Check every 15 minutes
            price_from=500,       # Min price €500
            price_to=2000,        # Max price €2000
            limit=10              # Show up to 10 results
        )
        
        search_id = search_response["search_id"]
        print(f"Search created with ID: {search_id}")
        print(f"Status: {search_response['status']}")
        
        # 2. Get search results
        print("\nInitial results:")
        results = client.get_search_results(search_id)
        print(f"Found {len(results)} listings")
        
        # Display first 3 results
        for i, listing in enumerate(results[:3], 1):
            print(f"\n--- Listing {i} ---")
            print(f"Title: {listing.get('title')}")
            print(f"Price: €{listing.get('price')}")
            if listing.get('link'):
                print(f"Link: {listing.get('link')}")
        
        # 3. Start listening for real-time notifications
        print("\nStarting WebSocket listener for real-time notifications...")
        print("Press Ctrl+C to stop")
        
        # Listen for notifications for 60 seconds or until user interrupts
        try:
            await asyncio.wait_for(
                client.listen_for_notifications(search_id),
                timeout=60
            )
        except asyncio.TimeoutError:
            print("\nWebSocket listener timeout reached")
        except KeyboardInterrupt:
            print("\nWebSocket listener stopped by user")
        
        # 4. Stop the search
        print("\nStopping the search...")
        stop_response = client.stop_search(search_id)
        print(f"Search stopped: {stop_response}")
        
        # 5. Delete the search when done
        print("\nDeleting the search...")
        delete_response = client.delete_search(search_id)
        print(f"Search deleted: {delete_response}")
    
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        print("Make sure the FastAPI server is running at http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run the example."""
    print("MarktplaatsSearch API Client Example")
    print("====================================")
    
    try:
        asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\nClient example stopped by user")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 