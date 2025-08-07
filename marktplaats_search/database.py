from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./data/marktplaats_api.db"

engine = create_async_engine(DATABASE_URL, echo=False) # Set echo=True for detailed SQL logging
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency to get a database session.
    Ensures the session is closed after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def create_db_and_tables():
    """
    Creates all database tables defined in models.py.
    """
    async with engine.begin() as conn:
        # For development, you might want to drop tables first
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
