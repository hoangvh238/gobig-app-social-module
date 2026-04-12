from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

database_url = settings.database_url.replace('localhost', '127.0.0.1')

engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600 
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
