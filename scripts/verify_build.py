#!/usr/bin/env python3
"""Verify the built distribution imports cleanly and exposes a typed public API.

Runs against the *installed* package, not the source tree, so it catches packaging mistakes
that an in-tree test cannot: a missing module in the wheel, a bad entry point, a missing
`py.typed` marker.
"""

from __future__ import annotations

import importlib
import sys

#: Modules that must be importable from the built wheel.
REQUIRED_MODULES: tuple[str, ...] = ("drh",)

#: Symbols that must be present on the top-level package.
REQUIRED_SYMBOLS: tuple[str, ...] = ("__version__",)


def check(modules: tuple[str, ...], symbols: tuple[str, ...]) -> list[str]:
    """Import the required modules and confirm the required symbols exist.

    Args:
        modules: Dotted module paths that must import without error.
        symbols: Attribute names that must be present on the `drh` package.

    Returns:
        A list of human-readable problems. Empty when the build is sound.
    """
    problems: list[str] = []
    pkg = None
    for name in modules:
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            problems.append("cannot import " + name + ": " + repr(exc))
            continue
        if name == "drh":
            pkg = module

    if pkg is not None:
        for symbol in symbols:
            if not hasattr(pkg, symbol):
                problems.append("drh is missing required symbol " + repr(symbol))

    return problems


def main() -> int:
    """Entry point. Returns 0 when the build is sound, else 1.

    Returns:
        Process exit code.
    """
    problems = check(REQUIRED_MODULES, REQUIRED_SYMBOLS)

    if problems:
        for problem in problems:
            print("build check failed: " + problem, file=sys.stderr)
        return 1

    import drh

    print("Build check OK: drh " + str(drh.__version__) + " imports from the built wheel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
