from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime  # datetime.datetime yerine datetime kullanmak daha temiz


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(100))
    role = Column(String(50), default="student")
    school_name = Column(String(100), nullable=True)
    branch = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False)
    parent_name = Column(String(100))  # Eklendi
    phone = Column(String(20))
    verification_token = Column(String(255), unique=True, nullable=True)

    exam_results = relationship("ExamResult", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"  # Debug için yararlı


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    school = Column(String(200))
    grade = Column(String(50))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)  # datetime.datetime.utcnow yerine datetime.utcnow

    def __repr__(self):
        return f"<Application {self.email}>"  # Debug için yararlı