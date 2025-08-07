#!/usr/bin/env python3
"""
Test runner script for MarktplaatsSearch API.
Runs comprehensive endpoint tests and generates a detailed report.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_api_endpoints import run_comprehensive_test


def print_header():
    """Print test header with system information."""
    print("🔍 MarktplaatsSearch API Test Suite")
    print("=" * 60)
    print(f"📅 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("=" * 60)


def print_footer(results: dict, start_time: float):
    """Print test footer with results and timing."""
    duration = time.time() - start_time
    total_tests = results['passed'] + results['failed']
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST REPORT")
    print("=" * 60)
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"📋 Total Tests: {total_tests}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    if total_tests > 0:
        success_rate = (results['passed'] / total_tests) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 PERFECT SCORE! All endpoints working correctly!")
        elif success_rate >= 90:
            print("🟢 EXCELLENT! API is highly functional")
        elif success_rate >= 75:
            print("🟡 GOOD! Most endpoints working")
        else:
            print("🔴 NEEDS ATTENTION! Several endpoints failing")
    
    if results['errors']:
        print(f"\n🚨 DETAILED ERRORS ({len(results['errors'])}):")
        print("-" * 40)
        for i, error in enumerate(results['errors'], 1):
            print(f"{i:2d}. {error}")
    
    print("=" * 60)
    print("✨ Test run complete!")


async def main():
    """Main test runner function."""
    print_header()
    start_time = time.time()
    
    try:
        # Check if server is running
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/", timeout=5.0)
                if response.status_code != 200:
                    print("❌ Server not responding correctly at http://localhost:8000")
                    print("   Please ensure the server is running with: python main.py")
                    return
            except Exception as e:
                print("❌ Could not connect to server at http://localhost:8000")
                print(f"   Error: {e}")
                print("   Please ensure the server is running with: python main.py")
                return
        
        print("✅ Server connection verified")
        print("🚀 Starting comprehensive API tests...\n")
        
        # Run the comprehensive test suite
        results = await run_comprehensive_test()
        
        # Print final report
        print_footer(results, start_time)
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())