from sqlalchemy import  Column, Integer, String
from database import Base
from sqlalchemy.orm import relationship

# SQLAlchemy Model
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="student")

    exam_results = relationship("ExamResult", back_populates="user")


