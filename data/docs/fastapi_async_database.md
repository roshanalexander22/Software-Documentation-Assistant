---
doc_id: DOC-FA-009
title: Async Database Integration with SQLAlchemy 2.0 in FastAPI
version: v0.115
framework: FastAPI
category: Database
tags: [database, sqlalchemy, asyncpg, asyncsession, crud, modern]
source_url: https://fastapi.tiangolo.com/tutorial/sql-databases/
---

# Async Database Integration with SQLAlchemy 2.0 in FastAPI

Modern FastAPI applications leverage SQLAlchemy 2.0 with asynchronous drivers (such as `asyncpg` for PostgreSQL or `aiosqlite` for SQLite) to prevent database queries from blocking the ASGI event loop.

## Modern SQLAlchemy 2.0 Setup

```python
from typing import Annotated, AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select
from pydantic import BaseModel

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class ItemModel(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    description: Mapped[str]

# Dependency yielding async session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

app = FastAPI(title="Async DB Service", version="0.115.0")

class ItemCreate(BaseModel):
    title: str
    description: str

class ItemRead(ItemCreate):
    id: int

@app.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(item_in: ItemCreate, db: SessionDep):
    new_item = ItemModel(title=item_in.title, description=item_in.description)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item

@app.get("/items", response_model=list[ItemRead])
async def list_items(db: SessionDep):
    result = await db.execute(select(ItemModel))
    items = result.scalars().all()
    return items
```

## Best Practices
- Never use synchronous `Session` blocking calls inside an `async def` endpoint.
- Always configure `expire_on_commit=False` when using async SQLAlchemy to prevent detached instance lazy load errors.
- Wrap session handling in an async generator with `try...finally` or `async with`.

