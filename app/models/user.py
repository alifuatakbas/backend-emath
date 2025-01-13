from sqlalchemy import Column, Integer, String
from database import Base
from sqlalchemy.orm import relationship

# SQLAlchemy Model
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)  # 100 karakter uzunluğunda
    email = Column(String(100), unique=True, index=True)  # 100 karakter uzunluğunda
    full_name = Column(String(100))  # 100 karakter uzunluğunda
    hashed_password = Column(String(100))  # 100 karakter uzunluğunda
    role = Column(String(50), default="student")  # 50 karakter uzunluğunda

    exam_results = relationship("ExamResult", back_populates="user")
