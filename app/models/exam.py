# models/exam.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    is_published = Column(Boolean, default=False)
    start_time = Column(DateTime, nullable=True)  # Sınavın başlama zamanı
    end_time = Column(DateTime, nullable=True)    # Sınavın giriş bitiş zamanı
    duration_minutes = Column(Integer, default=90) # Sınav süresi (dakika)

    questions = relationship("Question", back_populates="exam")
    exam_results = relationship("ExamResult", back_populates="exam")
    question_counter = Column(Integer, default=0)

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    text = Column(String, nullable=False)
    image = Column(String, nullable=True)
    question_id = Column(Integer)  # Her sınav için sıralı soru numarası

    option_1 = Column(String, default="A")
    option_2 = Column(String, default="B")
    option_3 = Column(String, default="C")
    option_4 = Column(String, default="D")
    option_5 = Column(String, default="E")

    correct_option_id = Column(Integer, nullable=False)

    exam = relationship("Exam", back_populates="questions")

class ExamResult(Base):
    __tablename__ = "exam_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exam_id = Column(Integer, ForeignKey("exams.id"))
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)  # Öğrencinin sınava başlama zamanı
    ends_at = Column(DateTime, nullable=True)     # Öğrencinin sınav bitiş zamanı

    user = relationship("UserDB", back_populates="exam_results")
    exam = relationship("Exam", back_populates="exam_results")



