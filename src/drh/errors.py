"""Typed exception hierarchy for the research harness.

Every failure mode in a long-horizon run is something an operator has to act on, so errors
carry the context needed to act: which run, which step, what was attempted, and whether a
retry is worth attempting. A bare `Exception("something went wrong")` at hour three of a run
is worse than a crash, because it hides the fact that the run is stuck.

The hierarchy is rooted at :class:`DrhError` so a caller can catch everything this library
raises with one `except` clause, while still distinguishing a transient network blip
(retryable) from a policy rejection (not retryable). That distinction drives the executor's
retry policy, so it is part of the type contract rather than a naming convention.

Every error is serializable via :meth:`DrhError.to_dict` and reconstructable via
:meth:`DrhError.from_dict`, because a crashed worker may be resumed in a different process and
the error has to survive that boundary.
"""

from __future__ import annotations

from typing import Any, ClassVar

__all__ = [
    "BudgetExceededError",
    "ClaimVerificationError",
    "ConfigurationError",
    "ContentTooLargeError",
    "DrhError",
    "IdempotencyConflictError",
    "IllegalTransitionError",
    "LedgerError",
    "ProviderError",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "RunNotFoundError",
    "SandboxPolicyError",
    "StateCorruptionError",
    "StepFailedError",
    "StepNotFoundError",
    "ToolError",
    "ToolNotFoundError",
    "ToolRejectedError",
    "ToolTimeoutError",
]


