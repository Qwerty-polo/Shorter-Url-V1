import os
from datetime import timedelta, timezone, datetime

import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


#deprecated auto - якшо хтось зайде з страим типом хешу він переробиця автоматично на найновіший
#schema це алгоритм за яким ми шифруємо може бути sha256, або md5 (це старіші)
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')

def create_access_token(data: dict, expires_delta: timedelta):
    #робимо копію даних шоб не зіпсувати оригінал
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 3. Додаємо цей час у дані
    to_encode.update({'exp': expire})

    # 4. Шифруємо все це у рядок
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return encoded_jwt


def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(user_unhashed_password: str, hashed_password: str):
    return pwd_context.verify(user_unhashed_password, hashed_password)
