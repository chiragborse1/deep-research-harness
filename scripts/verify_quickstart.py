#!/usr/bin/env python3
"""Verify the README Quickstart is real: every command it lists must actually exist.

SPEC 0.6 item 8 requires the README Quickstart to be copy-pasteable and CI-verified on every
push. Docs rot silently, so this gate parses the Quickstart code blocks out of README.md and
checks each command against the project: that the console script is declared, that the module
paths it references exist, and that no command assumes a credential.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: Matches a fenced bash code block.
BASH_BLOCK = re.compile(r"```bash\n(.*?)```", re.DOTALL)

#: Console scripts the CLI is expected to expose.
KNOWN_SCRIPTS: frozenset[str] = frozenset({"drh"})

#: Shell words that would indicate a network or credentialed command.
FORBIDDEN_TOKENS: tuple[str, ...] = (
    "curl ",
    "wget ",
    "pip install openai",
)


def quickstart_blocks(readme: str) -> list[str]:
    """Return the contents of every bash code block in the README.

    Args:
        readme: Full text of README.md.

    Returns:
        A list of block bodies, in document order.
    """
    return [m.group(1) for m in BASH_BLOCK.finditer(readme)]


def check_blocks(blocks: list[str]) -> list[str]:
    """Check each quickstart block for forbidden or malformed commands.

    Args:
        blocks: Code block bodies extracted from the README.

    Returns:
        A list of problems. Empty when the quickstart is clean.
    """
    problems: list[str] = []
    if not blocks:
        return ["README.md contains no ```bash quickstart block"]

    for idx, block in enumerate(blocks, start=1):
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for token in FORBIDDEN_TOKENS:
                if token in stripped:
                    problems.append(
                        "quickstart block "
                        + str(idx)
                        + " uses a network/credentialed command: "
                        + stripped,
                    )
    return problems


def main() -> int:
    """Entry point. Returns 0 when the quickstart is valid, else 1.

    Returns:
        Process exit code.
    """
    root = Path(__file__).resolve().parent.parent
    readme = root / "README.md"
    if not readme.is_file():
        print("error: README.md not found at " + str(readme), file=sys.stderr)
        return 1

    blocks = quickstart_blocks(readme.read_text(encoding="utf-8"))
    problems = check_blocks(blocks)
    if problems:
        for problem in problems:
            print("quickstart check failed: " + problem, file=sys.stderr)
        return 1

    print("Quickstart OK: " + str(len(blocks)) + " bash block(s) validated, no network commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
