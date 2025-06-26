from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from app.models.exam import Exam, Question, ExamResult, Answer
from app.models.user import UserDB
from app.routers.auth import get_current_user
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


class ExamResultWithUser(BaseModel):
    id: int
    user_id: int
    exam_id: int
    correct_answers: int
    incorrect_answers: int
    completed: bool
    start_time: str
    end_time: str
    user: dict
    exam: dict

    class Config:
        from_attributes = True


class AnswerDetail(BaseModel):
    id: int
    question_id: int
    selected_option: int
    is_correct: bool
    question: dict

    class Config:
        from_attributes = True


@router.get("/exam-results", response_model=List[ExamResultWithUser])
async def get_all_exam_results(
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Tüm sınav sonuçlarını getir (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Tüm sınav sonuçlarını kullanıcı ve sınav bilgileriyle birlikte getir
        results = (
            db.query(ExamResult)
            .join(UserDB, ExamResult.user_id == UserDB.id)
            .join(Exam, ExamResult.exam_id == Exam.id)
            .all()
        )

        exam_results = []
        for result in results:
            # Kullanıcı bilgilerini hazırla
            user_data = {
                "id": result.user.id,
                "full_name": result.user.full_name,
                "email": result.user.email,
                "school_name": result.user.school_name,
                "branch": result.user.branch,
                "role": result.user.role
            }

            # Sınav bilgilerini hazırla
            exam_data = {
                "id": result.exam.id,
                "title": result.exam.title
            }

            exam_results.append(ExamResultWithUser(
                id=result.id,
                user_id=result.user_id,
                exam_id=result.exam_id,
                correct_answers=result.correct_answers,
                incorrect_answers=result.incorrect_answers,
                completed=result.completed,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                user=user_data,
                exam=exam_data
            ))

        return exam_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri getirilirken hata oluştu: {str(e)}")


@router.get("/exam-results/{exam_result_id}/answers", response_model=List[AnswerDetail])
async def get_exam_result_answers(
        exam_result_id: int,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Belirli bir sınav sonucunun cevap detaylarını getir (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Sınav sonucunu kontrol et
        exam_result = db.query(ExamResult).filter(ExamResult.id == exam_result_id).first()
        if not exam_result:
            raise HTTPException(status_code=404, detail="Sınav sonucu bulunamadı")

        # Cevap detaylarını soru bilgileriyle birlikte getir
        answers = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(Answer.exam_result_id == exam_result_id)
            .all()
        )

        answer_details = []
        for answer in answers:
            # Soru bilgilerini hazırla
            question_data = {
                "id": answer.question.id,
                "text": answer.question.text,
                "option_1": answer.question.option_1,
                "option_2": answer.question.option_2,
                "option_3": answer.question.option_3,
                "option_4": answer.question.option_4,
                "option_5": answer.question.option_5,
                "correct_option_id": answer.question.correct_option_id
            }

            answer_details.append(AnswerDetail(
                id=answer.id,
                question_id=answer.question_id,
                selected_option=answer.selected_option,
                is_correct=answer.is_correct,
                question=question_data
            ))

        return answer_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cevap detayları getirilirken hata oluştu: {str(e)}")


@router.get("/exam-results/grade/{grade}")
async def get_exam_results_by_grade(
        grade: str,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Belirli bir sınıfın sınav sonuçlarını getir (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Belirli sınıftaki öğrencilerin sınav sonuçlarını getir
        results = (
            db.query(ExamResult)
            .join(UserDB, ExamResult.user_id == UserDB.id)
            .join(Exam, ExamResult.exam_id == Exam.id)
            .filter(UserDB.branch == grade)
            .all()
        )

        exam_results = []
        for result in results:
            user_data = {
                "id": result.user.id,
                "full_name": result.user.full_name,
                "email": result.user.email,
                "school_name": result.user.school_name,
                "branch": result.user.branch,
                "role": result.user.role
            }

            exam_data = {
                "id": result.exam.id,
                "title": result.exam.title
            }

            exam_results.append(ExamResultWithUser(
                id=result.id,
                user_id=result.user_id,
                exam_id=result.exam_id,
                correct_answers=result.correct_answers,
                incorrect_answers=result.incorrect_answers,
                completed=result.completed,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                user=user_data,
                exam=exam_data
            ))

        return exam_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sınıf sonuçları getirilirken hata oluştu: {str(e)}")


@router.get("/exam-results/exam/{exam_id}")
async def get_exam_results_by_exam(
        exam_id: int,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Belirli bir sınavın sonuçlarını getir (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Belirli sınavın sonuçlarını getir
        results = (
            db.query(ExamResult)
            .join(UserDB, ExamResult.user_id == UserDB.id)
            .join(Exam, ExamResult.exam_id == Exam.id)
            .filter(ExamResult.exam_id == exam_id)
            .all()
        )

        exam_results = []
        for result in results:
            user_data = {
                "id": result.user.id,
                "full_name": result.user.full_name,
                "email": result.user.email,
                "school_name": result.user.school_name,
                "branch": result.user.branch,
                "role": result.user.role
            }

            exam_data = {
                "id": result.exam.id,
                "title": result.exam.title
            }

            exam_results.append(ExamResultWithUser(
                id=result.id,
                user_id=result.user_id,
                exam_id=result.exam_id,
                correct_answers=result.correct_answers,
                incorrect_answers=result.incorrect_answers,
                completed=result.completed,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                user=user_data,
                exam=exam_data
            ))

        return exam_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sınav sonuçları getirilirken hata oluştu: {str(e)}")


@router.get("/exam-results/search/{search_term}")
async def search_exam_results(
        search_term: str,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Öğrenci adı, email veya okul adına göre sınav sonuçlarını ara (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Arama terimine göre sonuçları getir
        results = (
            db.query(ExamResult)
            .join(UserDB, ExamResult.user_id == UserDB.id)
            .join(Exam, ExamResult.exam_id == Exam.id)
            .filter(
                (UserDB.full_name.ilike(f"%{search_term}%")) |
                (UserDB.email.ilike(f"%{search_term}%")) |
                (UserDB.school_name.ilike(f"%{search_term}%"))
            )
            .all()
        )

        exam_results = []
        for result in results:
            user_data = {
                "id": result.user.id,
                "full_name": result.user.full_name,
                "email": result.user.email,
                "school_name": result.user.school_name,
                "branch": result.user.branch,
                "role": result.user.role
            }

            exam_data = {
                "id": result.exam.id,
                "title": result.exam.title
            }

            exam_results.append(ExamResultWithUser(
                id=result.id,
                user_id=result.user_id,
                exam_id=result.exam_id,
                correct_answers=result.correct_answers,
                incorrect_answers=result.incorrect_answers,
                completed=result.completed,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat(),
                user=user_data,
                exam=exam_data
            ))

        return exam_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama sonuçları getirilirken hata oluştu: {str(e)}")


@router.get("/exam-results/stats/summary")
async def get_exam_results_summary(
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Sınav sonuçları özet istatistiklerini getir (sadece admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    try:
        # Toplam sonuç sayısı
        total_results = db.query(ExamResult).count()

        # Tamamlanan sınav sayısı
        completed_results = db.query(ExamResult).filter(ExamResult.completed == True).count()

        # Ortalama başarı oranı
        results = db.query(ExamResult).filter(ExamResult.completed == True).all()
        total_correct = sum(r.correct_answers for r in results)
        total_questions = sum(r.correct_answers + r.incorrect_answers for r in results)
        avg_success = (total_correct / total_questions * 100) if total_questions > 0 else 0

        # Sınıf bazında istatistikler
        grade_stats = {}
        for grade in ['3', '4', '5', '6', '7']:
            grade_results = (
                db.query(ExamResult)
                .join(UserDB, ExamResult.user_id == UserDB.id)
                .filter(UserDB.branch == grade, ExamResult.completed == True)
                .all()
            )

            if grade_results:
                grade_correct = sum(r.correct_answers for r in grade_results)
                grade_total = sum(r.correct_answers + r.incorrect_answers for r in grade_results)
                grade_avg = (grade_correct / grade_total * 100) if grade_total > 0 else 0
                grade_stats[grade] = {
                    "count": len(grade_results),
                    "avg_success": round(grade_avg, 2)
                }

        return {
            "total_results": total_results,
            "completed_results": completed_results,
            "avg_success_rate": round(avg_success, 2),
            "grade_statistics": grade_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İstatistikler getirilirken hata oluştu: {str(e)}")