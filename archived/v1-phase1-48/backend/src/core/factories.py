# =============================================================================
# IPA Platform - Service Factory
# =============================================================================
# Sprint 112: S112-2 - Environment-Aware Service Factory
# Phase 31: Security Hardening + Quick Wins
#
# Provides environment-aware service creation:
#   - production: Real implementations only, raises on failure
#   - development: Real preferred, WARNING + fallback to mock
#   - testing: Mock implementations directly
#
# Dependencies:
#   - Settings (src.core.config)
# =============================================================================

import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ServiceFactory:
    """Environment-aware service factory.

    Routes service creation to real or mock implementations based on
    the APP_ENV environment variable.

    - production/staging: Real only, raises RuntimeError on failure
    - development: Real preferred, falls back to mock with WARNING
    - testing: Mock directly

    Usage:
        ServiceFactory.register(
            "business_intent_router",
            real_factory=create_real_router,
            mock_factory=create_mock_router,
        )
        router = ServiceFactory.create("business_intent_router")
    """

    _registry: Dict[str, Dict[str, Optional[Callable]]] = {}

    @classmethod
    def register(
        cls,
        service_name: str,
        real_factory: Callable[..., Any],
        mock_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Register real and mock factories for a service.

        Args:
            service_name: Unique service identifier
            real_factory: Callable that creates the real implementation
            mock_factory: Callable that creates the mock implementation
        """
        cls._registry[service_name] = {
            "real": real_factory,
            "mock": mock_factory,
        }

    @classmethod
    def create(cls, service_name: str, **kwargs: Any) -> Any:
        """Create a service instance based on current environment.

        Args:
            service_name: Registered service name
            **kwargs: Passed to the factory callable

        Returns:
            Service instance (real or mock depending on environment)

        Raises:
            ValueError: If service_name is not registered
            RuntimeError: If real factory fails in production
        """
        env = os.environ.get("APP_ENV", "development")
        entry = cls._registry.get(service_name)

        if entry is None:
            raise ValueError(
                f"Unknown service: '{service_name}'. "
                f"Registered services: {list(cls._registry.keys())}"
            )

        real_factory = entry["real"]
        mock_factory = entry["mock"]

        # Testing environment: use mock directly
        if env == "testing" and mock_factory is not None:
            logger.debug(f"Creating mock {service_name} (testing environment)")
            return mock_factory(**kwargs)

        # Try real implementation first
        try:
            instance = real_factory(**kwargs)
            logger.info(f"Created real {service_name}")
            return instance
        except Exception as e:
            if env == "production":
                raise RuntimeError(
                    f"Failed to create {service_name} in production: {e}. "
                    f"Check environment variables and service dependencies."
                ) from e

            # Development fallback
            if mock_factory is not None:
                logger.warning(
                    f"Failed to create real {service_name} in {env}, "
                    f"falling back to mock. Error: {e}. "
                    f"This is NOT acceptable in production."
                )
                return mock_factory(**kwargs)

            raise RuntimeError(
                f"Failed to create {service_name} and no mock available: {e}"
            ) from e

    @classmethod
    def is_registered(cls, service_name: str) -> bool:
        """Check if a service is registered."""
        return service_name in cls._registry

    @classmethod
    def list_services(cls) -> list[str]:
        """List all registered service names."""
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations. For testing cleanup."""
        cls._registry.clear()

    @classmethod
    def get_environment(cls) -> str:
        """Get current environment setting."""
        return os.environ.get("APP_ENV", "development")


def register_orchestration_services() -> None:
    """Register orchestration services in ServiceFactory.

    Sprint 112: Centralizes mock/real factory registration.
    Mock factories use lazy imports from tests.mocks to avoid
    importing test code in production.

    Called during app startup (main.py lifespan).
    """
    from src.integrations.orchestration import (
        create_router,
        create_guided_dialog_engine,
        create_hitl_controller,
    )

    def _mock_router(**kwargs: Any) -> Any:
        from tests.mocks.orchestration import create_mock_router
        return create_mock_router(**kwargs)

    def _mock_dialog_engine(**kwargs: Any) -> Any:
        from tests.mocks.orchestration import create_mock_dialog_engine
        return create_mock_dialog_engine(**kwargs)

    def _mock_hitl_controller(**kwargs: Any) -> Any:
        from tests.mocks.orchestration import create_mock_hitl_controller
        controller, _, _ = create_mock_hitl_controller(**kwargs)
        return controller

    ServiceFactory.register(
        "business_intent_router",
        real_factory=create_router,
        mock_factory=_mock_router,
    )
    ServiceFactory.register(
        "guided_dialog_engine",
        real_factory=create_guided_dialog_engine,
        mock_factory=_mock_dialog_engine,
    )
    ServiceFactory.register(
        "hitl_controller",
        real_factory=create_hitl_controller,
        mock_factory=_mock_hitl_controller,
    )

    logger.info(
        f"Registered {len(ServiceFactory.list_services())} orchestration services"
    )
