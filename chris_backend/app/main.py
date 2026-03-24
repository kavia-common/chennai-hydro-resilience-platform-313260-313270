from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, model_info, predict

app = FastAPI(
    title="CHRIS Backend API",
    version="0.1.0",
    description="CHRIS (Chennai Hydro-Resilience Intelligence System) backend APIs for ML inference.",
)

# In production, restrict origins. For now, allow local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(model_info.router)
app.include_router(predict.router)
