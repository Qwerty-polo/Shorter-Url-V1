from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, desc, delete
from starlette import status
from starlette.responses import RedirectResponse

from generatkey.utils import generate_key
from typing import Optional
from database.db import SessionDep
from models.models import User, Url, Click
from routers.api.auth import get_current_user
from fastapi import Form
from routers.api.auth import authenticate_user
from security.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, get_password_hash
from datetime import timedelta
import validators

# кю ар коди імпорти
import qrcode
from io import BytesIO # Штука, щоб тримати картинку в пам'яті, а не на диску
from fastapi.responses import StreamingResponse # Спеціальна відповідь для файлів

from routers.api.auth import get_token_from_cookie

from fastapi.templating import Jinja2Templates



import re

from routers.api.url_shorter import get_or_404

router = APIRouter(tags=["Web Pages"])

templates = Jinja2Templates(directory="templates")


# --- СТОРІНКА РЕЄСТРАЦІЇ ---
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# --- Register Post ----
@router.post("/register", response_class=HTMLResponse)
async def register_user_ui(
        db: SessionDep,
        request: Request,
        email: str = Form(...),
        password: str = Form(...)
        ):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    exist_user = result.scalar_one_or_none()

    if exist_user:
        return templates.TemplateResponse("register.html", {"request": request,"error": "User already exists"})

    hashed_pass = get_password_hash(password)

    new_user = User(email=email, hashed_pass=hashed_pass)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)






# ------- Login ----------

@router.post("/login")
async def login_web(db: SessionDep,
                    request: Request,
                    email: str = Form(...),
                    password: str = Form(...)
                    ):
    #перевірка юзера

    query = select(User).where(User.email == email)
    user_one = await db.scalar(query)

    if not user_one or not verify_password(password, user_one.hashed_password):
        # Помилка 401 - Неавторизований
        return templates.TemplateResponse("login.html", {"request": request, "error": "Password or username are incorrect"})

    my_expire_time = timedelta(minutes=30)

    access_token_expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token({
        "sub": user_one.email}, expires_delta=access_token_expire)


    response = RedirectResponse(url="/dashboard", status_code=303)

    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=my_expire_time)

    return response



@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


#------  Logout ---------
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)

    #  Видаляємо куку
    response.delete_cookie("access_token")

    return response

# --- ГОЛОВНА СТОРІНКА ---
@router.get("/")
async def main_page(request: Request,
                    db: SessionDep,
                    current_user: User = Depends(get_token_from_cookie)):
    query = select(Url).where(Url.user_id == 1)
    result = await db.execute(query)
    urls = result.scalars().all()


    return templates.TemplateResponse("index.html", {"request": request,
                                                     "urls": urls,
                                                     "user": current_user}) # Потрібен для шапки сайту



# ---- Сторінка користувача ----
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
        request: Request,
        db: SessionDep):
        # Ми пробуємо дістати токен вручну, щоб не викликати помилку, якщо його немає

    token = request.cookies.get("access_token")

    # СЦЕНАРІЙ 1: Гість (немає токена)
    if not token:
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        # СЦЕНАРІЙ 2: Юзер (спробуємо розшифрувати токен)
        # Викликаємо нашого "Охоронця" вручну
        user = await get_current_user(token=token, db=db)

        # 👇 ЯКЩО УСПІХ - ДІСТАЄМО ПОСИЛАННЯ ЦЬОГО ЮЗЕРА
        # Шукаємо в таблиці Url, де user_id дорівнює id нашого юзера
        # Сортуємо: нові зверху (order_by desc)
        result = await db.execute(select(Url).where(Url.user_id == user.id).order_by(desc(Url.id)))
        user_urls = result.scalars().all()

        # Віддаємо Дашборд і передаємо туди список посилань (urls)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,  # Можна писати "Привіт, Вася"
            "urls": user_urls  # Список посилань для відображення
        })

    except Exception:
        # Якщо токен є, але він "протух" або битий -> показуємо вхід
        return templates.TemplateResponse("login.html", {"request": request})


