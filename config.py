from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Налаштування, щоб читати з .env
    # extra="ignore" каже: "Якщо в .env є щось зайве, просто ігноруй, не падай з помилкою"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()