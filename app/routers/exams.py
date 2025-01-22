from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.exam_schemas import ExamSubmission, ExamResultResponse, ExamWithResult, QuestionResultDetail
from database import get_db
from app.models.exam import Exam, Question, ExamResult, Answer
from app.routers.auth import get_current_user
from app.models.user import UserDB
from datetime import datetime, timedelta
import pytz
from typing import List
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

    # Soruların options'larını ve image'larını da içerecek şekilde veriyi döndürüyoruz
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
            "options": options,
            "image": question.image,  # image alanını ekledik
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

        # Sınavın tüm sorularını al
        exam_questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        questions_dict = {q.id: q for q in exam_questions}

        correct_count = 0
        incorrect_count = 0

        # Önce mevcut cevapları sil (eğer varsa)
        db.query(Answer).filter(Answer.exam_result_id == existing_result.id).delete()

        # Öğrenci cevaplarını kaydet ve doğru/yanlış sayısını hesapla
        answers_to_add = []
        for answer in submission.answers:
            question = questions_dict.get(answer.question_id)
            if question:
                is_correct = answer.selected_option_id == question.correct_option_id

                student_answer = Answer(
                    exam_result_id=existing_result.id,
                    question_id=question.id,
                    selected_option=answer.selected_option_id,
                    is_correct=is_correct
                )
                answers_to_add.append(student_answer)

                if is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1

        # Toplu olarak cevapları ekle
        db.bulk_save_objects(answers_to_add)

        total_questions = len(exam_questions)
        if total_questions == 0:
            raise HTTPException(status_code=400, detail="Bu sınavda soru bulunmamaktadır")

        score_percentage = (correct_count / total_questions) * 100

        # Sonuçları güncelle
        existing_result.correct_answers = correct_count
        existing_result.incorrect_answers = incorrect_count
        existing_result.completed = True  # Sınavı tamamlandı olarak işaretle

        # Soru detaylarını al
        questions_with_answers = []
        for question in exam_questions:
            student_answer = next(
                (ans for ans in answers_to_add if ans.question_id == question.id),
                None
            )

            options = [
                question.option_1,
                question.option_2,
                question.option_3,
                question.option_4,
                question.option_5
            ]
            # None değerleri listeden çıkar
            options = [opt for opt in options if opt is not None]

            questions_with_answers.append(QuestionResultDetail(
                question_text=question.text,
                question_image=question.image_url if hasattr(question, 'image_url') else None,
                options=options,
                correct_option=question.correct_option_id,
                student_answer=student_answer.selected_option if student_answer else None,
                is_correct=student_answer.is_correct if student_answer else False
            ))

        # Değişiklikleri kaydet
        db.commit()

        return ExamResultResponse(
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            total_questions=total_questions,
            score_percentage=score_percentage,
            questions=questions_with_answers
        )

    except Exception as e:
        print(f"Hata detayı: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Sınav gönderilirken bir hata oluştu: {str(e)}"
        )


@router.get("/exam-results/{exam_id}", response_model=ExamResultResponse)
async def get_exam_result(
        exam_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    result = (
        db.query(ExamResult)
        .filter(
            ExamResult.exam_id == exam_id,
            ExamResult.user_id == current_user.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Bu sınav için sonuç bulunamadı"
        )

    exam_questions = (
        db.query(Question)
        .filter(Question.exam_id == exam_id)
        .all()
    )

    student_answers = (
        db.query(Answer)
        .filter(Answer.exam_result_id == result.id)
        .all()
    )

    questions_with_answers = []
    for question in exam_questions:
        student_answer = next(
            (ans for ans in student_answers if ans.question_id == question.id),
            None
        )

        options = [
            question.option_1,
            question.option_2,
            question.option_3,
            question.option_4,
            question.option_5
        ]
        options = [opt for opt in options if opt is not None]

        # Doğru cevap indeksi 0'dan başlıyor (0=1.şık, 1=2.şık, ...)
        correct_option_index = question.correct_option_id - 1

        questions_with_answers.append({
            "question_text": question.text,
            "question_image": question.image_url if hasattr(question, 'image_url') else None,
            "options": options,
            "correct_option": correct_option_index,  # 0-based index (0=1.şık, 1=2.şık, ...)
            "student_answer": student_answer.selected_option - 1 if student_answer else None,  # Öğrencinin cevabını da 0-based yap
            "is_correct": student_answer.is_correct if student_answer else False
        })

    total_questions = result.correct_answers + result.incorrect_answers
    score_percentage = (result.correct_answers / total_questions * 100) if total_questions > 0 else 0

    return {
        "correct_answers": result.correct_answers,
        "incorrect_answers": result.incorrect_answers,
        "total_questions": total_questions,
        "score_percentage": round(score_percentage, 2),
        "questions": questions_with_answers
    }

@router.get("/user/completed-exams", response_model=List[ExamWithResult])
async def get_completed_exams(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # Kullanıcının sonuçları olan sınavları getir
    completed_exams = (
        db.query(Exam)
        .join(ExamResult, Exam.id == ExamResult.exam_id)
        .filter(ExamResult.user_id == current_user.id)
        .all()
    )

    return completed_exams