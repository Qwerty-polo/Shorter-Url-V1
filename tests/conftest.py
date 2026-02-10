import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.db import get_db, Base

from main import app



# 1. Створюємо тимчасову базу даних (в пам'яті)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


# 2. Функція, яка підміняє справжню БД на тестову
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

# 3. Підміняємо залежність у самому FastAPI
app.dependency_overrides[get_db] = override_get_db

# Ця штука каже pytest: "Всі тести будуть асинхронні"
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# 4. Готуємо "Клієнта" (наш віртуальний браузер)
@pytest.fixture(scope="function")
async def client():

    # Перед тестами: Створюємо таблиці
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Віддаємо клієнта для тестів
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

   # Після тестів: Видаляємо таблиці (прибираємо за собою)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)