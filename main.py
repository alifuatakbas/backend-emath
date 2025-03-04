from fastapi import FastAPI, HTTPException
from app.routers import auth, exams,admin_exams
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

try:
    Base.metadata.create_all(bind=engine)  # MySQL'e bağlanarak tabloları oluşturur
except Exception as e:
    print(f"Database error: {e}")

port = int(os.getenv("PORT", 8080))

app = FastAPI()


app.include_router(auth.router)
app.include_router(exams.router)

app.include_router(admin_exams.router)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.eolimpiyat.com",
        "https://eolimpiyat.com",
        "http://localhost:3000",
        "https://api.eolimpiyat.com"
    ],
    allow_origin_regex="https://.*\.eolimpiyat\.com",  # Alt domainler için
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

app.mount("/static", StaticFiles(directory="static"), name="static")


