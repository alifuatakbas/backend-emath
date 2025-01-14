from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from dotenv import load_dotenv
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_FROM=os.getenv('MAIL_FROM'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', '587')),
    MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_FROM_NAME=os.getenv('MAIL_FROM_NAME', 'System'),
    MAIL_SSL_TLS=False,  # Değişti
    MAIL_STARTTLS=True,  # Yeni eklendi
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


async def send_reset_email(email: EmailStr, token: str):
    reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password?token={token}"

    message = MessageSchema(
        subject="Şifre Sıfırlama",
        recipients=[email],
        body=f"""
        Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:
        {reset_link}

        Bu link 30 dakika süreyle geçerlidir.
        """,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)