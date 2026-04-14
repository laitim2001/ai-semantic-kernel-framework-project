"""Expert Seeder — plants built-in YAML definitions into the database.

Called once during application startup. Idempotent — existing records
are not overwritten.

Sprint 163 — Phase 46 Agent Expert Registry.
"""

import logging
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.agent_expert import AgentExpertRepository

logger = logging.getLogger(__name__)

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"


async def seed_builtin_experts(session: AsyncSession) -> int:
    """Seed all YAML definitions into the database.

    Returns the number of newly created experts (0 if all already exist).
    """
    repo = AgentExpertRepository(session)
    created = 0

    if not _DEFINITIONS_DIR.is_dir():
        logger.warning("Expert definitions directory not found: %s", _DEFINITIONS_DIR)
        return 0

    yaml_files = sorted(_DEFINITIONS_DIR.glob("*.yaml"))
    for yaml_path in yaml_files:
        try:
            with open(yaml_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)

            if not isinstance(data, dict) or not data.get("name"):
                logger.warning("Skipping invalid YAML: %s", yaml_path)
                continue

            existing = await repo.get_by_name(data["name"])
            if existing is None:
                await repo.upsert_from_yaml(data)
                created += 1
                logger.debug("Seeded expert: %s", data["name"])
            else:
                logger.debug("Expert already exists: %s", data["name"])

        except Exception as exc:
            logger.warning("Failed to seed %s: %s", yaml_path.name, exc)

    await session.commit()
    logger.info("Expert seeder: %d new experts seeded from %d YAML files", created, len(yaml_files))
    return created
