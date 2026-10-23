from fastapi import FastAPI

from app.routes import router
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_ORIGINS

app = FastAPI(title="CAM Salary API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

app.include_router(router)
