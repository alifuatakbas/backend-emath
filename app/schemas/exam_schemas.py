from pydantic import BaseModel
from typing import List

class QuestionAnswerSubmission(BaseModel):
    question_id: int
    selected_option_id: int

class ExamSubmission(BaseModel):
    answers: List[QuestionAnswerSubmission]

class ExamResultResponse(BaseModel):
    correct_answers: int
    incorrect_answers: int
    total_questions: int
    score_percentage: float

    class Config:
        from_attributes = True

class ExamCreateRequest(BaseModel):
    title: str

class QuestionSCH(BaseModel):
    id: int
    text: str
    options: List[str]

class ExamSCH(BaseModel):
    id: int
    title: str
    is_published: bool
    questions: List[QuestionSCH]  # Sınavın soruları

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    text: str
    options: list[str]
    correct_option_index: int