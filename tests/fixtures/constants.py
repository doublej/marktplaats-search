"""Test constants and templates for MarktplaatsSearch testing."""

from typing import Any

# API Configuration
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "test_user"
API_TIMEOUT = 30

# Database Configuration
TEST_DATABASE_URL = "sqlite:///test_marktplaats.db"

# Test Data Templates
SEARCH_DATA_TEMPLATE: dict[str, Any] = {
    "query": "iPhone 15",
    "zip_code": "1012",
    "distance": 10000,
    "price_from": 0,
    "price_to": 2000,
    "interval": 300,
    "is_active": True,
}

SEARCH_UPDATE_TEMPLATE: dict[str, Any] = {
    "query": "iPhone 15 Pro",
    "zip_code": "1013",
    "distance": 25000,
    "price_from": 500,
    "price_to": 1500,
    "interval": 600,
}

LISTING_DATA_TEMPLATE: dict[str, Any] = {
    "title": "Test iPhone 15 128GB",
    "url": "https://www.marktplaats.nl/listing/test123",
    "price": "€ 950,00",
    "price_numeric": 95000,
    "seller_name": "TestSeller",
    "location": "Amsterdam",
    "condition": "used",
    "is_new": False,
    "description": "Test listing description",
    "images": ["https://example.com/image1.jpg"],
}

USER_DATA_TEMPLATE: dict[str, Any] = {
    "user_identifier": "test_user_123",
    "is_active": True,
}

# Mock API Responses
MOCK_USER_RESPONSE: dict[str, Any] = {
    "id": "user123",
    "user_identifier": "test_user",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
    "last_activity": "2024-01-01T12:00:00Z",
}

MOCK_SEARCH_RESPONSE: dict[str, Any] = {
    "id": "search123",
    "query": "iPhone 15",
    "zip_code": "1012",
    "distance": 10000,
    "price_from": 0,
    "price_to": 2000,
    "interval": 300,
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
    "last_run": "2024-01-01T12:00:00Z",
}

MOCK_LISTING_RESPONSE: dict[str, Any] = {
    "id": "listing123",
    "title": "iPhone 15 128GB",
    "url": "https://www.marktplaats.nl/listing/test123",
    "price": "€ 950,00",
    "price_numeric": 95000,
    "seller_name": "TestSeller",
    "location": "Amsterdam",
    "condition": "used",
    "is_new": False,
    "created_at": "2024-01-01T00:00:00Z",
}

# Test Data Collections
TEST_ZIP_CODES = ["1012", "1013", "1071", "1091", "2000"]
TEST_QUERIES = ["iPhone 15", "MacBook Pro", "PlayStation 5", "Nintendo Switch"]
TEST_PRICES = [(0, 500), (500, 1000), (1000, 2000), (2000, 5000)]
TEST_DISTANCES = [5000, 10000, 25000, 50000, 75000]

# Error Response Templates
API_ERROR_RESPONSES: dict[str, dict[str, Any]] = {
    "auth_failed": {
        "status_code": 401,
        "detail": "Authentication failed",
        "error_type": "authentication_error",
    },
    "not_found": {
        "status_code": 404,
        "detail": "Resource not found",
        "error_type": "not_found_error",
    },
    "validation_error": {
        "status_code": 422,
        "detail": "Validation error",
        "error_type": "validation_error",
    },
    "server_error": {
        "status_code": 500,
        "detail": "Internal server error",
        "error_type": "server_error",
    },
}
