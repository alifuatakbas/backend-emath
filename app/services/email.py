from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
from dotenv import load_dotenv
import os
from pathlib import Path

# Debug için mevcut dizini yazdır
current_dir = Path(__file__).parent.parent.parent
print(f"Current directory: {current_dir}")

# .env dosyasının tam yolunu belirt
env_path = current_dir / '.env'
print(f"Looking for .env at: {env_path}")

# .env dosyasını yükle
load_dotenv(dotenv_path=env_path)

# Debug için environment değişkenlerini kontrol et
# Doğrudan değerleri kullan
email_conf = ConnectionConfig(
    MAIL_USERNAME="akbasalifuat@gmail.com",  # Doğrudan değer
    MAIL_PASSWORD="dbbomqqmapxzriwa",  # Doğrudan değer
    MAIL_FROM="akbasalifuat@gmail.com",  # Doğrudan değer
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="Exam System",
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://e-math-frontend.vercel.app')


async def send_reset_email(email: EmailStr, token: str):
    try:
        # Reset linkini deploy edilmiş adrese yönlendir
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

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
        return True
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        return False