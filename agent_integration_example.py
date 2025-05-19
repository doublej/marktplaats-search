#!/usr/bin/env python3
"""
Advanced agent integration example for MarktplaatsSearch API.

This example demonstrates an autonomous agent that:
1. Manages multiple searches based on user preferences
2. Processes new listings with custom logic
3. Takes actions on interesting listings (e.g., sending notifications)
4. Uses a scoring system to prioritize listings

Requirements:
- requests
- websockets
- (Optional) smtp library for email notifications
"""

import asyncio
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import random  # Just for demonstration purposes

# Import the client
from client_example import MarktplaatsSearchClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("MarktplaatsAgent")


class ListingScorer:
    """
    Evaluates listings and assigns a score based on how well they match preferences.
    """
    
    def __init__(self, preferences: Dict[str, Any]):
        """
        Initialize with user preferences.
        
        Args:
            preferences: Dict with preference settings like:
                - keywords: List of positive keywords
                - negative_keywords: List of keywords to avoid
                - ideal_price: Ideal price point
                - price_range: Acceptable price range (+/-) from ideal
                - min_description_length: Minimum description length
                - preferred_locations: List of preferred locations
        """
        self.preferences = preferences
        logger.info(f"Initialized listing scorer with preferences: {preferences}")
    
    def score_listing(self, listing: Dict[str, Any]) -> float:
        """
        Score a listing based on how well it matches preferences.
        Returns a score between 0 and 1, where 1 is a perfect match.
        """
        score = 0.5  # Start with neutral score
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        price = listing.get('price')
        location = None
        if listing.get('location'):
            location = listing.get('location').get('city', '')
        
        # Check keywords (weighted heavily)
        for keyword in self.preferences.get('keywords', []):
            if keyword.lower() in title:
                score += 0.15
            elif description and keyword.lower() in description:
                score += 0.1
        
        # Check negative keywords (strong penalty)
        for keyword in self.preferences.get('negative_keywords', []):
            if keyword.lower() in title:
                score -= 0.2
            elif description and keyword.lower() in description:
                score -= 0.15
        
        # Check price (if specified)
        if price is not None and self.preferences.get('ideal_price') is not None:
            ideal_price = self.preferences['ideal_price']
            price_range = self.preferences.get('price_range', ideal_price * 0.2)  # Default 20%
            
            # Calculate how far price is from ideal (as percentage of price_range)
            price_diff = abs(price - ideal_price)
            if price_diff <= price_range:
                # Within range - score based on closeness to ideal
                price_score = 1 - (price_diff / price_range)
                score += price_score * 0.2  # Price is worth up to 0.2 points
            else:
                # Outside range - penalty based on how far outside
                penalty = min(0.2, (price_diff - price_range) / ideal_price)
                score -= penalty
        
        # Check description length
        min_length = self.preferences.get('min_description_length', 0)
        if description and len(description) >= min_length:
            score += 0.05
        
        # Check location (if preferences specified)
        if location and self.preferences.get('preferred_locations'):
            if location.lower() in [loc.lower() for loc in self.preferences['preferred_locations']]:
                score += 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))


