from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.schemas.exam_schemas import ExamSubmission, ExamResultResponse, ExamCreateRequest,ExamSCH,QuestionSCH
from database import get_db
from app.models.exam import Exam, Question, ExamResult
from app.routers.auth import get_current_user
from app.models.user import UserDB
from datetime import datetime, timedelta,date
import pytz
router = APIRouter()
User = UserDB




@router.get("/exams")
def get_exams(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        # Admin kullanıcı tüm sınavları görebilir
        exams = db.query(Exam).all()
    else:
        # Normal kullanıcı için:
        # 1. Yalnızca yayınlanmış sınavları al
        # 2. Kullanıcının çözmediği sınavları filtrele
        taken_exam_ids = db.query(ExamResult.exam_id).filter(
            ExamResult.user_id == current_user.id
        ).all()
        taken_exam_ids = [exam_id for (exam_id,) in taken_exam_ids]

        exams = db.query(Exam).filter(
            Exam.is_published == True,
            ~Exam.id.in_(taken_exam_ids)  # Çözülmemiş sınavları filtrele
        ).all()

    return exams




@router.get("/exams/{exam_id}")
def get_exam(
        exam_id: int,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Kullanıcı daha önce sınavı çözdüyse
    existing_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    # Soruların options'larını da içerecek şekilde veriyi döndürüyoruz
    questions = []
    for question in exam.questions:
        options = [
            question.option_1,
            question.option_2,
            question.option_3,
            question.option_4,
            question.option_5
        ]
        questions.append({
            "id": question.id,
            "text": question.text,
            "options": options,  # options burada bir liste olarak döndürülüyor
            "correct_option_id": question.correct_option_id
        })

    return {
        "id": exam.id,
        "title": exam.title,
        "questions": questions,
        "has_been_taken": bool(existing_result)
    }


@router.post("/start-exam/{exam_id}")
def start_exam(
        exam_id: int,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    try:
        # Sınavın var olup olmadığını kontrol et
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Sınav bulunamadı")

        # Kullanıcının bu sınavı daha önce başlatıp başlatmadığını kontrol et
        existing_result = db.query(ExamResult).filter(
            ExamResult.user_id == current_user.id,
            ExamResult.exam_id == exam_id
        ).first()

        if existing_result:
            # Sınav zaten başlatılmış, süre kontrolü yap
            current_time = datetime.utcnow()
            remaining_time = existing_result.end_time - current_time

            if remaining_time.total_seconds() <= 0:
                raise HTTPException(status_code=400, detail="Sınav süresi dolmuş")

            # Süre dolmamışsa kalan süreyi hesapla
            remaining_minutes = int(remaining_time.total_seconds() / 60)

            return {
                "message": "Sınav devam ediyor",
                "start_time": existing_result.start_time.isoformat(),
                "end_time": existing_result.end_time.isoformat(),
                "remaining_minutes": remaining_minutes
            }

        # Yeni sınav başlat
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=90)

        # Timezone'ları açıkça belirt
        start_time = start_time.replace(tzinfo=pytz.UTC)
        end_time = end_time.replace(tzinfo=pytz.UTC)

        new_result = ExamResult(
            user_id=current_user.id,
            exam_id=exam_id,
            start_time=start_time,
            end_time=end_time,
            correct_answers=0,
            incorrect_answers=0
        )

        db.add(new_result)
        db.commit()
        db.refresh(new_result)

        return {
            "message": "Sınav başlatıldı",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "remaining_minutes": 90
        }

    except Exception as e:
        print(f"Start exam error: {str(e)}")  # Hata ayıklama için
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Sınav başlatılırken bir hata oluştu: {str(e)}")

@router.get("/exam-time/{exam_id}")
def get_exam_time_status(
    exam_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()

    if not exam_result:
        return {
            "is_started": False,
            "remaining_minutes": None,
            "message": "Sınav henüz başlatılmamış"
        }

    current_time = datetime.utcnow()
    end_time = exam_result.end_time

    if current_time > end_time:
        return {
            "is_started": True,
            "remaining_minutes": 0,
            "message": "Sınav süresi dolmuş"
        }

    remaining_time = end_time - current_time
    remaining_minutes = int(remaining_time.total_seconds() / 60)

    return {
        "is_started": True,
        "remaining_minutes": remaining_minutes,
        "start_time": exam_result.start_time.isoformat(),
        "end_time": exam_result.end_time.isoformat(),
        "message": "Sınav devam ediyor"
    }


@router.post("/submit-exam/{exam_id}", response_model=ExamResultResponse)
def submit_exam(
        exam_id: int,
        submission: ExamSubmission,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    try:
        # Sınavın başlatılıp başlatılmadığını kontrol et
        existing_result = db.query(ExamResult).filter(
            ExamResult.user_id == current_user.id,
            ExamResult.exam_id == exam_id
        ).first()

        if not existing_result:
            raise HTTPException(status_code=400, detail="Sınav henüz başlatılmamış")

        # Debug için yazdırma
        print(f"Submission answers: {submission.answers}")

        # Doğru ve yanlış cevapları hesapla
        correct_count = 0
        incorrect_count = 0

        # Önce sınavın tüm sorularını al
        exam_questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        questions_dict = {q.id: q for q in exam_questions}

        print(f"Available questions: {[q.id for q in exam_questions]}")  # Debug için

        for answer in submission.answers:
            print(f"Processing answer for question {answer.question_id}")  # Debug için

            question = questions_dict.get(answer.question_id)
            if question:
                if answer.selected_option_id == question.correct_option_id:
                    correct_count += 1
                else:
                    incorrect_count += 1
            else:
                print(f"Question not found: {answer.question_id}")  # Debug için

        total_questions = len(exam_questions)
        if total_questions == 0:
            raise HTTPException(status_code=400, detail="Bu sınavda soru bulunmamaktadır")

        score_percentage = (correct_count / total_questions) * 100

        # Sonuçları kaydet
        existing_result.correct_answers = correct_count
        existing_result.incorrect_answers = incorrect_count
        db.commit()

        print(f"Final results - Correct: {correct_count}, Incorrect: {incorrect_count}")  # Debug için

        return ExamResultResponse(
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            total_questions=total_questions,
            score_percentage=score_percentage
        )

    except Exception as e:
        print(f"Error in submit_exam: {str(e)}")  # Debug için
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Sınav gönderilirken bir hata oluştu: {str(e)}"
        )