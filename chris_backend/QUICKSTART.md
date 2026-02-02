# CHRIS Backend - Quick Start Guide

## Prerequisites

- Python 3.12+
- pip (Python package manager)
- Supabase account (for database)

## Setup (First Time)

1. **Navigate to backend directory**
   ```bash
   cd chennai-hydro-resilience-platform-313260-313270/chris_backend
   ```

2. **Create virtual environment** (if not exists)
   ```bash
   python3 -m venv venv
   ```

3. **Install dependencies**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env.example` to `.env` (already done)
   - Update Supabase credentials if needed
   ```bash
   # .env file should have:
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_JWT_SECRET=your_jwt_secret
   ```

## Running the Backend

### Quick Start (Recommended)

The easiest way to start the backend is using the `start.sh` script:

```bash
./start.sh
```

The server will start on `http://0.0.0.0:3001` with hot reload enabled.

### Start Script Options

```bash
# Show help and all available options
./start.sh --help

# Start on a custom port
./start.sh --port 3101

# Start on a different host
./start.sh --host 127.0.0.1

# Disable auto-reload (for production-like testing)
./start.sh --no-reload

# Enable debug logging
./start.sh --log-level debug

# Production mode with multiple workers (disables reload)
./start.sh --workers 4 --no-reload

# Combine options
./start.sh --port 8080 --log-level debug
```

### Accessing the Server

**Local development:**
- API Documentation: `http://localhost:3001/docs`
- Health Check: `http://localhost:3001/health`
- OpenAPI Spec: `http://localhost:3001/openapi.json`

**Via proxy (in dev environment):**
- Access via: `/proxy/3001/` (or `/proxy/<PORT>/` if using custom port)
- Example: `/proxy/3001/docs`

### Manual Start (Alternative)

If you prefer to start uvicorn manually:

```bash
source venv/bin/activate
export PYTHONPATH=.
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

## Verify It's Working

### Option 1: Health Check
```bash
curl http://localhost:3001/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "..."}
```

### Option 2: Run Verification Script
```bash
python3 verify_backend.py
```

### Option 3: Browser
Open: `http://localhost:3001/docs` (Interactive API documentation)

## Common Commands

### Check if backend is running
```bash
lsof -i :3001
```

### Stop the backend
```bash
# If running in foreground, press Ctrl+C

# If running in background
pkill -f "uvicorn src.api.main:app"

# Or kill specific port
kill -9 $(lsof -t -i:3001)
```

### View logs (if running in background)
```bash
tail -f backend.log
```

### Test endpoints
```bash
# Get all zones
curl http://localhost:3001/api/v1/map/sponge-zones

# Get specific zone
curl http://localhost:3001/api/v1/map/sponge-zones/Z001/details

# Citywide risk stats
curl http://localhost:3001/api/v1/citywide-risk

# Health check
curl http://localhost:3001/health
```

## Development

### Hot Reload
The backend automatically reloads when you change `.py` files in the `src/` directory (when using `./start.sh` or `--reload` flag).

### Run Tests
```bash
source venv/bin/activate
pytest
```

### Run Tests with Coverage
```bash
source venv/bin/activate
pytest --cov=src --cov-report=html
```

### Quick Test Script
```bash
./run_tests.sh
```

### Linting
```bash
source venv/bin/activate
flake8 src/
```

## Key Endpoints for Frontend

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/health` | GET | Health check | No |
| `/api/v1/map/sponge-zones` | GET | Get all zones (GeoJSON) | No |
| `/api/v1/map/sponge-zones/{zone_id}/details` | GET | Get zone details | No |
| `/api/v1/citywide-risk` | GET | Citywide risk stats | No |
| `/api/v1/forecast/` | POST | Flood forecast | JWT Required |
| `/docs` | GET | Interactive API docs | No |
| `/openapi.json` | GET | OpenAPI specification | No |

## Environment Variables

### Essential Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `UVICORN_HOST` | 0.0.0.0 | Server host |
| `PORT` | 3001 | Server port |
| `PYTHONPATH` | . | Python module path |
| `SUPABASE_URL` | (required) | Supabase project URL |
| `SUPABASE_KEY` | (required) | Supabase anon key |
| `SUPABASE_JWT_SECRET` | (required) | JWT secret for auth |

### Optional Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | development | Environment mode |
| `LOG_LEVEL` | info | Logging level |
| `ALLOWED_ORIGINS` | localhost:3000,... | CORS allowed origins |
| `RATE_LIMIT_MAX` | 100 | Max requests per window |
| `RATE_LIMIT_WINDOW_S` | 60 | Rate limit window (seconds) |
| `UVICORN_WORKERS` | 1 | Number of worker processes |

### Setting Environment Variables

The `start.sh` script automatically:
1. Loads variables from `.env` if present
2. Applies sensible defaults for missing variables
3. Ensures `ALLOWED_ORIGINS` includes `http://localhost:3000`
4. Sets `PYTHONPATH=.` for correct module resolution

