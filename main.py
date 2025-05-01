from fastapi import FastAPI, HTTPException
from app.routers import auth, exams, admin_exams
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.services.schedular import init_scheduler, shutdown_scheduler
import os

try:
    Base.metadata.create_all(bind=engine)  # MySQL'e bağlanarak tabloları oluşturur
except Exception as e:
    print(f"Database error: {e}")

port = int(os.getenv("PORT", 8080))

app = FastAPI()

# Uygulama başlatıldığında scheduler'ı başlat
@app.on_event("startup")
async def startup_event():
    try:
        init_scheduler()
        print("Scheduler başarıyla başlatıldı")
    except Exception as e:
        print(f"Scheduler başlatılırken hata oluştu: {e}")

# Uygulama kapatıldığında scheduler'ı durdur
@app.on_event("shutdown")
async def shutdown_event():
    try:
        shutdown_scheduler()
        print("Scheduler başarıyla durduruldu")
    except Exception as e:
        print(f"Scheduler durdurulurken hata oluştu: {e}")

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