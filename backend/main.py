"""
Supply Chain Decision Engine — FastAPI entry point.
Run: uvicorn main:app --reload --port 8000
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before anything else so GEMINI_API_KEY is available
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from api.dead_stock import router as dead_stock_router
from api.supplier import router as supplier_router
from api.demand import router as demand_router
from api.queue import router as queue_router
from api.explain import router as explain_router
from api.sku import router as sku_router
from api.decisions import router as decisions_router
from api.forecast import router as forecast_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="Supply Chain Decision Engine",
    description="Dead stock detection, supplier reliability, demand trends, scenario simulation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dead_stock_router)
app.include_router(supplier_router)
app.include_router(demand_router)
app.include_router(queue_router)
app.include_router(explain_router)
app.include_router(sku_router)
app.include_router(decisions_router)
app.include_router(forecast_router)


@app.get("/health")
def health():
    return {"status": "ok"}
