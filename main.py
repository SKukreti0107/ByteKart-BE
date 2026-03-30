import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from db import init_db

from routers import public, users, orders, returns, support, redeem_codes, admin

# --- Production detection ---
_is_prod = os.getenv("ENVIRONMENT", "production") == "production"

# Configure logging level
logging.basicConfig(
    level=logging.WARNING if _is_prod else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# --- Request timeout middleware ---
class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=30.0)
        except asyncio.TimeoutError:
            return StarletteResponse(status_code=504, content="Request timeout")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

# Timeout Middleware (outermost — wraps everything)
app.add_middleware(TimeoutMiddleware)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://byte-kart.vercel.app",
        "http://localhost:5173",
        "https://www.bytekart.co.in",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/")
def read_root():
    return {"message": "Welcome to ByteKart API"}


# Include all routers
app.include_router(public.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(support.router)
app.include_router(redeem_codes.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

