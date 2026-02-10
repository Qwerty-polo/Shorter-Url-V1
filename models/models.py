from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, Boolean, ForeignKey, DateTime
from database.db import Base
from sqlalchemy.sql import func

from datetime import datetime


class Url(Base):
    __tablename__ = "urls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    target_url: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    clicks: Mapped[int] = mapped_column(Integer, default=0)

    click_history: Mapped[list['Click']] = relationship(back_populates="url", cascade="all, delete-orphan")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    owner: Mapped['User'] = relationship(back_populates="urls")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)

    urls: Mapped[list['Url']] = relationship(back_populates='owner')

# models.py


class Click(Base):
    __tablename__ = "clicks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 👇 БУЛО: server_default=func.now() (це робота бази даних)
    # 👇 СТАЛО: default=datetime.utcnow (це робота Python, це надійніше зараз)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    url_id: Mapped[int] = mapped_column(Integer, ForeignKey("urls.id"))

    # Тут ми вже виправили раніше, тут все ок
    url: Mapped['Url'] = relationship(back_populates="click_history")