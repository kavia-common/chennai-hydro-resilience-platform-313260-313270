#!/usr/bin/env python3
"""
Backend Startup Verification Script

Verifies that the CHRIS backend is properly configured and can start successfully.
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text:^60}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def print_success(text):
    print(f"{GREEN}✓{NC} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{NC} {text}")

def print_error(text):
    print(f"{RED}✗{NC} {text}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("Environment Configuration Check")
    
    if not Path('.env').exists():
        print_error(".env file not found")
        return False
    
    print_success(".env file exists")
    
    # Load and check required variables
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'BACKEND_URL',
        'FRONTEND_URL',
        'ALLOWED_ORIGINS'
    ]
    
    missing_vars = []
    with open('.env', 'r') as f:
        env_content = f.read()
        for var in required_vars:
            if f"{var}=" not in env_content:
                missing_vars.append(var)
            else:
                # Extract value
                for line in env_content.split('\n'):
                    if line.startswith(f"{var}="):
                        value = line.split('=', 1)[1].strip()
                        if value:
                            print_success(f"{var} is set")
                        else:
                            print_warning(f"{var} is empty")
    
    if missing_vars:
        print_warning(f"Missing variables: {', '.join(missing_vars)}")
        return False
    
    return True

def check_dependencies():
    """Check if Python dependencies are installed"""
    print_header("Dependencies Check")
    
    try:
        import fastapi
        print_success(f"FastAPI installed (version {fastapi.__version__})")
    except ImportError:
        print_error("FastAPI not installed")
        return False
    
    try:
        import uvicorn
        print_success(f"Uvicorn installed (version {uvicorn.__version__})")
    except ImportError:
        print_error("Uvicorn not installed")
        return False
    
    try:
        import supabase
        print_success("Supabase client installed")
    except ImportError:
        print_error("Supabase client not installed")
        return False
    
    return True

def check_source_structure():
    """Check if source code structure is correct"""
    print_header("Source Code Structure Check")
    
    required_paths = [
        'src/api/main.py',
        'src/api/routes/forecast.py',
        'src/api/routes/zones.py',
        'src/api/routes/citywide.py',
        'src/middleware/auth.py',
        'src/middleware/rate_limit.py',
        'src/utils/supabase_client.py',
        'src/schemas/forecast.py',
        'src/schemas/zone.py',
        'src/schemas/citywide.py'
    ]
    
    all_exist = True
    for path in required_paths:
        if Path(path).exists():
            print_success(f"{path} exists")
        else:
            print_error(f"{path} missing")
            all_exist = False
    
    return all_exist

def test_import():
    """Test if main application can be imported"""
    print_header("Import Test")
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, '.')
        from src.api.main import app
        print_success("Main application imports successfully")
        print_success(f"App title: {app.title}")
        print_success(f"App version: {app.version}")
        return True
    except Exception as e:
        print_error(f"Failed to import application: {e}")
        return False

def check_routes():
    """Check if all required routes are registered"""
    print_header("Routes Check")
    
    try:
        sys.path.insert(0, '.')
        from src.api.main import app
        
        required_routes = [
            ('GET', '/health'),
            ('GET', '/'),
            ('POST', '/api/v1/forecast/'),
            ('GET', '/api/v1/map/sponge-zones'),
            ('GET', '/api/v1/map/sponge-zones/{zone_id}/details'),
            ('GET', '/api/v1/citywide-risk')
        ]
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    routes.append((method, route.path))
        
        all_found = True
        for method, path in required_routes:
            found = any(r[0] == method and r[1] == path for r in routes)
            if found:
                print_success(f"{method} {path}")
            else:
                print_error(f"{method} {path} - NOT FOUND")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"Failed to check routes: {e}")
        return False

def main():
    """Run all verification checks"""
    print_header("CHRIS Backend Startup Verification")
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("Dependencies", check_dependencies),
        ("Source Structure", check_source_structure),
        ("Import", test_import),
        ("Routes", check_routes)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Check '{name}' failed with exception: {e}")
            results[name] = False
    
    # Summary
    print_header("Verification Summary")
    
    all_passed = True
    for name, passed in results.items():
        if passed:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            all_passed = False
    
    print()
    if all_passed:
        print_success("All checks passed! Backend is ready to start.")
        print()
        print(f"{BLUE}To start the backend, run:{NC}")
        print(f"  ./start.sh")
        print()
        print(f"{BLUE}Or manually:{NC}")
        print(f"  python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload")
        print()
        return 0
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print()
        print(f"{YELLOW}Common fixes:{NC}")
        print(f"  1. Install dependencies: pip install -r requirements.txt")
        print(f"  2. Verify .env file exists and has correct values")
        print(f"  3. Check file permissions")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
