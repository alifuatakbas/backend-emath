from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import  OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models.user import UserDB
from app.schemas.user import User, UserCreate, Token
from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from database import get_db

router = APIRouter()


@router.post("/register", response_model=User)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Email kontrolü
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email adresi zaten kayıtlı")

    hashed_password = get_password_hash(user.password)
    db_user = UserDB(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email veya şifre hatalı")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user