from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import api_router

app = FastAPI(
    title="PromoStudio API",
    description="Backend API for PromoStudio - AI-powered promo generation tool",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "PromoStudio API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
