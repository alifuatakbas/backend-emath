from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# MySQL Bağlantısı: Burada kendi MySQL bağlantı bilgilerinizi girmelisiniz
SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://kullanici_adiniz:sifreniz@localhost/db_adiniz"

# SQLAlchemy motorunu oluşturuyoruz
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=10, max_overflow=20)

# SessionLocal, veritabanı ile bağlantı kuracak oturumlarımızı yaratmak için kullanılır
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Veritabanı modelimiz için temel sınıf
Base = declarative_base()

def get_db():
    db = SessionLocal()  # Veritabanı oturumu
    try:
        yield db
    finally:
        db.close()  # Oturum bitiminde kapanır
