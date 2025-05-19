# MarktplaatsSearch API

This document describes the API for managing Marktplaats searches. The API allows users to start, monitor, and manage automated searches for listings on Marktplaats.

**Authentication:** All API endpoints that manage or retrieve user-specific data require an API token to be passed in the `Authorization` header (e.g., `Authorization: Bearer <your_api_token>`).

**Data Persistence:** Search configurations, their status, and collected results are stored in local files on the server (e.g., JSON or SQLite files).

## API Endpoints

### 1. Start a New Search

*   **Method:** `POST`
*   **Path:** `/api/searches`
*   **Description:** Initiates a new search process based on the provided query parameters and search interval.
*   **Request Body (JSON):**
    *   `query` (string, required): The search term (e.g., "Samsung SSD").
    *   `zip_code` (string, optional): The postal code for location-based searches.
    *   `distance` (integer, optional): Search radius in meters.
    *   `price_from` (integer, optional): Minimum price.
    *   `price_to` (integer, optional): Maximum price.
    *   `limit` (integer, optional, default: 25): Number of results per page/fetch.
    *   `sort_by` (string, optional): Sorting criteria (e.g., "LOCATION", "PRICE").
    *   `sort_order` (string, optional): Sorting order ("ASC", "DESC").
    *   `interval` (integer, required): The interval in seconds at which the search should be re-executed or checked for new results.
*   **Response:**
    *   `201 Created`: On successful creation, returns the ID of the newly created search and its initial status.
    *   `400 Bad Request`: If required parameters are missing or invalid.

### 2. Get All Searches (for current user)

*   **Method:** `GET`
*   **Path:** `/api/searches`
*   **Description:** Retrieves a list of all searches initiated by the authenticated user, including their current status (e.g., active, inactive, completed) and basic configuration.
*   **Request Parameters:** None.
*   **Response:**
    *   `200 OK`: Returns an array of search objects. Each object includes `search_id`, `query`, `status`, `interval`, etc.

### 3. End a Search

*   **Method:** `POST` (or `PUT` if considered an update to state)
*   **Path:** `/api/searches/{search_id}/end`
*   **Description:** Stops an active search process. The search is marked as "inactive," polling for new results ceases, but its configuration and any collected results are retained.
*   **Request Parameters (Path):**
    *   `search_id` (string, required): The ID of the search to end.
*   **Response:**
    *   `200 OK`: If the search was successfully marked as inactive.
    *   `404 Not Found`: If the `search_id` does not exist.

### 4. Change a Query

*   **Method:** `PUT`
*   **Path:** `/api/searches/{search_id}/query`
*   **Description:** Modifies the search query parameters (e.g., search term, price range) for an existing search. This can apply to an active search (modifying it live) or a saved/inactive search configuration.
*   **Request Parameters (Path):**
    *   `search_id` (string, required): The ID of the search to modify.
*   **Request Body (JSON):**
    *   Contains the query parameters to update (e.g., `query`, `price_to`). Only provided fields will be updated.
*   **Response:**
    *   `200 OK`: On successful update, returns the updated search configuration.
    *   `404 Not Found`: If the `search_id` does not exist.
    *   `400 Bad Request`: If the new query parameters are invalid.

### 5. Change an Interval

*   **Method:** `PUT`
*   **Path:** `/api/searches/{search_id}/interval`
*   **Description:** Modifies the polling interval for an existing search. This can apply to an active search or a saved/inactive search configuration.
*   **Request Parameters (Path):**
    *   `search_id` (string, required): The ID of the search to modify.
*   **Request Body (JSON):**
    *   `interval` (integer, required): The new interval in seconds.
*   **Response:**
    *   `200 OK`: On successful update, returns the updated search configuration.
    *   `404 Not Found`: If the `search_id` does not exist.
    *   `400 Bad Request`: If the interval is invalid.

### 6. Get List of Results

*   **Method:** `GET`
*   **Path:** `/api/searches/{search_id}/results`
*   **Description:** Retrieves a paginated list of results (listings) collected for a specific search.
*   **Request Parameters (Path):**
    *   `search_id` (string, required): The ID of the search whose results are to be fetched.
*   **Request Parameters (Query):**
    *   `page` (integer, optional, default: 1): The page number for pagination.
    *   `per_page` (integer, optional, default: 20): Number of results per page.
*   **Response:**
    *   `200 OK`: Returns a paginated list of search results. Each result includes an identifier (e.g., original Marktplaats item ID or URL) that can be used to fetch more details.
    *   `404 Not Found`: If the `search_id` does not exist.

### 7. Get More Details on Individual Results

*   **Method:** `GET`
*   **Path:** `/api/results/{result_id}` (Alternatively, could be `/api/searches/{search_id}/results/{result_id}` if results are strictly namespaced under searches)
*   **Description:** Retrieves detailed information for an individual search result (listing). The `result_id` is typically an identifier obtained from the "Get List of Results" endpoint (e.g., the original ID from Marktplaats).
*   **Request Parameters (Path):**
    *   `result_id` (string, required): The unique identifier of the listing/result.
*   **Response:**
    *   `200 OK`: Returns detailed information about the specified result.
    *   `404 Not Found`: If the `result_id` does not exist or is not accessible.
