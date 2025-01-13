from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    is_published = Column(Boolean, default=False)

    questions = relationship("Question", back_populates="exam")
    exam_results = relationship("ExamResult", back_populates="exam")

    question_counter = Column(Integer, default=0)  # Yeni eklenen soru sayısını tutmak için


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    text = Column(String, nullable=False)
    image = Column(String, nullable=True)

    # Seçeneklerin metinleri
    option_1 = Column(String, default="A")
    option_2 = Column(String, default="B")
    option_3 = Column(String, default="C")
    option_4 = Column(String, default="D")
    option_5 = Column(String, default="E")

    # Doğru cevabın ID'si
    correct_option_id = Column(Integer, nullable=False)  # 1, 2, 3, 4, 5

    exam = relationship("Exam", back_populates="questions")

class ExamResult(Base):
    __tablename__ = "exam_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exam_id = Column(Integer, ForeignKey("exams.id"))
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    started_at = Column(datetime, default=datetime.utcnow)
    ends_at = Column(datetime)

    user = relationship("UserDB", back_populates="exam_results")
    exam = relationship("Exam", back_populates="exam_results")