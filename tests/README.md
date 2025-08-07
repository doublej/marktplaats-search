# MarktplaatsSearch API Test Suite

Comprehensive testing suite for the MarktplaatsSearch API that validates all endpoints and functionality.

## 🧪 Test Coverage

### Authentication Endpoints
- ✅ User creation via CLI (`manage_users.py`)
- ✅ `GET /api/auth/me` - Get current user info
- ✅ `POST /api/auth/rotate-token` - Rotate API token

### Search Management Endpoints  
- ✅ `POST /api/searches` - Create new search
- ✅ `GET /api/searches` - List all searches (paginated)
- ✅ `GET /api/searches/{id}` - Get search details
- ✅ `PUT /api/searches/{id}` - Update search parameters
- ✅ `POST /api/searches/{id}/end` - Stop/deactivate search
- ✅ `DELETE /api/searches/{id}` - Delete search and results

### Results Endpoints
- ✅ `GET /api/searches/{id}/results` - Get search results (paginated)
- ✅ `GET /api/results/{id}` - Get listing details

### Static File Serving
- ✅ `GET /` - Web UI serving

## 🚀 Running Tests

### Prerequisites
Make sure the FastAPI server is running:
```bash
python main.py
```
Server should be accessible at `http://localhost:8000`

### Run All Tests
```bash
cd tests/
python run_tests.py
```

### Run Individual Test Module
```bash
cd tests/
python test_api_endpoints.py
```

## 📊 Test Features

### Comprehensive Validation
- **Authentication flow**: Creates test user, validates token, rotates tokens
- **CRUD operations**: Full create, read, update, delete cycle for searches
- **Data validation**: Ensures API responses match expected schemas
- **Error handling**: Tests both success and failure scenarios
- **Cleanup**: Automatically removes test data after completion

### Smart Test Management
- **Automatic cleanup**: Removes created searches/users after tests
- **Server validation**: Checks server availability before starting
- **Detailed reporting**: Shows pass/fail rates and specific errors
- **Timing information**: Reports test duration and performance

### Real API Testing
- **No mocking**: Tests against actual running API
- **Full integration**: Validates database, scheduler, authentication
- **Production-like**: Uses real HTTP requests with proper headers
- **Comprehensive**: Tests all major user workflows

## 📈 Test Output Example

```
🔍 MarktplaatsSearch API Test Suite
============================================================
📅 Started at: 2025-08-07 15:30:00
🐍 Python: 3.12.0
============================================================
🚀 Starting comprehensive API endpoint tests...

✅ Create user
   👤 Created user: test_api_user
   🔑 Token: mps_43f3b7a478985d32...
✅ GET /api/auth/me
   📋 User ID: 5, Active: True
✅ POST /api/auth/rotate-token
   🔄 New token: mps_a8d6c2f14e927b54...
✅ POST /api/searches
   🔍 Created search: 9292ad1c... Query: 'test laptop'
✅ GET /api/searches
   📝 Found 1 searches
✅ GET /api/searches/{id}
   📄 Search status: active, interval: 300s
✅ PUT /api/searches/{id}
   ✏️  Updated price_to: 750, interval: 600s
✅ GET /api/searches/{id}/results
   📊 Found 0 results
✅ POST /api/searches/{id}/end
   ⏹️  Search status: inactive
✅ DELETE /api/searches/{id}
   🗑️  Search deleted successfully
✅ GET / (Web UI)
   🌐 Web UI served successfully

============================================================
📊 FINAL TEST REPORT
============================================================
⏱️  Duration: 2.35 seconds
📋 Total Tests: 11
✅ Passed: 11
❌ Failed: 0
📈 Success Rate: 100.0%
🎉 PERFECT SCORE! All endpoints working correctly!
============================================================
✨ Test run complete!
```

## 🔧 Test Configuration

### Default Settings
- **Base URL**: `http://localhost:8000`
- **Test Username**: `test_api_user`
- **Timeout**: 30 seconds per request
- **Cleanup**: Automatic after each test run

### Customization
You can modify test parameters in `test_api_endpoints.py`:
- Change `BASE_URL` for different server locations
- Modify `TEST_USERNAME` for different test user names
- Adjust timeout values for slower systems

## 🐛 Troubleshooting

### Common Issues
1. **Server not running**: Ensure `python main.py` is running
2. **Port conflicts**: Check if port 8000 is available
3. **Database issues**: Ensure database is properly initialized
4. **Permission errors**: Check file permissions for test directory

### Test Failures
If tests fail:
1. Check server logs for errors
2. Verify database connectivity
3. Ensure all dependencies are installed
4. Review detailed error messages in test output

## 📝 Adding New Tests

To add new test cases:
1. Add test methods to `APITester` class
2. Call new tests in `run_comprehensive_test()`
3. Follow the existing pattern for error handling
4. Update this README with new test coverage

The test suite is designed to be easily extensible for new API endpoints and functionality.