from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime,Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime,timedelta
import pytz

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

    # DateTime kolonlarını açıkça tanımlayalım
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserDB", back_populates="exam_results")
    exam = relationship("Exam", back_populates="exam_results")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Eğer start_time ve end_time timezone içermiyorsa, UTC ekleyelim
        if self.start_time and self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=pytz.UTC)
        if self.end_time and self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=pytz.UTC)

