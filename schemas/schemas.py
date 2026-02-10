from datetime import datetime

from pydantic import Field

from pydantic import BaseModel, HttpUrl, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=30)

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

class UrlCreate(BaseModel):
    # HttpUrl крутий тим, що він сам перевірить, чи є там "http://"
    # Якщо юзер кине "привіт" - Pydantic сам видасть помилку.
    target_url: HttpUrl


class UrlInfo(UrlCreate):
    key: str
    is_active: bool
    clicks: int

    short_url: str | None = None

    # 👇 2. Ця магія дозволяє схемі читати дані прямо з об'єктів SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

# це для чого щоб користувач отримав свій токен у Json форматі
class Token(BaseModel):
    access_token: str
    token_type: str