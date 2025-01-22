from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from dotenv import load_dotenv
import os
from pathlib import Path
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug için mevcut dizini yazdır
current_dir = Path(__file__).parent.parent.parent
logger.info(f"Current directory: {current_dir}")

# .env dosyasının tam yolunu belirt
env_path = current_dir / '.env'
logger.info(f"Looking for .env at: {env_path}")
logger.info(f"Env file exists: {env_path.exists()}")

# .env dosyasını yükle
load_dotenv(dotenv_path=env_path)

# Environment değişkenlerini kontrol et
mail_conf = {
    'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', 'akbasalifuat@gmail.com'),
    'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', 'dbbomqqmapxzriwa'),
    'MAIL_FROM': os.environ.get('MAIL_FROM', 'akbasalifuat@gmail.com'),
    'MAIL_PORT': int(os.environ.get('MAIL_PORT', '587')),
    'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    'MAIL_FROM_NAME': os.environ.get('MAIL_FROM_NAME', 'ExamSystem')
}


# ConnectionConfig'i oluştur
try:
    email_conf = ConnectionConfig(
        MAIL_USERNAME=mail_conf['MAIL_USERNAME'],
        MAIL_PASSWORD=mail_conf['MAIL_PASSWORD'],
        MAIL_FROM=mail_conf['MAIL_FROM'],
        MAIL_PORT=mail_conf['MAIL_PORT'],
        MAIL_SERVER=mail_conf['MAIL_SERVER'],
        MAIL_FROM_NAME=mail_conf['MAIL_FROM_NAME'],
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    logger.info("Email configuration created successfully")
except Exception as e:
    logger.error(f"Error creating email configuration: {str(e)}")
    raise

FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://e-math-frontend.vercel.app')
logger.info(f"Frontend URL: {FRONTEND_URL}")

async def send_reset_email(email: EmailStr, token: str):
    try:
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
        logger.info(f"Sending reset email to: {email}")
        logger.info(f"Reset link: {reset_link}")

        message = MessageSchema(
            subject="Şifre Sıfırlama",
            recipients=[email],
            body=f"""
            <html>
                <body>
                    <h2>Şifre Sıfırlama İsteği</h2>
                    <p>Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:</p>
                    <p><a href="{reset_link}">Şifremi Sıfırla</a></p>
                    <p>Bu link 30 dakika süreyle geçerlidir.</p>
                </body>
            </html>
            """,
            subtype="html"
        )

        fm = FastMail(email_conf)
        await fm.send_message(message)
        logger.info(f"Reset email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Error sending reset email to {email}: {str(e)}")
        raise  # Hatayı yukarı fırlat