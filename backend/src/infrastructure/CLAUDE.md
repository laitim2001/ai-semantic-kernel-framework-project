# Infrastructure Layer

> Infrastructure layer — Database, Cache, Messaging (stub), Storage (empty)

---

## Directory Structure

```
infrastructure/
├── __init__.py
│
├── database/               # PostgreSQL integration (18 files) ✅ ACTIVE
│   ├── __init__.py
│   ├── session.py          # Database session management
│   ├── models/             # SQLAlchemy ORM models (8 files)
│   │   ├── base.py         # Base model class
│   │   ├── agent.py
│   │   ├── workflow.py
│   │   ├── execution.py
│   │   ├── checkpoint.py
│   │   ├── session.py
│   │   ├── audit.py
│   │   └── user.py
│   └── repositories/       # Data access layer (7 files)
│       ├── base.py         # BaseRepository (Generic CRUD)
│       ├── agent.py
│       ├── workflow.py
│       ├── execution.py
│       ├── checkpoint.py
│       ├── user.py
│       └── workflow.py
│
├── cache/                  # Redis integration (2 files) ✅ ACTIVE
│   ├── __init__.py
│   └── llm_cache.py        # LLM response caching
│
├── messaging/              # ⚠️ STUB — Only __init__.py exists
│   └── __init__.py         # Comment: "# Messaging infrastructure"
│
└── storage/                # ⚠️ EMPTY — No files or subdirectories
```

> **IMPORTANT**: `messaging/` and `storage/` are known gaps.
> - RabbitMQ integration is NOT implemented (only an empty __init__.py)
> - File storage layer does not exist yet
> - See Known Critical Issues in project memory

---

## Database Layer

### SQLAlchemy Model Template

```python
# models/example.py
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.infrastructure.database import Base


class ExampleModel(Base):
    """
    Example database model.

    Table: examples
    """
    __tablename__ = "examples"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Required fields
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False)

    # Optional fields
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Foreign keys
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = relationship("UserModel", back_populates="examples")
    items = relationship("ItemModel", back_populates="example", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Example(id={self.id}, name={self.name})>"
```

### Repository Pattern

```python
# repositories/base.py
from typing import Generic, TypeVar, List, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.

    Usage:
        class AgentRepository(BaseRepository[AgentModel]):
            def __init__(self, db: Session):
                super().__init__(db, AgentModel)
    """

    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        """Get single item by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[T]:
        """Get all items with optional filtering."""
        query = self.db.query(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)

        return query.offset(skip).limit(limit).all()

    def create(self, data: dict) -> T:
        """Create new item."""
        item = self.model(**data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, id: str, data: dict) -> T:
        """Update existing item."""
        item = self.get_by_id(id)
        if not item:
            raise ValueError(f"Item not found: {id}")

        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, id: str) -> None:
        """Delete item."""
        item = self.get_by_id(id)
        if item:
            self.db.delete(item)
            self.db.commit()

    def count(self, **filters) -> int:
        """Count items with optional filtering."""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.count()
```

### Custom Repository Example

```python
# repositories/agent_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.database.repositories.base import BaseRepository
from src.infrastructure.database.models.agent import AgentModel


class AgentRepository(BaseRepository[AgentModel]):
    """Repository for Agent model with custom queries."""

    def __init__(self, db: Session):
        super().__init__(db, AgentModel)

    def get_by_type(self, agent_type: str) -> List[AgentModel]:
        """Get all agents of a specific type."""
        return self.db.query(self.model).filter(
            self.model.type == agent_type
        ).all()

    def get_active_agents(self) -> List[AgentModel]:
        """Get all active agents."""
        return self.db.query(self.model).filter(
            self.model.status == "active"
        ).all()

    def search_by_name(self, name: str) -> List[AgentModel]:
        """Search agents by name (case-insensitive)."""
        return self.db.query(self.model).filter(
            self.model.name.ilike(f"%{name}%")
        ).all()
```

---

## Cache Layer

### Redis Client

```python
# cache/client.py
import redis
from typing import Optional, Any
import json

from src.core.config import settings


class RedisClient:
    """Redis client wrapper with common operations."""

    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self.client.get(key)

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value with TTL (default 1 hour)."""
        self.client.setex(key, ttl, value)

    def delete(self, key: str) -> None:
        """Delete key."""
        self.client.delete(key)

    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value."""
        value = self.get(key)
        return json.loads(value) if value else None

    def set_json(self, key: str, value: dict, ttl: int = 3600) -> None:
        """Set JSON value."""
        self.set(key, json.dumps(value), ttl)
```

### LLM Response Cache

```python
# cache/llm_cache.py
import hashlib
from typing import Optional

from src.infrastructure.cache.client import RedisClient


class LLMCache:
    """
    Cache for LLM responses to avoid duplicate API calls.

    Key format: llm:{model}:{hash(prompt)}
    TTL: 24 hours (default)
    """

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.default_ttl = 86400  # 24 hours

    def _make_key(self, model: str, prompt: str) -> str:
        """Generate cache key from model and prompt."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return f"llm:{model}:{prompt_hash}"

    def get(self, model: str, prompt: str) -> Optional[str]:
        """Get cached LLM response."""
        key = self._make_key(model, prompt)
        return self.redis.get(key)

    def set(self, model: str, prompt: str, response: str, ttl: Optional[int] = None) -> None:
        """Cache LLM response."""
        key = self._make_key(model, prompt)
        self.redis.set(key, response, ttl or self.default_ttl)

    def invalidate(self, model: str, prompt: str) -> None:
        """Invalidate cached response."""
        key = self._make_key(model, prompt)
        self.redis.delete(key)
```

---

## Messaging Layer

> **STATUS: NOT IMPLEMENTED** — Only `__init__.py` exists with a comment.

RabbitMQ is configured in Docker Compose (ports 5672/15672) but no Python publisher/consumer code exists. When implementing, follow this pattern:

```python
# messaging/publisher.py (TO BE IMPLEMENTED)
import pika
from src.core.config import settings

class MessagePublisher:
    """RabbitMQ message publisher. Queues: workflow.execute, notification.send, audit.log"""

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        self.channel = self.connection.channel()

    def publish(self, queue: str, message: dict) -> None:
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_publish(exchange="", routing_key=queue, body=json.dumps(message))
```

---

## Storage Layer

> **STATUS: NOT IMPLEMENTED** — Empty directory, no files.

File storage (for uploaded attachments, generated files) needs to be implemented.

---

## Best Practices

### Database

- Use migrations for schema changes (Alembic)
- Index frequently queried columns
- Use transactions for multi-step operations
- Handle connection pooling properly

### Cache

- Set appropriate TTLs
- Use cache invalidation strategically
- Don't cache sensitive data
- Handle cache misses gracefully

---

**Last Updated**: 2026-02-09
