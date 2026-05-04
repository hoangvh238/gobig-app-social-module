from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    app_port: int = 8001
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # External services
    storage_service_url: str
    upload_service_url: str  # Media upload service
    celery_broker_url: str
    elasticsearch_url: str
    es_story_index: str = "gobig_stories"

    # Story config
    story_max_size_bytes: int = 52_428_800  # 50MB
    story_ttl_days: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
