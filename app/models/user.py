from sqlalchemy import Column, Integer, String,Text,DateTime
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

# SQLAlchemy Model
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(100))
    role = Column(String(50), default="student")
    school_name = Column(String(100), nullable=True)  # Yeni eklenen
    branch = Column(String(50), nullable=True)        # Yeni eklenen

    exam_results = relationship("ExamResult", back_populates="user")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    school = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)