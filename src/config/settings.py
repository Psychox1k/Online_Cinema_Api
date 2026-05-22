from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_DB_PORT: int
    POSTGRES_DB: str

    SECRET_KEY_ACCESS: str
    SECRET_KEY_REFRESH: str
    JWT_SIGNING_ALGORITHM: str = "HS256"
    LOGIN_TIME_DAYS: int = 7

    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_HOST_USER: str
    EMAIL_HOST_PASSWORD: str

    S3_STORAGE_HOST: str
    S3_STORAGE_PORT: int
    S3_STORAGE_ACCESS_KEY: str
    S3_STORAGE_SECRET_KEY: str
    S3_BUCKET_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int



    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}")

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()