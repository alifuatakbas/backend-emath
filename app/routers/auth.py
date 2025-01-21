from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import  OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models.user import UserDB, Application
from app.schemas.user import User, UserCreate, Token,ApplicationCreate
from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from database import get_db
import logging
from app.schemas.auth_schemas import ForgotPasswordRequest, ResetPasswordRequest
from app.services.email import send_reset_email
from jose import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"


router = APIRouter()
load_dotenv()

@router.post("/register", response_model=User)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    logging.info(f"Received user data: {user}")

    # Email kontrolü
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email adresi zaten kayıtlı")

    hashed_password = get_password_hash(user.password)
    db_user = UserDB(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        school_name=user.school_name,
        branch=user.branch
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=None)  # response_model'i kaldırıyoruz
async def read_users_me(current_user: UserDB = Depends(get_current_user)):  # User yerine UserDB kullanıyoruz
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role
    }



# Şifremi unuttum endpoint'i
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Bu email adresi ile kayıtlı kullanıcı bulunamadı"
        )

    # Reset token oluştur
    token_data = {
        "sub": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    # os.getenv yerine doğrudan SECRET_KEY kullan
    reset_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")

    # Email gönder
    await send_reset_email(user.email, reset_token)

    return {"message": "Şifre sıfırlama linki email adresinize gönderildi"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        # Token'ı doğrula (burada da SECRET_KEY'i doğrudan kullan)
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")

        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

        # Yeni şifreyi hashle ve kaydet
        hashed_password = get_password_hash(request.new_password)
        user.hashed_password = hashed_password
        db.commit()

        return {"message": "Şifreniz başarıyla güncellendi"}

    except jwt.JWTError:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz veya süresi dolmuş token"
        )


@router.post("/applications")
async def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db)
):
    db_application = Application(
        full_name=application.fullName,
        email=application.email,
        phone=application.phone,
        school=application.school,
        grade=application.grade,
        message=application.message
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return {"message": "Başvuru başarıyla alındı"}