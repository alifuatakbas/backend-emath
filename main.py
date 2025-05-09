from fastapi import FastAPI, HTTPException
from app.routers import auth, exams, admin_exams
from database import engine, Base, SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.services.schedular import init_scheduler, shutdown_scheduler, auto_complete_exams
import os
from datetime import datetime
from app.models.exam import Exam
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db

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
        scheduler = init_scheduler()  # Tek çağrı
        scheduler.add_job(
            auto_complete_exams,
            'interval',
            minutes=1,
            args=[SessionLocal()],
            id='auto_complete_exams'
        )
        print("Scheduler ve auto-complete job başarıyla başlatıldı")
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


@app.get("/exams/active", include_in_schema=True)
async def get_active_exams_public(
    db: Session = Depends(get_db)
):
    try:
        current_time = datetime.utcnow()
        exams = db.query(Exam).filter(
            Exam.exam_start_date > current_time
        ).all()

        exam_list = []
        for exam in exams:
            exam_data = {
                "id": exam.id,
                "title": exam.title,
                "registration_start_date": exam.registration_start_date,
                "registration_end_date": exam.registration_end_date,
                "exam_start_date": exam.exam_start_date,
                "exam_end_date": exam.exam_end_date,
                "status": exam.status
            }
            exam_list.append(exam_data)

        return exam_list
    except Exception as e:
        print(f"Error in get_active_exams: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))