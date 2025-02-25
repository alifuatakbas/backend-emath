import os
from fastapi.security import  OAuth2PasswordRequestForm
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
from app.services.email import send_reset_email, send_verification_email
from jose import jwt, JWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pathlib import Path


current_dir = Path(__file__).parent.absolute()
env_path = current_dir.parent.parent / '.env'
print(f"Looking for .env at: {env_path}")
print(f"File exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path)  # env_path'i tanımladıktan hemen sonra yükleyin

router = APIRouter()
SECRET_KEY = os.getenv('SECRET_KEY')


@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Email kontrolü
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Şifre hash'leme
    hashed_password = get_password_hash(user.password)

    # Verification token oluşturma
    verification_token = create_access_token(
        data={"sub": user.email}  # expires_delta parametresini kaldırdık
    )

    # Yeni kullanıcı oluşturma
    db_user = UserDB(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        school_name=user.school_name,
        branch=user.branch,
        verification_token=verification_token,
        is_verified=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Doğrulama emaili gönderme
    await send_verification_email(user.email, verification_token)

    return {"message": "Kayıt başarılı. Lütfen email adresinizi doğrulayın"}
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Lütfen email adresinizi doğrulayın")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=None)  # response_model'i kaldırıyoruz
async def read_users_me(current_user: UserDB = Depends(get_current_user)):  # User yerine UserDB kullanıyoruz
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "school_name": current_user.school_name,
        "branch": current_user.branch
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


# app/routers/auth.py

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        # Token'ı decode et (diğer endpointlerdeki gibi doğrudan SECRET_KEY kullan)
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")

        # Kullanıcıyı bul
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı"
            )

        # Kullanıcı zaten doğrulanmış mı kontrol et
        if user.is_verified:
            return {"message": "Email adresi zaten doğrulanmış"}

        # Kullanıcıyı doğrulanmış olarak işaretle
        user.is_verified = True
        user.verification_token = None  # Token'ı temizle
        db.commit()

        return {"message": "Email adresi başarıyla doğrulandı"}

    except JWTError:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz veya süresi dolmuş token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Doğrulama işlemi sırasında bir hata oluştu"
        )

# conf tanımlamasından önce ekleyin
mail_settings = {
    'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', 'akbasalifuat@gmail.com'),
    'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', 'dbbomqqmapxzriwa'),
    'MAIL_FROM': os.environ.get('MAIL_FROM', 'akbasalifuat@gmail.com'),
    'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    'ADMIN_EMAIL': os.environ.get('ADMIN_EMAIL', 'huseyin.yildiz@eolimpiyat.com')
}

# Email konfigürasyonu
conf = ConnectionConfig(
    MAIL_USERNAME=mail_settings['MAIL_USERNAME'],
    MAIL_PASSWORD=mail_settings['MAIL_PASSWORD'],
    MAIL_FROM=mail_settings['MAIL_FROM'],
    MAIL_PORT=int(os.environ.get('MAIL_PORT', '587')),
    MAIL_SERVER=mail_settings['MAIL_SERVER'],
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

ADMIN_EMAILS = [mail_settings['ADMIN_EMAIL']]

@router.post("/applications")
async def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db)
):
    try:
        # Veritabanına kaydet
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

        # Email içeriğini hazırla
        html_content = f"""
        <h2>Yeni Başvuru Alındı</h2>
        <p><strong>Ad Soyad:</strong> {application.fullName}</p>
        <p><strong>Email:</strong> {application.email}</p>
        <p><strong>Telefon:</strong> {application.phone}</p>
        <p><strong>Okul:</strong> {application.school}</p>
        <p><strong>Sınıf:</strong> {application.grade}</p>
        <p><strong>Mesaj:</strong> {application.message}</p>
        <p><em>Bu email otomatik olarak gönderilmiştir.</em></p>
        """

        # Admin bildirimi gönder
        message = MessageSchema(
            subject="Yeni Başvuru Bildirimi - E-Olimpiyat",
            recipients=ADMIN_EMAILS,
            body=html_content,
            subtype="html"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

        # Başvuru sahibine teşekkür maili gönder
        thank_you_content = f"""
        <h2>Başvurunuz Alındı</h2>
        <p>Sayın {application.fullName},</p>
        <p>E-Olimpiyat'a yaptığınız başvuru başarıyla alınmıştır. 
        En kısa sürede sizinle iletişime geçeceğiz.</p>
        <br>
        <p>Başvuru bilgileriniz:</p>
        <ul>
            <li>Ad Soyad: {application.fullName}</li>
            <li>Email: {application.email}</li>
            <li>Okul: {application.school}</li>
            <li>Sınıf: {application.grade}</li>
        </ul>
        <br>
        <p>Saygılarımızla,<br>E-Olimpiyat Ekibi</p>
        """

        thank_you_message = MessageSchema(
            subject="Başvurunuz Alındı - E-Olimpiyat",
            recipients=[application.email],
            body=thank_you_content,
            subtype="html"
        )

        await fm.send_message(thank_you_message)

        return {"message": "Başvuru başarıyla alındı"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Başvuru işlemi sırasında bir hata oluştu: {str(e)}"
        )