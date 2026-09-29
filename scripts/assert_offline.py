#!/usr/bin/env python3
"""Assert that no LLM provider credential is present in the environment.

The suite must pass on a machine with no API key (SPEC 0.5). This script turns that
requirement into a CI gate that fails loudly and by name, instead of a test that quietly
skips because a key happens to exist on the runner.

It is a hard failure, not a skip: a credential in the environment means CI is not proving
what it claims to prove.
"""

from __future__ import annotations

import os
import sys

#: Environment variables that would let a test silently reach a paid API.
CREDENTIAL_VARS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "COHERE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "TOGETHER_API_KEY",
    "REPLICATE_API_TOKEN",
    "DRH_PROVIDER_API_KEY",
)


def present_credentials(environ: dict[str, str] | None = None) -> list[str]:
    """Return the credential variables that are set to a non-empty value.

    Args:
        environ: Environment mapping to inspect. Defaults to `os.environ`.

    Returns:
        Names of credential variables holding a non-empty value, sorted.
    """
    env = os.environ if environ is None else environ
    return sorted(name for name in CREDENTIAL_VARS if env.get(name, "").strip())


def main() -> int:
    """Entry point. Returns 0 when the environment is credential-free, else 1.

    Returns:
        Process exit code.
    """
    found = present_credentials()
    if found:
        print(
            "Offline guarantee violated: provider credentials are set in this environment.",
            file=sys.stderr,
        )
        for name in found:
            print("  " + name + " is set", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "CI must run the full suite against MockProvider with no network access.",
            file=sys.stderr,
        )
        print(
            "Unset these variables locally, or unset them in the workflow environment.",
            file=sys.stderr,
        )
        return 1

    print("Offline OK: none of " + str(len(CREDENTIAL_VARS)) + " credential variables are set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
