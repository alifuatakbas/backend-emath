# routers/exam.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.schemas.exam_schemas import (
    ExamSubmission, ExamResultResponse, ExamCreateRequest,
    ExamSCH, QuestionSCH, ExamTimeInfo
)
from database import get_db
from app.models.exam import Exam, Question, ExamResult
from app.routers.auth import get_current_user
from app.models.user import UserDB

router = APIRouter()
User = UserDB


@router.post("/create-exam")
def create_exam(
        request: ExamCreateRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    exam = Exam(
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        duration_minutes=request.duration_minutes
    )
    db.add(exam)
    db.commit()
    return {"message": "Sınav oluşturuldu", "exam_id": exam.id}


@router.post("/add-question/{exam_id}")
def add_question(
        exam_id: int,
        text: str,
        options: list[str],
        correct_option_index: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    if len(options) != 5:
        raise HTTPException(status_code=400, detail="Her soru için 5 seçenek gereklidir")

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    question_number = exam.question_counter + 1
    exam.question_counter = question_number

    question = Question(exam_id=exam_id, text=text)
    question.option_1 = options[0]
    question.option_2 = options[1]
    question.option_3 = options[2]
    question.option_4 = options[3]
    question.option_5 = options[4]
    question.correct_option_id = correct_option_index
    question.question_id = question_number

    db.add(question)
    db.commit()

    return {"message": "Soru ve seçenekler eklendi", "question_id": question.question_id}


@router.get("/exam/{exam_id}/time-check", response_model=ExamTimeInfo)
async def check_exam_time(exam_id: int, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    existing_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    now = datetime.utcnow()

    if existing_result and existing_result.started_at:
        remaining_time = existing_result.ends_at - now
        remaining_minutes = int(remaining_time.total_seconds() / 60)

        if remaining_minutes <= 0:
            return ExamTimeInfo(
                remaining_minutes=0,
                can_start=False,
                message="Sınav süreniz doldu"
            )

        return ExamTimeInfo(
            remaining_minutes=remaining_minutes,
            can_start=True,
            message=f"Sınavınız devam ediyor. Kalan süre: {remaining_minutes} dakika"
        )

    if now < datetime.combine(exam.start_time, datetime.min.time()):
        return ExamTimeInfo(
            remaining_minutes=exam.duration_minutes,
            can_start=False,
            message="Sınav henüz başlamadı"
        )

    if now > datetime.combine(exam.end_time, datetime.min.time()):
        return ExamTimeInfo(
            remaining_minutes=0,
            can_start=False,
            message="Sınav giriş süresi sona erdi"
        )

    return ExamTimeInfo(
        remaining_minutes=exam.duration_minutes,
        can_start=True,
        message="Sınava başlayabilirsiniz"
    )


@router.post("/start-exam/{exam_id}")
def start_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    now = datetime.utcnow()
    if now < datetime.combine(exam.start_time, datetime.min.time()):
        raise HTTPException(status_code=400, detail="Exam has not started yet")

    exam.start_time = now
    exam.end_time = now + timedelta(minutes=exam.duration_minutes)
    db.commit()
    db.refresh(exam)
    return {"message": "Exam started", "start_time": exam.start_time, "end_time": exam.end_time}


@router.post("/submit-exam/{exam_id}", response_model=ExamResultResponse)
def submit_exam(
        exam_id: int,
        submission: ExamSubmission,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    if not exam_result:
        raise HTTPException(status_code=400, detail="Sınava başlamadınız")

    now = datetime.utcnow()
    if now > exam_result.ends_at:
        raise HTTPException(status_code=400, detail="Sınav süresi doldu")

    if exam_result.correct_answers > 0 or exam_result.incorrect_answers > 0:
        raise HTTPException(status_code=400, detail="Sınav zaten tamamlandı")

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    total_questions = db.query(Question).filter(Question.exam_id == exam_id).count()
    correct_count = 0
    incorrect_count = 0

    for question_answer in submission.answers:
        question = db.query(Question).filter(
            Question.id == question_answer.question_id,
            Question.exam_id == exam_id
        ).first()

        if not question:
            raise HTTPException(status_code=404, detail=f"Soru bulunamadı: {question_answer.question_id}")

        if question_answer.selected_option_id == question.correct_option_id:
            correct_count += 1
        else:
            incorrect_count += 1

    score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    exam_result.correct_answers = correct_count
    exam_result.incorrect_answers = incorrect_count
    db.commit()

    return ExamResultResponse(
        correct_answers=correct_count,
        incorrect_answers=incorrect_count,
        total_questions=total_questions,
        score_percentage=score_percentage
    )


@router.get("/exams/{exam_id}/submission-status")
def check_submission_status(
        exam_id: int,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    has_submitted = exam_result is not None and (
            exam_result.correct_answers > 0 or
            exam_result.incorrect_answers > 0
    )

    return {"hasSubmitted": has_submitted}


@router.get("/exam-results/{exam_id}")
def get_exam_results(
        exam_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    if not exam_result:
        raise HTTPException(status_code=404, detail="Sınav sonucu bulunamadı")

    return {
        "correct_answers": exam_result.correct_answers,
        "incorrect_answers": exam_result.incorrect_answers,
        "started_at": exam_result.started_at,
        "ends_at": exam_result.ends_at
    }


@router.get("/exams")
def get_exams(
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        exams = db.query(Exam).all()
    else:
        exams = db.query(Exam).filter(Exam.is_published == True).all()

    return exams


@router.get("/exams/{exam_id}", response_model=ExamSCH)
async def get_exam(
        exam_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    if not exam.is_published and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Bu sınava erişim yetkiniz yok")

    questions_with_options = []
    for question in exam.questions:
        options = [
            question.option_1,
            question.option_2,
            question.option_3,
            question.option_4,
            question.option_5
        ]
        questions_with_options.append(QuestionSCH(
            id=question.id,
            text=question.text,
            options=options
        ))

    return ExamSCH(
        id=exam.id,
        title=exam.title,
        is_published=exam.is_published,
        questions=questions_with_options
    )

