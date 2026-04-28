"""
L4b Decision Engine Contracts.

Sprint 116: Interface definitions for the decision/routing engine layer.
PatternMatcher, SemanticRouter, LLMClassifier implement these interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..contracts import RoutingRequest, RoutingResult


class RoutingLayerProtocol(ABC):
    """
    Protocol for individual routing layers.

    Each routing layer (Pattern, Semantic, LLM) implements this protocol.
    Layers are tried in priority order until one produces a confident match.
    """

    @abstractmethod
    async def classify(self, request: RoutingRequest) -> Optional[RoutingResult]:
        """
        Attempt to classify the request.

        Returns None if the layer cannot classify with sufficient confidence.

        Args:
            request: Normalized routing request

        Returns:
            RoutingResult if confident, None if not
        """
        ...

    @abstractmethod
    def get_layer_name(self) -> str:
        """Return the name of this routing layer."""
        ...

    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """Return the minimum confidence threshold for this layer."""
        ...


@dataclass
class LayerExecutionMetric:
    """Metrics for a single routing layer execution."""

    layer_name: str
    execution_time_ms: float
    confidence: float
    matched: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingPipelineResult:
    """
    Result from the complete routing pipeline.

    Contains the final result plus metrics from each layer attempted.
    """

    result: RoutingResult
    layers_attempted: List[LayerExecutionMetric] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def matched_layer(self) -> Optional[str]:
        """Get the name of the layer that produced the match."""
        for layer in self.layers_attempted:
            if layer.matched:
                return layer.layer_name
        return None

    @property
    def layers_tried_count(self) -> int:
        """Get the number of layers that were attempted."""
        return len(self.layers_attempted)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "result": self.result.to_dict(),
            "layers_attempted": [
                {
                    "layer_name": lm.layer_name,
                    "execution_time_ms": round(lm.execution_time_ms, 2),
                    "confidence": round(lm.confidence, 3),
                    "matched": lm.matched,
                }
                for lm in self.layers_attempted
            ],
            "total_time_ms": round(self.total_time_ms, 2),
            "matched_layer": self.matched_layer,
        }


class DecisionEngineProtocol(ABC):
    """
    Protocol for the complete Decision Engine (L4b).

    Orchestrates the routing pipeline across multiple layers.
    """

    @abstractmethod
    async def route(self, request: RoutingRequest) -> RoutingPipelineResult:
        """
        Execute the full routing pipeline.

        Tries layers in priority order (Pattern -> Semantic -> LLM)
        until one produces a confident match.

        Args:
            request: Normalized routing request from L4a

        Returns:
            RoutingPipelineResult with decision and metrics
        """
        ...

    @abstractmethod
    def get_pipeline_config(self) -> Dict[str, Any]:
        """
        Get current pipeline configuration.

        Returns:
            Dictionary with layer configurations
        """
        ...
