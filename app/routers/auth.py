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
from config import settings
# Logging ayarları
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Kullanımı:
logger.info("Bilgi mesajı")
logger.error("Hata mesajı")


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
        parent_name=user.parent_name,  # Eklendi
        phone=user.phone,  # Eklendi
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
    logger.info(f"Received forgot password request for email: {request.email}")

    # 1. Email formatını kontrol et
    if not request.email:
        logger.error("Email is empty")
        raise HTTPException(status_code=400, detail="Email adresi gerekli")

    # 2. Kullanıcıyı kontrol et
    user = db.query(UserDB).filter(UserDB.email == request.email).first()
    if not user:
        logger.warning(f"User not found: {request.email}")
        raise HTTPException(status_code=404, detail="Bu email ile kayıtlı kullanıcı bulunamadı")

    try:
        # 3. Token oluştur
        token_data = {
            "sub": user.email,
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        reset_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # 4. Email gönder
        await send_reset_email(user.email, reset_token)

        logger.info(f"Password reset email sent successfully to {user.email}")
        return {"message": "Şifre sıfırlama linki email adresinize gönderildi"}

    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Şifre sıfırlama işlemi sırasında bir hata oluştu"
        )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Şifre sıfırlama isteği başladı")

        try:
            payload = jwt.decode(request.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            if not email:
                logger.error("Token'da email bilgisi bulunamadı")
                raise HTTPException(status_code=400, detail="Geçersiz token formatı")

            logger.info(f"Token doğrulandı, email: {email}")

        except jwt.ExpiredSignatureError:
            logger.warning("Token süresi dolmuş")
            raise HTTPException(status_code=400, detail="Token süresi dolmuş")
        except jwt.JWTError as e:
            logger.error(f"Token doğrulama hatası: {str(e)}")
            raise HTTPException(status_code=400, detail="Geçersiz token")

        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            logger.warning(f"Kullanıcı bulunamadı: {email}")
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

        try:
            hashed_password = get_password_hash(request.new_password)
            user.hashed_password = hashed_password
            db.commit()
            logger.info(f"Şifre başarıyla güncellendi: {email}")
        except Exception as e:
            logger.error(f"Şifre güncelleme hatası: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Şifre güncellenirken bir hata oluştu")

        return {"message": "Şifreniz başarıyla güncellendi"}

    except HTTPException as he:
        # HTTP hatalarını olduğu gibi yükselt
        raise he
    except Exception as e:
        # Beklenmeyen hataları logla
        logger.error(f"Beklenmeyen hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Şifre sıfırlama işlemi sırasında bir hata oluştu"
        )


# app/routers/auth.py

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        # Token'ı decode et (settings'den SECRET_KEY ve ALGORITHM kullanarak)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=400,
                detail="Geçersiz token"
            )

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
        user.verification_token = None
        db.commit()

        return {"message": "Email adresi başarıyla doğrulandı"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Doğrulama linkinin süresi dolmuş"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz doğrulama linki"
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