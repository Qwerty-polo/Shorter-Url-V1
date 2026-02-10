import os
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import Annotated

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# (Фіча для деплою) Render дає "postgres://", а SQLAlchemy хоче "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

class Base(DeclarativeBase):
    pass

engine = create_async_engine(DATABASE_URL, echo=True)

Session_local = async_sessionmaker(
    bind= engine,
    class_=AsyncSession, #необовязково якшо вже зверху вказав шо використовуєш async_sessionmaker
    expire_on_commit=False
)

async def get_db():
#беремо сесії з нашої фабрики яку ми прописали вище
    async with Session_local() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db)]