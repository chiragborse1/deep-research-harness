"""Long-horizon research agent harness.

`drh` provides the durable execution substrate for research agents that must run for
hours rather than minutes: crash-consistent run state, sandboxed tool execution,
provider-agnostic model access, and a veracity ledger that ties every claim to evidence.

Nothing in this package imports a vendor LLM SDK. All model access goes through
:class:`drh.providers.Provider`.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
