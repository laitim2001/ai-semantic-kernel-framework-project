# =============================================================================
# IPA Platform - Base Classifier
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Abstract base class for intent classifiers.
# All classifiers must inherit from this class and implement the classify method.
#
# Dependencies:
#   - models (ExecutionMode, ClassificationResult, SessionContext)
# =============================================================================

from abc import ABC, abstractmethod
from typing import List, Optional

from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    Message,
    SessionContext,
)


class BaseClassifier(ABC):
    """
    Abstract base class for intent classifiers.

    All classifiers must inherit from this class and implement the classify method.
    Classifiers analyze user input and return a classification result with
    the detected execution mode and confidence level.

    Attributes:
        name: Unique name for the classifier
        weight: Weight for this classifier's result (0.0 to 1.0)
        enabled: Whether this classifier is enabled

    Example:
        >>> class MyClassifier(BaseClassifier):
        ...     async def classify(self, input_text, context, history):
        ...         return ClassificationResult(
        ...             mode=ExecutionMode.CHAT_MODE,
        ...             confidence=0.8,
        ...             reasoning="Simple question detected",
        ...             classifier_name=self.name
        ...         )
    """

    def __init__(
        self,
        name: str = "base",
        weight: float = 1.0,
        enabled: bool = True,
    ):
        """
        Initialize the classifier.

        Args:
            name: Unique name for the classifier
            weight: Weight for this classifier's result (0.0 to 1.0)
            enabled: Whether this classifier is enabled
        """
        self.name = name
        self.weight = weight
        self.enabled = enabled

    @abstractmethod
    async def classify(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> ClassificationResult:
        """
        Classify the input text and return a classification result.

        Args:
            input_text: The user input to classify
            context: Optional session context for additional information
            history: Optional conversation history

        Returns:
            ClassificationResult with the detected mode and confidence

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement classify()")

    def is_enabled(self) -> bool:
        """Check if the classifier is enabled."""
        return self.enabled

    def get_weight(self) -> float:
        """Get the classifier weight."""
        return self.weight

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, weight={self.weight}, enabled={self.enabled})>"
