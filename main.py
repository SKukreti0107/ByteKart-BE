from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db

from routers import public, users, orders, returns, support, redeem_codes, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

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
