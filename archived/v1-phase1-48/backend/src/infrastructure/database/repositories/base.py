# =============================================================================
# IPA Platform - Base Repository
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Abstract base repository providing common CRUD operations.
# All concrete repositories should inherit from this class.
# =============================================================================

from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.base import Base


# Type variable for model classes
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Abstract base repository with common CRUD operations.

    Provides generic implementation for:
        - create: Insert new record
        - get: Retrieve by ID
        - get_by: Retrieve by arbitrary field
        - list: Paginated list with filtering
        - update: Update existing record
        - delete: Remove record

    Type Parameters:
        ModelT: SQLAlchemy model class

    Example:
        class AgentRepository(BaseRepository[Agent]):
            model = Agent
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get(self, id: UUID) -> Optional[ModelT]:
        """
        Get a record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        return await self._session.get(self.model, id)

    async def get_by(self, **kwargs: Any) -> Optional[ModelT]:
        """
        Get a record by arbitrary field values.

        Args:
            **kwargs: Field name and value pairs

        Returns:
            First matching model instance or None
        """
        stmt = select(self.model).filter_by(**kwargs)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        **filters: Any,
    ) -> Tuple[List[ModelT], int]:
        """
        List records with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of records per page
            order_by: Field name to order by
            order_desc: Whether to order descending
            **filters: Field filters (exact match)

        Returns:
            Tuple of (list of records, total count)
        """
        # Base query
        stmt = select(self.model)

        # Apply filters
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.filter(getattr(self.model, field) == value)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_desc:
                stmt = stmt.order_by(order_column.desc())
            else:
                stmt = stmt.order_by(order_column)
        elif hasattr(self.model, "created_at"):
            # Default to created_at desc
            stmt = stmt.order_by(self.model.created_at.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(self, id: UUID, **kwargs: Any) -> Optional[ModelT]:
        """
        Update an existing record.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get(id)
        if instance is None:
            return None

        for field, value in kwargs.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get(id)
        if instance is None:
            return False

        await self._session.delete(instance)
        await self._session.flush()
        return True

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        instance = await self.get(id)
        return instance is not None

    async def count(self, **filters: Any) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Field filters (exact match)

        Returns:
            Number of matching records
        """
        stmt = select(func.count()).select_from(self.model)

        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.filter(getattr(self.model, field) == value)

        result = await self._session.execute(stmt)
        return result.scalar() or 0
