from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    app_port: int = 8001

    class Config:
        env_file = ".env"


settings = Settings()
