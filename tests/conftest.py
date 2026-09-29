"""Shared pytest fixtures for the `drh` test suite.

Every fixture here is offline and deterministic. The suite must pass on a machine with no API
key and no network access, which is a hard requirement of the project (see DESIGN.md 3.4).
"""

from __future__ import annotations

import os

import pytest

#: Credential variables scrubbed for every test, so a locally exported key cannot make a
#: test silently reach a paid API and pass for the wrong reason.
CREDENTIAL_VARS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "COHERE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "DRH_PROVIDER_API_KEY",
)


@pytest.fixture(autouse=True)
def _forbid_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every provider credential from the environment for the whole test session.

    The CI gate (`scripts/assert_offline.py`) checks the CI environment. This fixture extends
    the same guarantee to local runs.

    Args:
        monkeypatch: pytest monkeypatch fixture used to mutate the environment.
    """
    for name in CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)
    leaked = [name for name in CREDENTIAL_VARS if os.environ.get(name)]
    assert not leaked, "credentials leaked into test environment: " + ", ".join(leaked)
