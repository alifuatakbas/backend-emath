from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, String
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.exam import Exam
from database import Base, SessionLocal


# ExamSession Model
class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    status = Column(String, default="pending")  # pending, active, completed

    # Relationships will be handled in their respective models
    # exam = relationship("Exam", back_populates="sessions")
    # user = relationship("User", back_populates="exam_sessions")


# Scheduler'ı yapılandır
scheduler = BackgroundScheduler({
    'apscheduler.timezone': 'UTC',
    'apscheduler.job_defaults.coalesce': True,
    'apscheduler.job_defaults.max_instances': 1
})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def update_exam_status(exam_id: int, status: str):
    """
    Sınav durumunu günceller ve gerekli işlemleri yapar
    """
    db = next(get_db())
    try:
        # Sınavı bul
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if exam:
            exam.status = status

            # Eğer sınav bittiyse, tüm aktif oturumları kapat
            if status == 'completed':
                active_sessions = db.query(ExamSession).filter(
                    ExamSession.exam_id == exam_id,
                    ExamSession.is_completed == False
                ).all()

                for session in active_sessions:
                    session.is_completed = True
                    session.end_time = datetime.utcnow()
                    session.status = "completed"

            db.commit()
            print(f"Sınav {exam_id} durumu {status} olarak güncellendi: {datetime.utcnow()}")
    except Exception as e:
        print(f"Sınav durumu güncellenirken hata oluştu: {e}")
        db.rollback()
    finally:
        db.close()


def schedule_exam_events(exam_id: int,
                         registration_start: datetime,
                         registration_end: datetime,
                         exam_start: datetime,
                         exam_end: datetime):
    """
    Sınav için tüm otomatik işlemleri zamanlar
    """
    try:
        # Başvuru başlangıcı için zamanlama
        scheduler.add_job(
            update_exam_status,
            'date',
            run_date=registration_start,
            args=[exam_id, 'registration_open'],
            id=f'exam_{exam_id}_reg_start',
            replace_existing=True
        )
        print(f"Sınav {exam_id} başvuru başlangıcı zamanlandı: {registration_start}")

        # Başvuru bitişi için zamanlama
        scheduler.add_job(
            update_exam_status,
            'date',
            run_date=registration_end,
            args=[exam_id, 'registration_closed'],
            id=f'exam_{exam_id}_reg_end',
            replace_existing=True
        )
        print(f"Sınav {exam_id} başvuru bitişi zamanlandı: {registration_end}")

        # Sınav başlangıcı için zamanlama
        scheduler.add_job(
            update_exam_status,
            'date',
            run_date=exam_start,
            args=[exam_id, 'exam_active'],
            id=f'exam_{exam_id}_start',
            replace_existing=True
        )
        print(f"Sınav {exam_id} başlangıcı zamanlandı: {exam_start}")

        # Sınav bitişi için zamanlama
        scheduler.add_job(
            update_exam_status,
            'date',
            run_date=exam_end,
            args=[exam_id, 'completed'],
            id=f'exam_{exam_id}_end',
            replace_existing=True
        )
        print(f"Sınav {exam_id} bitişi zamanlandı: {exam_end}")

    except Exception as e:
        print(f"Sınav zamanlama işleminde hata: {e}")


def get_exam_status(exam, current_time: datetime = None) -> str:
    """
    Sınavın mevcut durumunu hesaplar
    """
    if current_time is None:
        current_time = datetime.utcnow()

    if not exam.is_published:
        return "unpublished"

    if current_time < exam.registration_start_date:
        return "registration_pending"

    if current_time <= exam.registration_end_date:
        return "registration_open"

    if current_time <= exam.exam_end_date:
        return "exam_active"

    return "completed"


def init_scheduler():
    """
    Uygulama başlangıcında scheduler'ı başlatır ve mevcut sınavları kontrol eder
    """
    if not scheduler.running:
        scheduler.start()
        print("Scheduler başlatıldı")

        # Mevcut sınavları kontrol et ve zamanla
        db = next(get_db())
        try:
            current_time = datetime.utcnow()
            exams = db.query(Exam).all()

            for exam in exams:
                # Sadece gelecekteki olayları zamanla
                if exam.exam_end_date > current_time:
                    schedule_exam_events(
                        exam_id=exam.id,
                        registration_start=exam.registration_start_date,
                        registration_end=exam.registration_end_date,
                        exam_start=exam.exam_start_date,
                        exam_end=exam.exam_end_date
                    )
        except Exception as e:
            print(f"Mevcut sınavları kontrol ederken hata: {e}")
        finally:
            db.close()


def shutdown_scheduler():
    """
    Uygulama kapanırken scheduler'ı durdurur
    """
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler durduruldu")


# Sınav durumları için sabitler
EXAM_STATUSES = {
    "unpublished": "Yayınlanmamış",
    "registration_pending": "Başvuru Beklemede",
    "registration_open": "Başvuru Açık",
    "registration_closed": "Başvuru Kapalı",
    "exam_active": "Sınav Aktif",
    "completed": "Tamamlandı"
}

# Hata mesajları için sabitler
ERROR_MESSAGES = {
    "exam_not_found": "Sınav bulunamadı",
    "update_failed": "Sınav durumu güncellenirken hata oluştu",
    "scheduling_failed": "Sınav zamanlama işlemi başarısız oldu"
}