# dependencies.py
from fastapi import Depends, HTTPException, status, APIRouter, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
# from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
import jwt


from datetime import timedelta
from database.db import SessionDep
from models.models import User
from schemas.schemas import UserCreate, UserResponse, Token
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from security.security import verify_password, create_access_token, get_password_hash

# Імпортуємо налаштування, які ми винесли нагору в auth.py
from security.security import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


# # 1. Ця штука каже FastAPI: "Токени брати з ручки /login"
# # Це потрібно, щоб у Swagger з'явилася форма логіну при натисканні на замочок
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

router = APIRouter(tags=["Auth"])


async def authenticate_user(db: SessionDep,
                      email: str,
                      password: str
                      ):
    # 1. Шукаємо юзера в базі
    query = select(User).where(User.email == email)
    user = await db.scalar(query)


    # 2. Якщо юзера немає - повертаємо False
    if not user:
        return False

    # 3. Перевіряємо пароль, використовуючи твою функцію з security.py
    if not verify_password(password, user.hashed_password):
        return False

    # 4. Все ок -> віддаємо юзера
    return user



# ------- Спосіб отримання через хедер ------

async def get_current_user_api(
        db: SessionDep,
        token: str = Depends(oauth2_scheme)
    ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    query = select(User).where(User.email == email)
    user = await db.scalar(query)

    if user is None:
        raise credentials_exception

    return user



# Swagger відправляє дані не як JSON, а як форму. Тому ми використовуємо OAuth2PasswordRequestForm
@router.post("/token")
async def login_for_access_token(
        db: SessionDep,
        form_data: OAuth2PasswordRequestForm = Depends(),  # 👈 Swagger заповнює це сам

):
    # form_data.username - це буде наш email (Swagger так називає поле)
    user = await authenticate_user(db, email=form_data.username, password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Генеруємо токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Swagger розуміє тільки таку відповідь:
    return {"access_token": access_token, "token_type": "bearer"}




# --- СПОСІБ ОТРИМАННЯ ТОКЕНА (через Куку) ---
def get_token_from_cookie(request: Request):
    # Ми просто читаємо куку. Якщо її немає - поверне None
    token = request.cookies.get("access_token")
    return token


async def get_current_user(db:SessionDep,
                           token: str = Depends(get_token_from_cookie)):# Тепер залежимо від куки

# Заготовка помилки (401), яку ми будемо кидати, якщо щось не так
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    if token is None:
        raise credentials_exception

    try:
        # 3. РОЗШИФРОВКА: Пробуємо прочитати токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 4. ДІСТАЄМО ДАНІ: Шукаємо там поле 'sub' (де ми сховали імейл)
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError: # Якщо токен невалідний
        raise credentials_exception

# 5. ПОШУК В БАЗІ: Чи є такий юзер насправді?
    query = select(User).where(User.email == email)
    result = await db.scalar(query)

    if result is None:
        raise credentials_exception

    # 6. УСПІХ: Повертаємо живого юзера
    return result



@router.post('/register')
async def register_user(db: SessionDep,
                        email: str = Form(...),# 👇 Form(...) означає "бери дані з HTML форми"
                        password: str = Form(...),
                        ):
    query = select(User).where(User.email == email)
    user_one = await db.scalar(query)


    if user_one is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    hash_pass = get_password_hash(password)

    new_user = User(
        email = email,
        hashed_password = hash_pass
    )

    db.add(new_user)
    await db.commit()

    # 3. Після успішної реєстрації перекидаємо на головну
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/login")
async def login_user(db: SessionDep,
                     response: Response,
                     email: str = Form(...),
                     password: str = Form(...),
                     ):
    query = select(User).where(User.email == email)
    user_one = await db.scalar(query)

    if not user_one or not verify_password(password, user_one.hashed_password):
        # Помилка 401 - Неавторизований
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    my_expire_time = timedelta(minutes=30)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_one.email}, expires_delta=access_token_expires
    )
    print("TOKEN:", access_token)

    # 4. 👇 МАГІЯ ТУТ: Створюємо редирект і ліпимо куку

    # Створюємо об'єкт відповіді: "Йди на сторінку /" (код 303 важливий для форм)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Записуємо токен у куки браузера
    response.set_cookie(
        key="access_token",  # Назва ключа (має збігатися з тим, що шукає pages.py)
        value=access_token,  # Значення
        httponly=True,  # Безпека: JS не може вкрасти куку
        max_age=1800  # Час життя (30 хв)
    )

    return response


@router.get("/logout")
async def logout():
    # 1. Створюємо відповідь "Йди на головну сторінку"
    response = RedirectResponse(url="/", status_code=303)

    # 2. 🔥 ГОЛОВНИЙ МОМЕНТ: Видаляємо куку
    # Браузер отримає наказ: "Забудь, що таке access_token!"
    response.delete_cookie("access_token")

    return response
