from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.schemas.exam_schemas import ExamSubmission, ExamResultResponse, ExamCreateRequest,ExamSCH,QuestionSCH
from database import get_db
from app.models.exam import Exam, Question, ExamResult
from app.routers.auth import get_current_user
from app.models.user import UserDB
from datetime import datetime, timedelta
router = APIRouter()
User = UserDB

@router.post("/create-exam")
def create_exam(request: ExamCreateRequest | None
                , db: Session = Depends(get_db),
                current_user: UserDB = Depends(get_current_user)):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")
    exam = Exam(title=request.title)
    db.add(exam)
    db.commit()
    return {"message": "Sınav oluşturuldu", "exam_id": exam.id}


@router.post("/add-question/{exam_id}")
def add_question(exam_id: int,
                 text: str,
                 options: list[str],
                 correct_option_index: int,
                 db: Session = Depends(get_db),
                 current_user: UserDB = Depends(get_current_user)
                 ):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    # Soru oluşturuluyor, sadece metin alınıyor
    if len(options) != 5:
        raise HTTPException(status_code=400, detail="Her soru için 5 seçenek gereklidir")

    # Exam modelinden sınavı alıyoruz
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    # Exam'a ait question_counter'ı artırıyoruz
    question_number = exam.question_counter + 1
    exam.question_counter = question_number  # question_counter'ı güncelle

    # Yeni soruyu ekliyoruz
    question = Question(exam_id=exam_id, text=text)
    question.option_1 = options[0]
    question.option_2 = options[1]
    question.option_3 = options[2]
    question.option_4 = options[3]
    question.option_5 = options[4]

    # Doğru cevabın index'ine göre correct_option_id'yi belirliyoruz
    question.correct_option_id = correct_option_index

    # Question ID'yi, her sınav için sıralı şekilde belirlemek
    question.question_id = question_number  # question_id her sınav için sıralı olacak

    db.add(question)
    db.commit()

    # question_counter'ı veritabanına kaydediyoruz
    db.commit()

    return {"message": "Soru ve seçenekler eklendi", "question_id": question.question_id}



@router.get("/exams/{exam_id}/submission-status")
def check_submission_status(exam_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()
    has_submitted = exam_result is not None
    return {"hasSubmitted": has_submitted}

@router.post("/submit-exam/{exam_id}", response_model=ExamResultResponse)
def submit_exam(
        exam_id: int,
        submission: ExamSubmission,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    existing_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()
    if not existing_result:
        raise HTTPException(status_code=400, detail="Exam not started")

    now = datetime.utcnow()
    # Check if the exam time has expired based on ends_at
    if now > existing_result.ends_at:
        raise HTTPException(status_code=400, detail="Exam time is over")

    # Calculate correct and incorrect answers
    correct_count = 0
    incorrect_count = 0

    for question_answer in submission.answers:
        question = db.query(Question).filter(Question.id == question_answer.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_answer.question_id} not found")

        correct_option_index = question.correct_option_id
        if question_answer.selected_option_id == correct_option_index:
            correct_count += 1
        else:
            incorrect_count += 1

    score_percentage = (correct_count / len(submission.answers)) * 100 if len(submission.answers) > 0 else 0

    existing_result.correct_answers = correct_count
    existing_result.incorrect_answers = incorrect_count
    db.commit()

    return ExamResultResponse(
        correct_answers=correct_count,
        incorrect_answers=incorrect_count,
        total_questions=len(submission.answers),
        score_percentage=score_percentage
    )

@router.get("/exam-results/{exam_id}")
def get_exam_results(
        exam_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Kullanıcının bu sınavdaki sonuçlarını getir
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    if not exam_result:
        raise HTTPException(status_code=404, detail="Sınav sonucu bulunamadı")

    return {
        "correct_answers": exam_result.correct_answers,
        "incorrect_answers": exam_result.incorrect_answers
    }

@router.get("/exams")
def get_exams(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        # Admin kullanıcı tüm sınavları görebilir
        exams = db.query(Exam).all()
    else:
        # Normal kullanıcı yalnızca yayınlanmış sınavları görebilir
        exams = db.query(Exam).filter(Exam.is_published == True).all()

    return exams


@router.post("/exams/{exam_id}/publish/{publish}", response_model=ExamSCH)
async def publish_exam(
    exam_id: int,
    publish: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    if publish not in [0, 1]:
        raise HTTPException(status_code=400, detail="Publish parameter must be 0 or 1")

    exam.is_published = bool(publish)
    db.commit()
    db.refresh(exam)

    # Prepare questions with options
    questions_with_options = []
    for question in exam.questions:
        options = [question.option_1, question.option_2, question.option_3, question.option_4, question.option_5]
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

@router.get("/exams/{exam_id}", response_model=ExamSCH)
async def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı")

    # Prepare questions with options
    questions_with_options = []
    for question in exam.questions:
        options = [question.option_1, question.option_2, question.option_3, question.option_4, question.option_5]
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

