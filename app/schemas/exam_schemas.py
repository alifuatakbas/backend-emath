from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class QuestionAnswer(BaseModel):
    question_id: int
    selected_option_id: int

class ExamSubmission(BaseModel):
    answers: List[QuestionAnswer]

class ExamResultResponse(BaseModel):
    correct_answers: int
    incorrect_answers: int
    total_questions: int
    score_percentage: float

class ExamCreateRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int = 90

class QuestionSCH(BaseModel):
    id: int
    text: str
    options: List[str]

class ExamSCH(BaseModel):
    id: int
    title: str
    is_published: bool
    questions: List[QuestionSCH]

class ExamTimeInfo(BaseModel):
    remaining_minutes: int
    can_start: bool
    message: str