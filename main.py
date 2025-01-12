from fastapi import FastAPI, HTTPException
from app.routers import auth, exams
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database error: {e}")
app = FastAPI()
app.include_router(auth.router)
app.include_router(exams.router)
# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
