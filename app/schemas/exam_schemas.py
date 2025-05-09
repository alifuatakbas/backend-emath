from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime

class ExamStatus(str, Enum):
    UNPUBLISHED = "unpublished"
    REGISTRATION_PENDING = "registration_pending"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    EXAM_ACTIVE = "exam_active"
    COMPLETED = "completed"

class ExamListResponse(BaseModel):
    id: int
    title: str
    registration_start_date: datetime
    registration_end_date: datetime
    exam_start_date: datetime
    exam_end_date: datetime
    can_register: bool
    status: str
    is_registered: bool
    registration_status: str

    class Config:
        from_attributes = True

class QuestionAnswerSubmission(BaseModel):
    question_id: int
    selected_option_id: int

class ExamSubmission(BaseModel):
    answers: List[QuestionAnswerSubmission]


class QuestionResultDetail(BaseModel):
    question_text: str
    question_image: Optional[str] = None
    options: List[str]
    correct_option: int
    student_answer: Optional[int]
    is_correct: bool


class ExamResultResponse(BaseModel):
    correct_answers: int
    incorrect_answers: int
    total_questions: int
    score_percentage: float
    questions: List[QuestionResultDetail]  # Yeni eklenen alan

    class Config:
        from_attributes = True

class ExamCreateRequest(BaseModel):
    title: str
    registration_start_date: datetime
    registration_end_date: datetime
    exam_start_date: datetime
    exam_end_date: Optional[datetime] = None
    duration_minutes: int  # Yeni eklenen alan

class QuestionSCH(BaseModel):
    id: int
    text: str
    options: List[str]
    image: str | None = None

class ExamSCH(BaseModel):
    id: int
    title: str
    is_published: bool
    registration_start_date: datetime
    registration_end_date: datetime
    exam_start_date: datetime
    exam_end_date: Optional[datetime] = None
    questions: List[QuestionSCH]

    class Config:
        from_attributes = True


class ExamWithResult(BaseModel):
    id: int
    title: str
    has_been_taken: bool = True
    correct_answers: Optional[int] = None
    incorrect_answers: Optional[int] = None
    score_percentage: Optional[float] = None
    completion_date: Optional[datetime] = None

    class Config:
        from_attributes = True