class NotificationService:
    """
    Service for sending notifications about interesting listings.
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self.notification_count = 0
    
    async def send_notification(self, search_id: str, listing: Dict[str, Any], score: float) -> bool:
        """
        Send a notification about an interesting listing.
        
        Args:
            search_id: ID of the search that found the listing
            listing: The listing data
            score: Interest score (0-1)
            
        Returns:
            bool: True if notification was sent successfully
        """
        # In a real implementation, this would send an email, push notification, etc.
        # For this example, we'll just log it
        self.notification_count += 1
        
        # Format price nicely if available
        price_str = f"€{listing.get('price')}" if listing.get('price') is not None else "No price"
        
        logger.info(f"🔔 NOTIFICATION #{self.notification_count} (Score: {score:.2f})")
        logger.info(f"Search ID: {search_id}")
        logger.info(f"Title: {listing.get('title')}")
        logger.info(f"Price: {price_str}")
        
        if listing.get('location') and listing.get('location').get('city'):
            logger.info(f"Location: {listing.get('location').get('city')}")
            
        if listing.get('link'):
            logger.info(f"Link: {listing.get('link')}")
            
        logger.info("-" * 40)
        
        # Simulate sending time
        await asyncio.sleep(0.5)
        
        return True


class MarktplaatsAgent:
    """
    Autonomous agent for monitoring Marktplaats listings.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the agent.
        
        Args:
            base_url: Base URL of the MarktplaatsSearch API
        """
        # Initialize services
        self.client = MarktplaatsSearchClient(base_url=base_url)
        self.notification_service = NotificationService()
        
        # State
        self.active_searches: Dict[str, Dict[str, Any]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.monitors: Dict[str, asyncio.Task] = {}
        self.scorers: Dict[str, ListingScorer] = {}
        
        # Settings
        self.min_score_threshold = 0.7  # Minimum score for notifications
        
        logger.info("MarktplaatsAgent initialized")
    
    async def add_search(self, 
                         user_id: str, 
                         query: str, 
                         preferences: Optional[Dict[str, Any]] = None, 
                         **search_params) -> str:
        """
        Add a new search for a user with their preferences.
        
        Args:
            user_id: ID of the user who created the search
            query: Search query
            preferences: User preferences for scoring listings
            **search_params: Additional parameters for the search
            
        Returns:
            str: The search ID
        """
        # Store user preferences for this search
        if preferences is None:
            preferences = {
                "keywords": [word for word in query.split() if len(word) > 3],
                "negative_keywords": []
            }
        
        # Create the search
        try:
            logger.info(f"Creating search for '{query}' with params: {search_params}")
            response = self.client.create_search(query=query, **search_params)
            search_id = response["search_id"]
            
            # Initialize scorer for this search
            self.scorers[search_id] = ListingScorer(preferences)
            
            # Store search info
            self.active_searches[search_id] = {
                "user_id": user_id,
                "query": query,
                "params": search_params,
                "created_at": datetime.now(),
                "last_notification": None
            }
            
            # Store user preferences
            self.user_preferences[search_id] = preferences
            
            # Start monitoring this search
            self._start_monitoring(search_id)
            
            logger.info(f"Search created with ID: {search_id}")
            return search_id
            
        except Exception as e:
            logger.error(f"Error creating search: {e}")
            raise
    
    def _start_monitoring(self, search_id: str) -> None:
        """
        Start monitoring a search for new listings.
        
        Args:
            search_id: ID of the search to monitor
        """
        if search_id in self.monitors and not self.monitors[search_id].done():
            logger.warning(f"Search {search_id} is already being monitored")
            return
        
        # Start a background task to monitor this search
        self.monitors[search_id] = asyncio.create_task(
            self._monitor_search(search_id)
        )
        logger.info(f"Started monitoring search {search_id}")
    
    async def _monitor_search(self, search_id: str) -> None:
        """
        Monitor a search for new listings.
        
        Args:
            search_id: ID of the search to monitor
        """
        def create_notification_handler(search_id):
            """Create a notification handler for this search."""
            
            async def notification_handler(message: Dict[str, Any]) -> None:
                """Handle notifications from the WebSocket."""
                if message.get("type") == "notification":
                    data = message.get("data", {})
                    new_listings = data.get("new_listings", [])
                    
                    if new_listings:
                        logger.info(f"Received {len(new_listings)} new listings for search {search_id}")
                        await self._process_new_listings(search_id, new_listings)
                
                elif message.get("type") == "status":
                    logger.debug(f"Received status update for search {search_id}")
                
                elif message.get("type") == "error":
                    logger.error(f"Received error for search {search_id}: {message.get('data', {}).get('message')}")
            
            return notification_handler
        
        try:
            # Create a handler for this search
            handler = create_notification_handler(search_id)
            
            # Start the WebSocket listener
            logger.info(f"Connecting to WebSocket for search {search_id}")
            await self.client.listen_for_notifications(search_id, callback=handler)
            
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for search {search_id}")
        except Exception as e:
            logger.error(f"Error monitoring search {search_id}: {e}")
            
            # Wait a bit before reconnecting
            await asyncio.sleep(5)
            
            # Try to reconnect if the search is still active
            if search_id in self.active_searches:
                logger.info(f"Reconnecting to WebSocket for search {search_id}")
                self._start_monitoring(search_id)
    
    async def _process_new_listings(self, search_id: str, listings: List[Dict[str, Any]]) -> None:
        """
        Process new listings for a search.
        
        Args:
            search_id: ID of the search
            listings: List of new listings
        """
        # Get the scorer for this search
        scorer = self.scorers.get(search_id)
        if not scorer:
            logger.warning(f"No scorer found for search {search_id}")
            return
        
        # Score each listing
        scored_listings = []
        for listing in listings:
            score = scorer.score_listing(listing)
            scored_listings.append((listing, score))
        
        # Sort by score (highest first)
        scored_listings.sort(key=lambda x: x[1], reverse=True)
        
        # Process listings that meet the threshold
        interesting_listings = [
            (listing, score) for listing, score in scored_listings 
            if score >= self.min_score_threshold
        ]
        
        if interesting_listings:
            logger.info(f"Found {len(interesting_listings)} interesting listings for search {search_id}")
            
            # Update last notification time
            self.active_searches[search_id]["last_notification"] = datetime.now()
            
            # Notify about each interesting listing
            for listing, score in interesting_listings:
                await self.notification_service.send_notification(search_id, listing, score)
        else:
            logger.info(f"No interesting listings found for search {search_id} (scored {len(scored_listings)} listings)")
    
    async def stop_search(self, search_id: str) -> bool:
        """
        Stop a search.
        
        Args:
            search_id: ID of the search to stop
            
        Returns:
            bool: True if the search was stopped successfully
        """
        try:
            # Cancel the monitor task
            if search_id in self.monitors and not self.monitors[search_id].done():
                self.monitors[search_id].cancel()
            
            # Stop the search in the API
            response = self.client.stop_search(search_id)
            
            # Update local state
            if search_id in self.active_searches:
                self.active_searches[search_id]["active"] = False
            
            logger.info(f"Search {search_id} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping search {search_id}: {e}")
            return False
    
    async def delete_search(self, search_id: str) -> bool:
        """
        Delete a search.
        
        Args:
            search_id: ID of the search to delete
            
        Returns:
            bool: True if the search was deleted successfully
        """
        try:
            # Cancel the monitor task
            if search_id in self.monitors and not self.monitors[search_id].done():
                self.monitors[search_id].cancel()
            
            # Delete the search in the API
            response = self.client.delete_search(search_id)
            
            # Clean up local state
            if search_id in self.active_searches:
                del self.active_searches[search_id]
            
            if search_id in self.user_preferences:
                del self.user_preferences[search_id]
            
            if search_id in self.scorers:
                del self.scorers[search_id]
            
            if search_id in self.monitors:
                del self.monitors[search_id]
            
            logger.info(f"Search {search_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting search {search_id}: {e}")
            return False
    
    async def get_active_searches(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active searches, optionally filtered by user ID.
        
        Args:
            user_id: Optional user ID to filter searches
            
        Returns:
            List of search info dictionaries
        """
        searches = []
        
        for search_id, search_info in self.active_searches.items():
            if user_id is None or search_info.get("user_id") == user_id:
                # Get current status from the API
                try:
                    status = self.client.get_search_status(search_id)
                    searches.append({
                        "search_id": search_id,
                        "user_id": search_info.get("user_id"),
                        "query": search_info.get("query"),
                        "created_at": search_info.get("created_at"),
                        "last_notification": search_info.get("last_notification"),
                        "status": status
                    })
                except Exception as e:
                    logger.warning(f"Error getting status for search {search_id}: {e}")
                    # Include what we know locally
                    searches.append({
                        "search_id": search_id,
                        "user_id": search_info.get("user_id"),
                        "query": search_info.get("query"),
                        "created_at": search_info.get("created_at"),
                        "last_notification": search_info.get("last_notification"),
                        "status": "unknown"
                    })
        
        return searches


