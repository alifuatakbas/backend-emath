from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "gizli_anahtar_buraya"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
