"""Tests for the typed exception hierarchy.

The hierarchy carries two contracts that callers depend on: the `retryable` flag drives the
executor's retry policy, and `to_dict`/`from_dict` round-trips let an error survive a process
boundary during crash recovery. Both are tested here, the second with property-based tests
because a lossy round-trip would silently corrupt recovery.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from drh.errors import (
    BudgetExceededError,
    ClaimVerificationError,
    ConfigurationError,
    ContentTooLargeError,
    DrhError,
    IdempotencyConflictError,
    IllegalTransitionError,
    LedgerError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
    RunNotFoundError,
    SandboxPolicyError,
    StateCorruptionError,
    StepFailedError,
    StepNotFoundError,
    ToolError,
    ToolNotFoundError,
    ToolRejectedError,
    ToolTimeoutError,
)

#: Every concrete error class, used to assert the hierarchy is complete and rooted.
ALL_ERRORS: tuple[type[DrhError], ...] = (
    ConfigurationError,
    RunNotFoundError,
    StepNotFoundError,
    StateCorruptionError,
    IllegalTransitionError,
    IdempotencyConflictError,
    StepFailedError,
    BudgetExceededError,
    ProviderError,
    ProviderUnavailableError,
    ProviderResponseError,
    ToolError,
    ToolNotFoundError,
    ToolRejectedError,
    ToolTimeoutError,
    ContentTooLargeError,
    SandboxPolicyError,
    LedgerError,
    ClaimVerificationError,
)


@pytest.mark.parametrize("error_cls", ALL_ERRORS, ids=lambda c: c.__name__)
def test_every_error_descends_from_base(error_cls: type[DrhError]) -> None:
    """Every error is catchable with a single `except DrhError`."""
    assert issubclass(error_cls, DrhError)


def test_unknown_error_name_falls_back_to_base() -> None:
    """A payload naming an unknown class still deserializes rather than raising."""
    recovered = DrhError.from_dict(
        {"error": "SomeFutureError", "message": "boom", "context": {"k": "v"}}
    )
    assert type(recovered) is DrhError
    assert recovered.message == "boom"


def test_retryable_flags_are_correct() -> None:
    """Retryability matches the operational reality of each failure.

    These flags drive the executor retry loop, so a wrong value is a real behavioral bug:
    marking a policy rejection retryable burns retries on a deterministic failure, and
    marking a timeout non-retryable kills runs that would have recovered.
    """
    assert ProviderUnavailableError.retryable is True
    assert ToolTimeoutError.retryable is True
    assert ToolRejectedError.retryable is False
    assert ProviderResponseError.retryable is False
    assert BudgetExceededError.retryable is False


def test_illegal_transition_reports_both_states() -> None:
    """The transition error names both the actual and the attempted state."""
    err = IllegalTransitionError("run-1", "FETCH", "DONE")
    assert "FETCH" in str(err)
    assert "DONE" in str(err)
    assert err.context["from_state"] == "FETCH"
    assert err.context["to_state"] == "DONE"


def test_step_failed_preserves_cause() -> None:
    """`StepFailedError` keeps the original exception for post-mortem diagnosis."""
    cause = ValueError("underlying")
    err = StepFailedError("run-1", "step-3", cause)
    assert err.cause is cause
    assert err.step_id == "step-3"
    assert err.context["cause_type"] == "ValueError"


# --- Property-based: serialization round-trip -------------------------------

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**53), max_value=2**53),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=40),
)
json_values = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(min_size=1, max_size=8), children, max_size=4),
    ),
    max_leaves=12,
)
context_st = st.dictionaries(st.text(min_size=1, max_size=8), json_values, max_size=5)
messages = st.text(min_size=1, max_size=80)


@given(msg=messages, ctx=context_st)
def test_to_dict_from_dict_round_trips(msg: str, ctx: dict[str, object]) -> None:
    """A base error survives serialization without loss.

    Crash recovery may hand an error to a different process, so a lossy round-trip would
    corrupt the record of why a run failed.
    """
    original = DrhError(msg, **ctx)
    recovered = DrhError.from_dict(original.to_dict())
    assert type(recovered) is DrhError
    assert recovered.message == original.message
    assert recovered.context == original.context
    assert recovered.retryable == original.retryable


@given(msg=messages, ctx=context_st)
def test_to_dict_is_json_serializable(msg: str, ctx: dict[str, object]) -> None:
    """`to_dict` output is JSON-serializable for any valid context."""
    import json

    payload = json.dumps(DrhError(msg, **ctx).to_dict())
    assert json.loads(payload)["message"] == msg