async def demo_agent():
    """Run a demonstration of the agent."""
    # Create the agent
    agent = MarktplaatsAgent()
    
    # Example user IDs
    users = ["user1", "user2"]
    
    # Example search configurations
    search_configs = [
        {
            "user_id": "user1",
            "query": "macbook pro",
            "preferences": {
                "keywords": ["macbook", "pro", "m1", "m2", "apple"],
                "negative_keywords": ["broken", "defect", "spares", "parts"],
                "ideal_price": 900,
                "price_range": 300,
                "min_description_length": 100,
                "preferred_locations": ["Amsterdam", "Utrecht", "Rotterdam"]
            },
            "search_params": {
                "price_from": 600,
                "price_to": 1500,
                "interval_minutes": 15
            }
        },
        {
            "user_id": "user2",
            "query": "playstation 5",
            "preferences": {
                "keywords": ["playstation", "ps5", "console", "controller"],
                "negative_keywords": ["broken", "defect", "spares", "parts", "bulk", "wholesale"],
                "ideal_price": 450,
                "price_range": 100,
                "preferred_locations": ["Amsterdam", "Haarlem", "Zaandam"]
            },
            "search_params": {
                "price_from": 350,
                "price_to": 600,
                "interval_minutes": 20
            }
        }
    ]
    
    # Create searches for each configuration
    search_ids = []
    for config in search_configs:
        user_id = config["user_id"]
        query = config["query"]
        preferences = config["preferences"]
        search_params = config["search_params"]
        
        try:
            search_id = await agent.add_search(
                user_id=user_id,
                query=query,
                preferences=preferences,
                **search_params
            )
            search_ids.append(search_id)
        except Exception as e:
            logger.error(f"Failed to create search for {query}: {e}")
    
    # Keep the agent running
    try:
        logger.info("Agent is running. Press Ctrl+C to stop.")
        
        # Simulate the agent running for a while
        for i in range(10):
            await asyncio.sleep(10)
            active_searches = await agent.get_active_searches()
            logger.info(f"Currently monitoring {len(active_searches)} searches")
            
            # Every 30 seconds, simulate a user stopping a search
            if i % 3 == 2 and search_ids:
                search_id = random.choice(search_ids)
                search_ids.remove(search_id)
                logger.info(f"Simulating user stopping search {search_id}")
                await agent.stop_search(search_id)
    
    except asyncio.CancelledError:
        logger.info("Demo cancelled")
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
    finally:
        # Clean up
        logger.info("Cleaning up agent resources...")
        for search_id in list(agent.active_searches.keys()):
            await agent.delete_search(search_id)


def main():
    """Run the agent demo."""
    print("MarktplaatsSearch Agent Demo")
    print("============================")
    print("This demo will create sample searches and monitor them for new listings.")
    print("Press Ctrl+C to stop the demo.")
    print()
    
    try:
        asyncio.run(demo_agent())
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 