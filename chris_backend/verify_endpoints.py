#!/usr/bin/env python3
"""
Endpoint verification script for CHRIS Backend API.
Verifies all expected endpoints are correctly registered.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def verify_endpoints():
    """Verify all expected endpoints are registered."""
    try:
        from src.api.main import app
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        print("Make sure dependencies are installed: pip install -r requirements.txt")
        return 1
    
    print("=== CHRIS Backend API - Endpoint Verification ===\n")
    
    expected_endpoints = {
        "/health": ["GET"],
        "/": ["GET"],
        "/api/v1/forecast/": ["POST"],
        "/api/v1/map/sponge-zones": ["GET"],
        "/api/v1/map/sponge-zones/{zone_id}/details": ["GET"],
        "/api/v1/citywide-risk": ["GET"],
    }
    
    # Get all routes
    routes = {}
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            path = route.path
            methods = list(route.methods)
            routes[path] = methods
    
    print("Registered Routes:")
    print("-" * 60)
    for path, methods in sorted(routes.items()):
        print(f"{', '.join(sorted(methods)):10} {path}")
    
    print("\n" + "=" * 60)
    print("Verification:")
    print("-" * 60)
    
    all_good = True
    for path, expected_methods in expected_endpoints.items():
        if path in routes:
            actual_methods = set(routes[path])
            expected_set = set(expected_methods)
            
            if expected_set.issubset(actual_methods):
                print(f"✅ {path}")
            else:
                print(f"⚠️  {path}")
                print(f"   Expected: {', '.join(expected_methods)}")
                print(f"   Found: {', '.join(actual_methods)}")
                all_good = False
        else:
            print(f"❌ {path} - NOT FOUND")
            all_good = False
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("✅ All endpoints verified!")
        print("\nEndpoints ready for frontend:")
        print("  - Health: GET /health")
        print("  - Forecast: POST /api/v1/forecast/ (protected)")
        print("  - Zones: GET /api/v1/map/sponge-zones")
        print("  - Zone Details: GET /api/v1/map/sponge-zones/{zone_id}/details")
        print("  - Citywide Risk: GET /api/v1/citywide-risk")
        
        cors_origins = os.getenv("ALLOWED_ORIGINS", "Not configured")
        print(f"\nCORS: {cors_origins}")
        
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "Not set")
        jwt_ok = jwt_secret and jwt_secret != "REQUIRED_FOR_JWT_VERIFICATION_GET_FROM_SUPABASE_DASHBOARD_SETTINGS_API"
        print(f"JWT Auth: {'✅ Configured' if jwt_ok else '❌ Not configured'}")
        
        return 0
    else:
        print("❌ Some endpoints are missing!")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(verify_endpoints())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
