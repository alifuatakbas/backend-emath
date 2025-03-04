from pydantic import BaseModel,Field

class UserBase(BaseModel):
    email: str
    full_name: str
    school_name: str
    branch: str
    parent_name: str  # Eklendi
    phone: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    # Test deployment
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class ApplicationCreate(BaseModel):
    fullName: str = Field(max_length=100)
    email: str = Field(max_length=100)
    phone: str = Field(max_length=20)
    school: str = Field(max_length=200)
    grade: str = Field(max_length=50)
    message: str