# ----- Кнопка QR-code -----
@router.get("/qr/{key}")
async def generate_qr(key: str, request: Request):
    # 1. Формуємо повне посилання (наприклад http://127.0.0.1:8000/AbCd12)
    # request.base_url дає нам адресу сайту
    full_url = str(request.base_url) + key

    # 2. Малюємо QR-код
    # box_size=10 - розмір квадратиків, border=4 - біла рамка
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(full_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # 3. Зберігаємо картинку в "уявний файл" в оперативній пам'яті (RAM)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)  # Перемотуємо "плівку" на початок, щоб можна було читати

    # 4. Віддаємо картинку браузеру
    return StreamingResponse(buf, media_type="image/png")


#----- Створення посилання -----
# routers/web/pages.py
from typing import Optional  # 👈 Обов'язково додай цей імпорт зверху!
import validators


@router.post("/shorten")
async def create_url_web(
        request: Request,
        db: SessionDep,
        target_url: str = Form(...),
        custom_key: Optional[str] = Form(None),
        current_user: User = Depends(get_current_user)
):
    # 1. Дістаємо список (з .all(), щоб не було помилки 500)
    result = await db.scalars(select(Url).where(Url.user_id == current_user.id))
    urls = result.all()

    # 2. Перевірка самого посилання
    if not validators.url(target_url):
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "urls": urls,
            "user": current_user,
            "error": "❌ Некоректне посилання! (має бути https://...)"
        })

    # 3. ЛОГІКА ДЛЯ НАЗВИ (Key)
    key = ""

    if custom_key:
        # --- 🛡️ БЛОК ЗАХИСТУ (НОВЕ) ---

        # А. Перевірка на заборонені символи (Тільки букви, цифри, - та _)
        # Ніяких слешів /, пробілів, крапок!
        if not re.match(r"^[a-zA-Z0-9_-]+$", custom_key):
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "urls": urls,
                "user": current_user,
                "error": "⚠️ У назві не можна використовувати тире, підкреслення (_) та символи по-типу (/)."
            })

        # Б. Перевірка на зарезервовані слова (щоб не зламати сайт)
        reserved_words = ["admin", "login", "register", "dashboard", "api", "static", "docs", "redoc", "shorten",
                          "delete"]
        if custom_key.lower() in reserved_words:
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "urls": urls,
                "user": current_user,
                "error": f"⛔ Назва '{custom_key}' зарезервована системою. Вибери іншу."
            })

        # В. Перевірка на зайнятість в базі
        existing_link = await db.scalar(select(Url).where(Url.key == custom_key))
        if existing_link:
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "urls": urls,
                "user": current_user,
                "error": f"⛔ Назва '{custom_key}' вже зайнята! Спробуй іншу."
            })

        # Якщо пройшов всі кола пекла - дозволяємо
        key = custom_key

    else:
        # Генерація, якщо поле пусте
        key = generate_key()
        # (Тут теоретично теж треба перевіряти на дублікат, але шанс мізерний)

    # 4. Зберігаємо
    new_url = Url(
        key=key,
        target_url=target_url,
        user_id=current_user.id
    )

    db.add(new_url)
    await db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

#------ Отримання конкретного Url + добавлення Clicks ------
@router.get("/{key}")
async def get_urls(key: str,
                   db: SessionDep,
                   ):
    query = select(Url).where(Url.key == key)

    url_obj = get_or_404(await db.scalar(query), "Url not found")

    url_obj.clicks += 1

    #Створюємо запис в історії (для графіків)
    new_click = Click(url_id=url_obj.id)
    db.add(new_click)

    await db.commit()

    return RedirectResponse(url=url_obj.target_url)



#-------- Видалення посилання ------

@router.post("/delete/{key}")
async def delete_urls(
        key: str,
        db: SessionDep,
        current_user: User = Depends(get_current_user)):
    # 1. Шукаємо посилання
    query = select(Url).where(Url.key == key)
    url_obj = await db.scalar(query)

    if not url_obj:
        return RedirectResponse(url="/dashboard?error=not_found", status_code=303)

    if url_obj.user_id != current_user.id:
        return RedirectResponse(url="/dashboard?error=no_permission", status_code=303)

    # "Видалити з таблиці Click всі записи, де url_id дорівнює нашому id"
    await db.execute(delete(Click).where(Click.url_id == url_obj.id))

    # 3. Тепер спокійно видаляємо саме посилання
    await db.delete(url_obj)

    # 4. Зберігаємо зміни
    await db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

