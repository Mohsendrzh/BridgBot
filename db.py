import logging
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot_database.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(nullable=True)
    state: Mapped[Optional[str]] = mapped_column(nullable=True) 
    created_at: Mapped[datetime]

class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int]
    title: Mapped[str]
    created_at: Mapped[datetime]


async def init_db():
    """Initializes the database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized with SQLAlchemy.")

async def set_user_state(telegram_id: int, state: Optional[str]):
    """Updates or sets the user's state."""
    async with AsyncSessionLocal() as session:
        now = datetime.now()

        stmt = sqlite_insert(User).values(
            telegram_id=telegram_id,
            state=state,
            created_at=now
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['telegram_id'],
            set_=dict(state=state)
        )
        await session.execute(stmt)
        await session.commit()

async def get_user_state(telegram_id: int) -> Optional[str]:
    """Gets the current state of the user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.state).where(User.telegram_id == telegram_id)
        )
        return result.scalars().first()

async def register_user_email(telegram_id: int, email: str):
    """Saves email and clears state."""
    async with AsyncSessionLocal() as session:
        stmt = sqlite_insert(User).values(
            telegram_id=telegram_id,
            email=email,
            created_at=datetime.now()
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['telegram_id'],
            set_=dict(email=email, state=None)
        )
        await session.execute(stmt)
        await session.commit()

async def add_task(telegram_id: int, title: str):
    """Adds a task and clears state."""
    async with AsyncSessionLocal() as session:
        new_task = Task(
            telegram_id=telegram_id,
            title=title,
            created_at=datetime.now()
        )
        session.add(new_task)
        
        await session.execute(
            sqlite_insert(User).values(
                telegram_id=telegram_id, 
                state=None, 
                created_at=datetime.now()
            )
            .on_conflict_do_update(index_elements=['telegram_id'], set_=dict(state=None))
        )
        
        await session.commit()

async def get_user_tasks(telegram_id: int) -> List[str]:
    """Retrieves all task titles."""
    async with AsyncSessionLocal() as session:
        stmt = select(Task.title).where(Task.telegram_id == telegram_id).order_by(Task.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())