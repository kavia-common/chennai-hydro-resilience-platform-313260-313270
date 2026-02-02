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
   ```

## Running the Backend

### Simple Start
```bash
./start.sh
```

The backend will start on `http://0.0.0.0:3001`

### Manual Start (Alternative)
```bash
source venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

## Verify It's Working

### Option 1: Health Check
```bash
curl http://localhost:3001/health
```

### Option 2: Run Verification Script
```bash
python3 verify_backend.py
```

### Option 3: Browser
Open: http://localhost:3001/docs (Interactive API documentation)

## Common Commands

### Check if backend is running
```bash
lsof -i :3001
```

### Stop the backend
```bash
pkill -f "uvicorn src.api.main:app"
```

### View logs (if running in background)
```bash
tail -f backend.log
```

### Test an endpoint
```bash
# Get all zones
curl http://localhost:3001/api/v1/map/sponge-zones

# Get specific zone
curl http://localhost:3001/api/v1/map/sponge-zones/Z001/details

# Health check
curl http://localhost:3001/health
```

## Development

### Hot Reload
The backend automatically reloads when you change `.py` files in the `src/` directory.

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

### Linting
```bash
source venv/bin/activate
flake8 src/
```

## Key Endpoints for Frontend

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/map/sponge-zones` | GET | Get all zones (GeoJSON) |
| `/api/v1/map/sponge-zones/{zone_id}/details` | GET | Get zone details |
| `/api/v1/citywide-risk` | GET | Citywide risk stats |
| `/api/v1/forecast/` | POST | Flood forecast (requires JWT) |
| `/docs` | GET | Interactive API docs |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 3001 | Server port |
| `NODE_ENV` | development | Environment mode |
| `ALLOWED_ORIGINS` | localhost:3000,... | CORS allowed origins |
| `RATE_LIMIT_MAX` | 100 | Max requests per window |
| `RATE_LIMIT_WINDOW_S` | 60 | Rate limit window (seconds) |

## Troubleshooting

### Port already in use
```bash
# Find process using port 3001
lsof -i :3001

# Kill it
kill -9 <PID>
```

### Module not found errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### Database connection errors
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check Supabase project status in dashboard
- Ensure tables exist: `zone_risk`, `forecast_predictions`, etc.

### CORS errors from frontend
- Add frontend origin to `ALLOWED_ORIGINS` in `.env`
- Restart backend after changing `.env`

## Documentation

- **Full Endpoint Reference**: `ENDPOINT_REFERENCE.md`
- **Backend Status**: `BACKEND_READY.md`
- **Security Guide**: `SECURITY.md`
- **API Docs**: http://localhost:3001/docs
- **OpenAPI Spec**: http://localhost:3001/openapi.json

## Support

For issues or questions:
1. Check `BACKEND_READY.md` for status
2. Review `ENDPOINT_REFERENCE.md` for API details
3. Run `python3 verify_backend.py` to test all endpoints
4. Check logs: `tail -f backend.log`
```
