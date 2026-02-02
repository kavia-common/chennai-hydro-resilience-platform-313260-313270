#!/usr/bin/env python3
"""
Backend Verification Script

Tests that the CHRIS backend is running and all endpoints are accessible.
"""
import requests
import sys
import time
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://localhost:3001"
TIMEOUT = 5


def test_endpoint(method: str, endpoint: str, description: str) -> Tuple[bool, str]:
    """
    Test a single endpoint.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Endpoint path
        description: Test description
        
    Returns:
        Tuple of (success, message)
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        else:
            response = requests.request(method, url, timeout=TIMEOUT)
        
        if response.status_code < 400:
            return True, f"✅ {description}: {response.status_code}"
        else:
            return False, f"❌ {description}: {response.status_code} - {response.text[:100]}"
    except requests.exceptions.ConnectionError:
        return False, f"❌ {description}: Connection refused - is the backend running?"
    except requests.exceptions.Timeout:
        return False, f"❌ {description}: Request timeout"
    except Exception as e:
        return False, f"❌ {description}: {str(e)}"


def main():
    """Run all endpoint tests."""
    print("=" * 80)
    print("CHRIS Backend Verification")
    print("=" * 80)
    print(f"\nTesting backend at: {BASE_URL}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Define tests
    tests: List[Tuple[str, str, str]] = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check endpoint"),
        ("GET", "/docs", "OpenAPI documentation"),
        ("GET", "/openapi.json", "OpenAPI JSON spec"),
        ("GET", "/api/v1/map/sponge-zones", "Get sponge zones (list)"),
        ("GET", "/api/v1/map/sponge-zones/Z001/details", "Get zone details (specific zone)"),
        ("GET", "/api/v1/citywide-risk", "Get citywide risk data"),
    ]
    
    results: List[Tuple[bool, str]] = []
    
    # Run tests
    for method, endpoint, description in tests:
        success, message = test_endpoint(method, endpoint, description)
        results.append((success, message))
        print(message)
    
    # Summary
    print("\n" + "=" * 80)
    total = len(results)
    passed = sum(1 for success, _ in results if success)
    failed = total - passed
    
    print(f"Summary: {passed}/{total} tests passed")
    
    if failed > 0:
        print(f"\n⚠️  {failed} test(s) failed")
        print("\nCommon issues:")
        print("  - Backend not running: Run './start.sh' in chris_backend directory")
        print("  - Port conflict: Check if port 3001 is already in use")
        print("  - Database not configured: Check SUPABASE_URL and SUPABASE_KEY in .env")
        print("  - Missing data: Ensure zone_risk table has sample data")
        return 1
    else:
        print("\n✅ All tests passed! Backend is running correctly.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```
