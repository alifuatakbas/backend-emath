from fastapi import APIRouter, Depends, HTTPException,Form
from sqlalchemy.orm import Session
from app.schemas.exam_schemas import ExamCreateRequest, ExamSCH, QuestionSCH
from database import get_db
from app.models.exam import Exam, Question, ExamResult
from app.routers.auth import get_current_user
from app.models.user import UserDB
from fastapi import File, UploadFile
import os
from app.services.storage import S3Service
import pytz
from datetime import datetime
from pydantic import BaseModel
from app.services.schedular import schedule_exam_events




# Normal router yerine admin prefix'li router kullanalım
router = APIRouter(prefix="/admin", tags=["admin"])
s3_service = S3Service()


class ExamCreateRequest(BaseModel):
    title: str
    requires_registration: bool = True  # Bu satırı ekleyin
    registration_start_date: datetime
    registration_end_date: datetime
    exam_start_date: datetime
    exam_end_date: datetime | None = None

@router.post("/create-exam")
def create_exam(
        request: ExamCreateRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Başvurusuz sınavlar için tarih kontrolü
        if request.requires_registration:
            # Tarihleri UTC'ye çevir
            exam = Exam(
                title=request.title,
                requires_registration=request.requires_registration,
                registration_start_date=request.registration_start_date.replace(tzinfo=pytz.UTC),
                registration_end_date=request.registration_end_date.replace(tzinfo=pytz.UTC),
                exam_start_date=request.exam_start_date.replace(tzinfo=pytz.UTC),
                exam_end_date=request.exam_end_date.replace(tzinfo=pytz.UTC) if request.exam_end_date else None,
                status='registration_pending'  # Başlangıç durumu
            )

            # Tarih kontrolü
            if exam.registration_end_date > exam.exam_start_date:
                raise HTTPException(
                    status_code=400,
                    detail="Başvuru bitiş tarihi sınav başlangıç tarihinden sonra olamaz"
                )
        else:
            # Başvurusuz sınavlar için sadece sınav tarihleri
            exam = Exam(
                title=request.title,
                requires_registration=request.requires_registration,
                registration_start_date=None,
                registration_end_date=None,
                exam_start_date=request.exam_start_date.replace(tzinfo=pytz.UTC),
                exam_end_date=request.exam_end_date.replace(tzinfo=pytz.UTC) if request.exam_end_date else None,
                status='registration_pending'  # Başlangıç durumu
            )

        db.add(exam)
        db.commit()
        db.refresh(exam)

        # Otomatik işlemleri zamanla
        schedule_exam_events(
            exam_id=exam.id,
            registration_start=exam.registration_start_date,
            registration_end=exam.registration_end_date,
            exam_start=exam.exam_start_date,
            exam_end=exam.exam_end_date if exam.exam_end_date else exam.exam_start_date
        )

        return {
            "message": "Sınav oluşturuldu ve zamanlandı",
            "exam_id": exam.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



# Dosya yükleme için güvenli bir yol oluştur
UPLOAD_DIR = "static/question_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@router.post("/add-question/{exam_id}")
async def add_question(
    exam_id: int,
    text: str = Form(...),
    options: list[str] = Form(...),
    correct_option_index: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Yetkiniz yok")

        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Sınav bulunamadı")

        # Fotoğraf yükleme işlemi
        image_url = None
        if image:
            image_url = await s3_service.upload_file(image)
            if not image_url:
                raise HTTPException(status_code=500, detail="Fotoğraf yüklenemedi")

        # Soru sayısını artır
        exam.question_counter += 1

        question = Question(
            exam_id=exam_id,
            text=text,
            image=image_url,  # Artık tam URL
            option_1=options[0],
            option_2=options[1],
            option_3=options[2],
            option_4=options[3],
            option_5=options[4],
            correct_option_id=correct_option_index
        )

        db.add(question)
        db.commit()
        db.refresh(question)

        return {
            "message": "Soru ve seçenekler başarıyla eklendi",
            "id": question.id,
            "image_url": image_url
        }

    except Exception as e:
        print(f"Hata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exams/{exam_id}/submission-status")
def check_submission_status(exam_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    exam_result = db.query(ExamResult).filter(
        ExamResult.user_id == current_user.id,
        ExamResult.exam_id == exam_id
    ).first()
    has_submitted = exam_result is not None
    return {"hasSubmitted": has_submitted}





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
