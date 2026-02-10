from typing import List

from fastapi import HTTPException, Request, Depends

from fastapi import APIRouter
from models import models
from schemas.schemas import UrlCreate, UrlInfo
from database.db import SessionDep
from generatkey.utils import generate_key
from models.models import Url, User
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload
from collections import Counter # Щоб зручно рахувати кліки

from routers.api.auth import get_current_user

from models.models import Url, Click
from routers.api.auth import get_current_user_api


router = APIRouter(tags=["API"])



# ------ Обробка 404 -----
def get_or_404(obj, message="Not found"):
    if obj is None:
        raise HTTPException(status_code=404, detail=message)
    return obj


#------ Перевірка користувача -----
def check_owner(obj_user_id: int, current_user_id: int):
    if obj_user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this action"
        )



# ------- Створення Url Json-формат ------
@router.post("/urls", response_model=UrlInfo)
async def create_urls(url_data: UrlCreate,
                      db: SessionDep,
                      request: Request,
                      current_user: User = Depends(get_current_user_api)):

    key = generate_key()

    # Створюємо об'єкт моделі
    # url_data.target_url - це об'єкт HttpUrl, тому перетворюємо його в str
    new_url = models.Url(
        key=key,
        target_url=str(url_data.target_url),
        user_id=current_user.id,
    )

    db.add(new_url)
    await db.commit()
    await db.refresh(new_url)

    # формування повного посилання
    # request.base_url поверне "http://127.0.0.1:8000/"
    new_url.short_url = str(request.base_url) + key

    return new_url


#------ Отримання всіх Urls ------
@router.get("/all_urls", response_model=List[UrlInfo])
async def get_all_short_urls(db:SessionDep,
                             request: Request,
                             ):
    query = select(Url).order_by(Url.key)
    result = await db.execute(query)
    urls = result.scalars().all()

    # 👇 2. Проходимо по кожному посиланню і "домальовуємо" адресу
    for url in urls:
        url.short_url = str(request.base_url) + url.key

    return urls




#----- Отримання інформацію про Url -------
@router.get("/urls/{key}")
async def get_curr_url(key: str,
                       db: SessionDep,
                       ):
    query = select(Url).where(Url.key == key)

    url_obj = get_or_404(await db.scalar(query), "Url not found")

    return url_obj


#------- Put-оновлення -------
@router.put("/{key}")
async def put_urls(db: SessionDep,
                   key: str,
                   url_data: UrlCreate,
                   current_user: User = Depends(get_current_user_api)):

    query = select(Url).where(Url.key == key)

    url_to_edit = (await db.execute(query)).scalar_one_or_none()

    get_or_404(url_to_edit, message="Not found")
    check_owner(url_to_edit.user_id, current_user.id)

    url_to_edit.target_url = str(url_data.target_url)

    await db.commit()
    await db.refresh(url_to_edit)

    return url_to_edit


#------- Delete key -------
@router.delete("/{key}")
async def delete_urls(key: str,
                      db: SessionDep,
                      current_user: User = Depends(get_current_user_api)):

    query =select(Url).where(Url.key == key)

    result = await db.scalar(query)

    get_or_404(result, message="Not found")
    check_owner(result.user_id, current_user.id)

    await db.delete(result)
    await db.commit()

    return {'message':f'Url {key} deleted'}



#------- Кнопка статистики в Dashboard -------
@router.get("/stats/{key}")
async def get_stats_json(key: str, db: SessionDep):
    # 1. Шукаємо посилання в базі разом з історією
    query = select(Url).where(Url.key == key).options(selectinload(Url.click_history))
    url_obj = await db.scalar(query)

    # Якщо посилання не знайдено - віддаємо помилку в форматі JSON
    if not url_obj:
        return JSONResponse({"error": "Link not found"}, status_code=404)

    # 2. Обробка даних (так само як було, але для таблиці)
    dates = [click.created_at.strftime("%Y-%m-%d") for click in url_obj.click_history]
    counts = Counter(dates)

    # Сортуємо: reverse=True означає "від нових до старих" (щоб вчора було вище, ніж позавчора)
    sorted_dates = sorted(counts.keys(), reverse=True)

    # 3. Формуємо список словників для таблиці
    stats_list = []
    for date in sorted_dates:
        stats_list.append({
            "date": date,
            "count": counts[date]
        })

    # 4. Віддаємо чистий JSON
    return JSONResponse(stats_list)