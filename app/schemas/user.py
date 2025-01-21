from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    full_name: str
    school_name: str
    branch: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int


    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class ApplicationCreate(BaseModel):
    fullName: str
    email: str
    phone: str | None = None
    school: str
    grade: str
    message: str | None = None