class DrhError(Exception):
    """Base class for every error raised by this library.

    Carries optional structured context so callers can react programmatically instead of
    parsing message text. Subclasses set :attr:`retryable` to declare whether retrying the
    same operation could plausibly succeed.
    """

    #: Whether retrying the operation that raised this error is sensible. Set per subclass.
    retryable: ClassVar[bool] = False

    def __init__(self, message: str, **context: Any) -> None:
        """Initialize the error with a message and optional structured context.

        Args:
            message: Human-readable description of what failed. Should say what was
                attempted and why it did not work, not merely name the exception.
            **context: Additional structured detail. Must be JSON-serializable.
        """
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, Any] = dict(context)

    def __str__(self) -> str:
        """Render the message with any structured context appended.

        Returns:
            The message alone when there is no context, otherwise the message followed by
            the context rendered as sorted `key=value` pairs.
        """
        if not self.context:
            return self.message
        rendered = ", ".join(f"{key}={value!r}" for key, value in sorted(self.context.items()))
        return f"{self.message} ({rendered})"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error for transport across a process boundary.

        A crashed worker may be resumed in a different process, so an error raised near the
        point of failure has to survive that boundary in a reconstructable form.

        Returns:
            A JSON-serializable dict with the exception class name, message, retryability,
            and structured context.
        """
        return {
            "error": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DrhError:
        """Reconstruct an error previously serialized by :meth:`to_dict`.

        Args:
            payload: A mapping produced by :meth:`to_dict`.

        Returns:
            An instance of the recorded exception class. Falls back to :class:`DrhError` when
            the recorded class name is not a known subclass, so a payload written by a newer
            version still deserializes rather than raising during recovery.
        """
        error_name = str(payload.get("error", ""))
        candidate = globals().get(error_name)
        if not (isinstance(candidate, type) and issubclass(candidate, DrhError)):
            candidate = DrhError
        message = str(payload.get("message", ""))
        raw_context = payload.get("context", {})
        context: dict[str, Any] = raw_context if isinstance(raw_context, dict) else {}
        return candidate(message, **context)


class ConfigurationError(DrhError):
    """Raised when configuration is missing, malformed, or internally inconsistent.

    Not retryable: the same configuration fails the same way every time, and retrying only
    delays surfacing the error the operator needs to see.
    """


class RunNotFoundError(DrhError):
    """Raised when a run id does not exist in the store."""


class StepNotFoundError(DrhError):
    """Raised when a step id does not exist within a run."""


class StateCorruptionError(DrhError):
    """Raised when persisted state is internally inconsistent.

    Deliberately distinct from an ordinary error: it means the durable store itself cannot be
    trusted, so a run in this state must not be resumed as though it were healthy. Recovery
    requires operator action, not a retry.
    """


class IllegalTransitionError(DrhError):
    """Raised when a state transition is not permitted from the current state.

    Carries both states so the caller can see what was attempted and what was expected, which
    is the difference between a diagnosable bug and a mystery.
    """

    def __init__(self, run_id: str, from_state: str, to_state: str) -> None:
        """Initialize with the run id and the attempted transition.

        Args:
            run_id: Identifier of the run whose transition was rejected.
            from_state: The state the run is actually in.
            to_state: The state the caller tried to move to.
        """
        super().__init__(
            "illegal transition " + from_state + " -> " + to_state,
            run_id=run_id,
            from_state=from_state,
            to_state=to_state,
        )


class IdempotencyConflictError(DrhError):
    """Raised when an idempotency key is reused for a materially different operation.

    Replaying a key with identical inputs is the normal crash-recovery path and returns the
    prior result. Reusing it for *different* inputs means two callers believe they own the
    same side effect, which is a correctness bug rather than a retry, so it raises instead of
    silently returning the wrong result.
    """


class StepFailedError(DrhError):
    """Raised when a step reaches a terminal failure state.

    Carries the underlying cause so the failure is diagnosable from the run record alone,
    rather than requiring the original stack trace to have been captured elsewhere.
    """

    def __init__(self, run_id: str, step_id: str, cause: BaseException) -> None:
        """Initialize with the failing step and its underlying cause.

        Args:
            run_id: Identifier of the run the step belongs to.
            step_id: Identifier of the step that failed.
            cause: The exception that caused the failure.
        """
        super().__init__(
            "step " + step_id + " failed: " + str(cause),
            run_id=run_id,
            step_id=step_id,
            cause_type=type(cause).__name__,
        )
        self.step_id: str = step_id
        self.cause: BaseException = cause


class BudgetExceededError(DrhError):
    """Raised when a run exceeds its configured token, cost, or wall-clock budget.

    Not retryable. A run that has blown its budget must halt visibly rather than continue
    spending.
    """


class ProviderError(DrhError):
    """Base class for model-access failures."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider endpoint is unreachable or returns a retryable status.

    Retryable: connection resets, timeouts, and 5xx responses are transient conditions a later
    attempt may well survive.
    """

    retryable: ClassVar[bool] = True


class ProviderResponseError(ProviderError):
    """Raised when a provider returns a response that cannot be interpreted.

    Covers malformed JSON, a missing expected field, or a refusal where a completion was
    required. Not retryable in general, because a deterministic prompt that produced garbage
    will usually produce garbage again.
    """


class ToolError(DrhError):
    """Base class for tool-execution failures."""


class ToolNotFoundError(ToolError):
    """Raised when a tool name is not registered."""


class ToolRejectedError(ToolError):
    """Raised when the sandbox policy refuses a tool invocation.

    Covers allowlist misses, path-jail escapes, and content-type rejections. Not retryable: the
    same call is refused for the same reason every time, and retrying would be an attempt to
    work around a control that exists deliberately.
    """


class ToolTimeoutError(ToolError):
    """Raised when a tool exceeds its deadline.

    Retryable, because a tool that timed out on a slow network may succeed on a later attempt.
    The run stays resumable either way.
    """

    retryable: ClassVar[bool] = True


class ContentTooLargeError(ToolError):
    """Raised when content exceeds the configured cap and cannot be stored as a reference.

    Distinct from a policy rejection: the content is permitted, it is simply too large to
    handle, which is a different problem with a different fix.
    """


class SandboxPolicyError(DrhError):
    """Raised when a sandbox configuration is invalid or self-contradictory.

    Raised at construction time rather than at invocation time, so a misconfigured sandbox
    fails immediately instead of at the first tool call hours into a run.
    """


class LedgerError(DrhError):
    """Base class for veracity-ledger failures."""


class ClaimVerificationError(LedgerError):
    """Raised when a claim cannot be verified against its cited evidence.

    This is for a *failed* verification, not an absent one. A claim with no evidence is
    recorded as `UNSUPPORTED` and carried through to the report, because hiding an
    unsupported claim is precisely the failure mode this project exists to prevent.
    """
