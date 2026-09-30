"""Connected, versioned business context and safe analytical execution.

No model calls, warehouse connections or source mutations occur on import.
"""

from .store import ContextError, Store

__all__ = ["ContextError", "Store"]
