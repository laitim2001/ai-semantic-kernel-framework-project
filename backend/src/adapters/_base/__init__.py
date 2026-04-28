"""adapters._base — ChatClient ABC + neutral types. See README.md."""

from adapters._base.chat_client import ChatClient, ModelInfo, PricingInfo, StreamEvent

__all__ = ["ChatClient", "ModelInfo", "PricingInfo", "StreamEvent"]
