from fastapi import FastAPI, HTTPException
from app.routers import auth, exams,admin_exams
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    Base.metadata.create_all(bind=engine)  # MySQL'e bağlanarak tabloları oluşturur
except Exception as e:
    print(f"Database error: {e}")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth.router)
app.include_router(exams.router)

app.include_router(admin_exams.router)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://e-math-frontend.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint

