"""
Comprehensive API endpoint tests for MarktplaatsSearch application.
Tests all authentication, search management, and result endpoints.
"""

import asyncio
from typing import Any

import httpx

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "test_api_user"


class APITester:
    """Comprehensive API endpoint testing class."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: str | None = None
        self.user_data: dict[str, Any] | None = None
        self.created_searches: list = []

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        # Cleanup: delete any created searches
        if self.token:
            for search_id in self.created_searches:
                try:
                    await self.delete_search(search_id)
                except:
                    pass

        await self.client.aclose()

    def _headers(self) -> dict[str, str]:
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make authenticated API request."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())

        response = await self.client.request(method=method, url=url, headers=headers, **kwargs)
        return response

    # Authentication endpoints
    async def create_user(self, username: str = TEST_USERNAME) -> dict[str, Any]:
        """Test user creation via manage_users.py script."""
        import re
        import subprocess

        try:
            # Create user via CLI tool
            result = subprocess.run(
                ["uv", "run", "python", "manage_users.py", "create", "--username", username],
                capture_output=True,
                text=True,
                cwd="/Users/jurrejan/Documents/development/python/MarktplaatsSearch",
            )

            if result.returncode != 0:
                raise Exception(f"User creation failed: {result.stderr}")

            # Extract token from output
            token_match = re.search(r"API Token: (mps_[a-f0-9]+)", result.stdout)
            if not token_match:
                raise Exception("Could not extract token from output")

            self.token = token_match.group(1)
            return {"username": username, "token": self.token}

        except Exception as e:
            print(f"User creation failed: {e}")
            raise

    async def test_auth_me(self) -> dict[str, Any]:
        """Test GET /api/auth/me endpoint."""
        response = await self.request("GET", "/api/auth/me")
        if response.status_code != 200:
            raise Exception(f"Auth me failed: {response.status_code} - {response.text}")

        self.user_data = response.json()
        return self.user_data

    async def test_token_rotation(self) -> str:
        """Test POST /api/auth/rotate-token endpoint."""
        response = await self.request("POST", "/api/auth/rotate-token")
        if response.status_code != 200:
            raise Exception(f"Token rotation failed: {response.status_code} - {response.text}")

        new_token_data = response.json()
        self.token = new_token_data["new_token"]
        return self.token

    # Search management endpoints
    async def create_search(self, search_data: dict[str, Any]) -> dict[str, Any]:
        """Test POST /api/searches endpoint."""
        response = await self.request("POST", "/api/searches", json=search_data)
        if response.status_code != 201:
            raise Exception(f"Search creation failed: {response.status_code} - {response.text}")

        search = response.json()
        self.created_searches.append(search["search_id"])
        return search

    async def get_searches(self, skip: int = 0, limit: int = 100) -> list:
        """Test GET /api/searches endpoint."""
        response = await self.request("GET", f"/api/searches?skip={skip}&limit={limit}")
        if response.status_code != 200:
            raise Exception(f"Get searches failed: {response.status_code} - {response.text}")

        return response.json()

    async def get_search_details(self, search_id: str) -> dict[str, Any]:
        """Test GET /api/searches/{search_id} endpoint."""
        response = await self.request("GET", f"/api/searches/{search_id}")
        if response.status_code != 200:
            raise Exception(f"Get search details failed: {response.status_code} - {response.text}")

        return response.json()

    async def update_search(self, search_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """Test PUT /api/searches/{search_id} endpoint."""
        response = await self.request("PUT", f"/api/searches/{search_id}", json=update_data)
        if response.status_code != 200:
            raise Exception(f"Search update failed: {response.status_code} - {response.text}")

        return response.json()

    async def end_search(self, search_id: str) -> dict[str, Any]:
        """Test POST /api/searches/{search_id}/end endpoint."""
        response = await self.request("POST", f"/api/searches/{search_id}/end")
        if response.status_code != 200:
            raise Exception(f"End search failed: {response.status_code} - {response.text}")

        return response.json()

    async def delete_search(self, search_id: str) -> bool:
        """Test DELETE /api/searches/{search_id} endpoint."""
        response = await self.request("DELETE", f"/api/searches/{search_id}")
        if response.status_code != 204:
            raise Exception(f"Delete search failed: {response.status_code} - {response.text}")

        return True

    # Results endpoints
    async def get_search_results(
        self, search_id: str, skip: int = 0, limit: int = 20, show_new_only: bool = False
    ) -> list:
        """Test GET /api/searches/{search_id}/results endpoint."""
        params = f"skip={skip}&limit={limit}&show_new_only={show_new_only}"
        response = await self.request("GET", f"/api/searches/{search_id}/results?{params}")
        if response.status_code != 200:
            raise Exception(f"Get search results failed: {response.status_code} - {response.text}")

        return response.json()

    async def get_listing_details(
        self, listing_id: str, mark_as_read: bool = True
    ) -> dict[str, Any]:
        """Test GET /api/results/{listing_id} endpoint."""
        response = await self.request(
            "GET", f"/api/results/{listing_id}?mark_as_read={mark_as_read}"
        )
        if response.status_code != 200:
            raise Exception(f"Get listing details failed: {response.status_code} - {response.text}")

        return response.json()


async def run_comprehensive_test():
    """Run comprehensive API endpoint tests."""
    print("🚀 Starting comprehensive API endpoint tests...")

    async with APITester() as tester:
        test_results = {"passed": 0, "failed": 0, "errors": []}

        def log_test(name: str, success: bool, error: str = None):
            if success:
                print(f"✅ {name}")
                test_results["passed"] += 1
            else:
                print(f"❌ {name}: {error}")
                test_results["failed"] += 1
                test_results["errors"].append(f"{name}: {error}")

        # Test 1: User Creation and Authentication
        try:
            user_data = await tester.create_user()
            log_test("Create user", True)
            print(f"   👤 Created user: {user_data['username']}")
            print(f"   🔑 Token: {user_data['token'][:20]}...")
        except Exception as e:
            log_test("Create user", False, str(e))
            return test_results

        # Test 2: Auth Me
        try:
            auth_data = await tester.test_auth_me()
            log_test("GET /api/auth/me", True)
            print(f"   📋 User ID: {auth_data.get('id')}, Active: {auth_data.get('is_active')}")
        except Exception as e:
            log_test("GET /api/auth/me", False, str(e))

        # Test 3: Token Rotation
        try:
            new_token = await tester.test_token_rotation()
            log_test("POST /api/auth/rotate-token", True)
            print(f"   🔄 New token: {new_token[:20]}...")
        except Exception as e:
            log_test("POST /api/auth/rotate-token", False, str(e))

        # Test 4: Create Search
        search_data = {
            "query": "test laptop",
            "zip_code": "1000AA",
            "distance": 5000,
            "price_from": 100,
            "price_to": 500,
            "limit": 25,
            "sort_by": "price",
            "sort_order": "asc",
            "interval": 300,
        }

        try:
            search = await tester.create_search(search_data)
            log_test("POST /api/searches", True)
            print(f"   🔍 Created search: {search['search_id'][:8]}... Query: '{search['query']}'")
            test_search_id = search["search_id"]
        except Exception as e:
            log_test("POST /api/searches", False, str(e))
            return test_results

        # Test 5: Get All Searches
        try:
            searches = await tester.get_searches()
            log_test("GET /api/searches", True)
            print(f"   📝 Found {len(searches)} searches")
        except Exception as e:
            log_test("GET /api/searches", False, str(e))

        # Test 6: Get Search Details
        try:
            details = await tester.get_search_details(test_search_id)
            log_test("GET /api/searches/{id}", True)
            print(f"   📄 Search status: {details['status']}, interval: {details['interval']}s")
        except Exception as e:
            log_test("GET /api/searches/{id}", False, str(e))

        # Test 7: Update Search
        update_data = {"price_to": 750, "interval": 600}
        try:
            updated = await tester.update_search(test_search_id, update_data)
            log_test("PUT /api/searches/{id}", True)
            print(
                f"   ✏️  Updated price_to: {updated['price_to']}, interval: {updated['interval']}s"
            )
        except Exception as e:
            log_test("PUT /api/searches/{id}", False, str(e))

        # Test 8: Get Search Results (will likely be empty but should work)
        try:
            results = await tester.get_search_results(test_search_id)
            log_test("GET /api/searches/{id}/results", True)
            print(f"   📊 Found {len(results)} results")
        except Exception as e:
            log_test("GET /api/searches/{id}/results", False, str(e))

        # Test 9: End Search
        try:
            ended = await tester.end_search(test_search_id)
            log_test("POST /api/searches/{id}/end", True)
            print(f"   ⏹️  Search status: {ended['status']}")
        except Exception as e:
            log_test("POST /api/searches/{id}/end", False, str(e))

        # Test 10: Delete Search
        try:
            await tester.delete_search(test_search_id)
            log_test("DELETE /api/searches/{id}", True)
            print("   🗑️  Search deleted successfully")
        except Exception as e:
            log_test("DELETE /api/searches/{id}", False, str(e))

        # Test 11: Static File Serving
        try:
            response = await tester.client.get(f"{tester.base_url}/")
            if response.status_code == 200 and "MarktplaatsSearch" in response.text:
                log_test("GET / (Web UI)", True)
                print("   🌐 Web UI served successfully")
            else:
                log_test("GET / (Web UI)", False, f"Status: {response.status_code}")
        except Exception as e:
            log_test("GET / (Web UI)", False, str(e))

    return test_results


if __name__ == "__main__":
    print("MarktplaatsSearch API Endpoint Tests")
    print("=" * 50)

    # Run tests
    results = asyncio.run(run_comprehensive_test())

    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📈 Success Rate: {results['passed']/(results['passed']+results['failed'])*100:.1f}%")

    if results["errors"]:
        print("\n🚨 ERRORS:")
        for error in results["errors"]:
            print(f"   • {error}")

    print(f"\n{'🎉 ALL TESTS PASSED!' if results['failed'] == 0 else '⚠️  Some tests failed'}")
