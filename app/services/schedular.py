from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, String
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.exam import Exam
from database import Base, SessionLocal
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.exam import Exam, ExamResult, Answer
from database import get_db


def auto_complete_exams():
    """
    Süresi dolan sınavları otomatik olarak tamamlar
    """
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()

        # Süresi dolan aktif sınavları bul
        active_results = db.query(ExamResult).join(Exam).filter(
            Exam.status == 'exam_active',
            ExamResult.completed == False,
            ExamResult.end_time <= current_time
        ).all()

        print(f"Found {len(active_results)} exams to auto-complete")

        for result in active_results:
            try:
                # Mevcut cevapları al
                answers = db.query(Answer).filter(
                    Answer.exam_result_id == result.id
                ).all()

                # Sonuçları hesapla
                correct_count = sum(1 for a in answers if a.is_correct)
                incorrect_count = len(answers) - correct_count

                # Sonucu güncelle
                result.completed = True
                result.correct_answers = correct_count
                result.incorrect_answers = incorrect_count
                result.auto_completed = True  # Otomatik tamamlandığını belirt

                db.commit()
                print(f"Auto-completed exam result {result.id} for user {result.user_id}")

            except Exception as e:
                print(f"Error auto-completing exam result {result.id}: {str(e)}")
                db.rollback()

    except Exception as e:
        print(f"Error in auto_complete_exams: {str(e)}")
    finally:
        db.close()




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
    db = SessionLocal()
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
        # Başvuru başlangıcı için zamanlama (sadece None değilse)
        if registration_start:
            scheduler.add_job(
                update_exam_status,
                'date',
                run_date=registration_start,
                args=[exam_id, 'registration_open'],
                id=f'exam_{exam_id}_reg_start',
                replace_existing=True
            )
            print(f"Sınav {exam_id} başvuru başlangıcı zamanlandı: {registration_start}")

        # Başvuru bitişi için zamanlama (sadece None değilse)
        if registration_end:
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
        if exam_start:
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
        if exam_end:
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

    # Başvurusuz sınavlar için özel mantık
    if not exam.requires_registration:
        if current_time < exam.exam_start_date:
            return "registration_pending"
        elif current_time <= exam.exam_end_date:
            return "exam_active"
        else:
            return "completed"

    # Başvurulu sınavlar için normal mantık
    if exam.registration_start_date and current_time < exam.registration_start_date:
        return "registration_pending"

    if exam.registration_end_date and current_time <= exam.registration_end_date:
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

        # Auto-complete job'ını ekle
        scheduler.add_job(
            auto_complete_exams,
            'interval',
            minutes=1,
            id='auto_complete_exams',
            replace_existing=True
        )
        print("Auto-complete job eklendi")

        # Mevcut sınavları kontrol et ve zamanla
        db = SessionLocal()
        try:
            current_time = datetime.utcnow()
            exams = db.query(Exam).all()

            for exam in exams:
                # Sadece gelecekteki olayları zamanla
                if exam.exam_end_date and exam.exam_end_date > current_time:
                    # Başvurusuz sınavlar için özel kontrol
                    if not exam.requires_registration:
                        # Başvurusuz sınavlar için sadece sınav başlangıç ve bitiş zamanlarını ayarla
                        if exam.exam_start_date and exam.exam_start_date > current_time:
                            scheduler.add_job(
                                update_exam_status,
                                'date',
                                run_date=exam.exam_start_date,
                                args=[exam.id, 'exam_active'],
                                id=f'exam_{exam.id}_start',
                                replace_existing=True
                            )
                            print(f"Başvurusuz sınav {exam.id} başlangıcı zamanlandı: {exam.exam_start_date}")
                        
                        if exam.exam_end_date and exam.exam_end_date > current_time:
                            scheduler.add_job(
                                update_exam_status,
                                'date',
                                run_date=exam.exam_end_date,
                                args=[exam.id, 'completed'],
                                id=f'exam_{exam.id}_end',
                                replace_existing=True
                            )
                            print(f"Başvurusuz sınav {exam.id} bitişi zamanlandı: {exam.exam_end_date}")
                    else:
                        # Normal başvurulu sınavlar için tüm zamanlamaları yap
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
        
        # Debug bilgilerini yazdır
        print("=== SCHEDULER DEBUG ===")
        debug_scheduler()
        print("=== END DEBUG ===")
    
    return scheduler


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

def debug_scheduler():
    """
    Scheduler durumunu debug etmek için
    """
    print(f"Scheduler running: {scheduler.running}")
    print(f"Total jobs: {len(scheduler.get_jobs())}")
    
    for job in scheduler.get_jobs():
        print(f"Job ID: {job.id}")
        print(f"  Function: {job.func.__name__}")
        print(f"  Next run: {job.next_run_time}")
        print(f"  Args: {job.args}")
        print("---")
    
    # Mevcut sınavları kontrol et
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        exams = db.query(Exam).all()
        
        print(f"Current time: {current_time}")
        print(f"Total exams: {len(exams)}")
        
        for exam in exams:
            print(f"Exam {exam.id}: {exam.title}")
            print(f"  Status: {exam.status}")
            print(f"  Requires registration: {exam.requires_registration}")
            print(f"  Exam start: {exam.exam_start_date}")
            print(f"  Exam end: {exam.exam_end_date}")
            print(f"  Registration start: {exam.registration_start_date}")
            print(f"  Registration end: {exam.registration_end_date}")
            print("---")
    except Exception as e:
        print(f"Error in debug_scheduler: {e}")
    finally:
        db.close()