You can also override via CLI:
```bash
./start.sh --port 8080 --log-level debug
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 3001
lsof -i :3001

# Kill it
kill -9 $(lsof -t -i:3001)

# Or use a different port
./start.sh --port 3101
```

### Module not found errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# Ensure PYTHONPATH is set (start.sh does this automatically)
export PYTHONPATH=.
```

### Database connection errors
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check Supabase project status in dashboard
- Ensure tables exist: `zone_risk`, `forecast_predictions`, etc.
- Run with debug logging: `./start.sh --log-level debug`

### CORS errors from frontend
- Add frontend origin to `ALLOWED_ORIGINS` in `.env`
- The `start.sh` script automatically includes `http://localhost:3000`
- Restart backend after changing `.env`

### Import errors (ModuleNotFoundError)
```bash
# Verify you're in the correct directory
pwd
# Should show: .../chris_backend

# Check PYTHONPATH
echo $PYTHONPATH
# Should include current directory (.)

# start.sh sets this automatically
./start.sh
```

### Server won't start
Run with debug output to see detailed error messages:
```bash
./start.sh --log-level debug
```

Common causes:
1. **Port conflict**: Use `--port` to specify different port
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Environment issues**: Check `.env` file exists and has valid values
4. **Python version**: Ensure Python 3.12+ is installed

### Getting help from start script
```bash
./start.sh --help
```

This shows all available options and troubleshooting hints.

## Development Workflow

### Typical Development Session

```bash
# 1. Start backend (with hot reload)
./start.sh

# 2. In another terminal, run tests on changes
pytest tests/

# 3. Check API docs in browser
open http://localhost:3001/docs

# 4. Test specific endpoint
curl http://localhost:3001/api/v1/citywide-risk

# 5. View logs (if needed)
# Logs appear in the terminal where you ran ./start.sh
```

### Production-like Testing

```bash
# Test with multiple workers (no reload)
./start.sh --workers 4 --no-reload

# Or set production environment
NODE_ENV=production ./start.sh --workers 4
```

## Documentation

- **Full Endpoint Reference**: `ENDPOINT_REFERENCE.md`
- **Backend Status**: `BACKEND_READY.md`
- **Security Guide**: `SECURITY.md`
- **Testing Guide**: `TESTING_QUICKSTART.md`
- **API Docs (Live)**: http://localhost:3001/docs
- **OpenAPI Spec**: http://localhost:3001/openapi.json

## Support

For issues or questions:
1. Check `BACKEND_READY.md` for current status
2. Review `ENDPOINT_REFERENCE.md` for API details
3. Run `python3 verify_backend.py` to test all endpoints
4. Start with debug logging: `./start.sh --log-level debug`
5. Check the troubleshooting section above

## Quick Reference Card

```bash
# Start server
./start.sh                      # Default (port 3001, hot reload)
./start.sh --port 8080          # Custom port
./start.sh --log-level debug    # Debug mode
./start.sh --workers 4          # Production mode

# Access
http://localhost:3001/docs      # API documentation
http://localhost:3001/health    # Health check
/proxy/3001/                    # Via proxy (dev env)

# Stop
Ctrl+C                          # Foreground
pkill -f "uvicorn src.api"      # Background

# Test
curl http://localhost:3001/health
python3 verify_backend.py
pytest

# Help
./start.sh --help
```
