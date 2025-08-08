"""
Base CRUD operations and service patterns.
Provides reusable patterns for database operations to reduce boilerplate.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database_utils import DatabaseService

# Type variables for generic CRUD operations
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType], DatabaseService):
    """
    Base CRUD class with default methods to Create, Read, Update, Delete (CRUD).

    Generic class that provides standard database operations for any SQLAlchemy model.
    Reduces boilerplate code in API endpoints and ensures consistent error handling.
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int | UUID) -> ModelType | None:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_or_404(self, db: AsyncSession, id: int | UUID) -> ModelType:
        """Get a single record by ID or raise 404."""
        obj = await self.get(db, id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{self.model.__name__} not found"
            )
        return obj

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        """Get multiple records with pagination and optional filtering."""
        query = select(self.model)

        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def count(self, db: AsyncSession, filters: dict[str, Any] | None = None) -> int:
        """Count total records with optional filtering."""
        query = select(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

        result = await db.execute(query)
        return result.scalar()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in.dict()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: CreateSchemaType, owner_id: int
    ) -> ModelType:
        """Create a new record with owner relationship."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in.dict()
        obj_data["user_id"] = owner_id
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = (
                obj_in.model_dump(exclude_unset=True)
                if hasattr(obj_in, "model_dump")
                else obj_in.dict(exclude_unset=True)
            )

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int | UUID) -> ModelType:
        """Delete a record by ID."""
        obj = await self.get_or_404(db, id)
        await db.delete(obj)
        await db.commit()
        return obj

    async def get_by_owner(
        self, db: AsyncSession, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """Get records owned by a specific user."""
        if not hasattr(self.model, "user_id"):
            raise ValueError(f"{self.model.__name__} does not have user_id field")

        query = select(self.model).where(self.model.user_id == owner_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_owner_and_id(
        self, db: AsyncSession, *, id: int | UUID, owner_id: int
    ) -> ModelType | None:
        """Get a record by ID that belongs to specific owner."""
        if not hasattr(self.model, "user_id"):
            raise ValueError(f"{self.model.__name__} does not have user_id field")

        query = select(self.model).where(self.model.id == id, self.model.user_id == owner_id)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_by_owner_and_id_or_404(
        self, db: AsyncSession, *, id: int | UUID, owner_id: int
    ) -> ModelType:
        """Get a record by ID and owner or raise 404."""
        obj = await self.get_by_owner_and_id(db, id=id, owner_id=owner_id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{self.model.__name__} not found"
            )
        return obj


class CRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Higher-level service class that combines CRUD operations with business logic.

    Provides a service layer pattern that can be used by API endpoints
    to handle complex business operations while maintaining clean separation.
    """

    def __init__(
        self,
        crud: CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType],
        response_model: type[ResponseSchemaType],
    ):
        self.crud = crud
        self.response_model = response_model

    async def create_item(
        self, db: AsyncSession, item_data: CreateSchemaType, owner_id: int | None = None
    ) -> ResponseSchemaType:
        """Create a new item with optional owner."""
        if owner_id:
            db_obj = await self.crud.create_with_owner(db, obj_in=item_data, owner_id=owner_id)
        else:
            db_obj = await self.crud.create(db, obj_in=item_data)

        return self.response_model.model_validate(db_obj)

    async def get_item(self, db: AsyncSession, item_id: int | UUID) -> ResponseSchemaType:
        """Get a single item by ID."""
        db_obj = await self.crud.get_or_404(db, item_id)
        return self.response_model.model_validate(db_obj)

    async def get_items(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ResponseSchemaType]:
        """Get multiple items with pagination."""
        db_objs = await self.crud.get_multi(db, skip=skip, limit=limit, filters=filters)
        return [self.response_model.model_validate(obj) for obj in db_objs]

    async def update_item(
        self,
        db: AsyncSession,
        item_id: int | UUID,
        item_data: UpdateSchemaType,
        owner_id: int | None = None,
    ) -> ResponseSchemaType:
        """Update an existing item."""
        if owner_id:
            db_obj = await self.crud.get_by_owner_and_id_or_404(db, id=item_id, owner_id=owner_id)
        else:
            db_obj = await self.crud.get_or_404(db, item_id)

        updated_obj = await self.crud.update(db, db_obj=db_obj, obj_in=item_data)
        return self.response_model.model_validate(updated_obj)

    async def delete_item(
        self, db: AsyncSession, item_id: int | UUID, owner_id: int | None = None
    ) -> None:
        """Delete an item."""
        if owner_id:
            db_obj = await self.crud.get_by_owner_and_id_or_404(db, id=item_id, owner_id=owner_id)
        else:
            db_obj = await self.crud.get_or_404(db, item_id)

        await self.crud.delete(db, id=db_obj.id)

    async def get_user_items(
        self, db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 100
    ) -> list[ResponseSchemaType]:
        """Get all items for a specific user."""
        db_objs = await self.crud.get_by_owner(db, owner_id=owner_id, skip=skip, limit=limit)
        return [self.response_model.model_validate(obj) for obj in db_objs]
