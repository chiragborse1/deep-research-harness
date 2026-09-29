#!/usr/bin/env python3
"""Fail if a vendor LLM SDK is imported anywhere in the core library.

This is the mechanical half of the endpoint-independence requirement (SPEC 0.5). The
architectural half is the `drh.providers.Provider` trait; this script is the guard rail
that stops the trait from quietly eroding as adapters get added.

Only `src/` is scanned. Adapters speak plain HTTP via `httpx`, so a vendor SDK in core
would mean someone bypassed the trait rather than implemented it.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

#: Import roots that constitute a hardcoded vendor dependency.
FORBIDDEN: frozenset[str] = frozenset(
    {
        "openai",
        "anthropic",
        "google",  # covers google.generativeai and google.genai
        "cohere",
        "mistralai",
        "groq",
        "together",
        "replicate",
        "litellm",  # a router, not a provider; banned for the same reason as the rest
        "langchain",
        "langchain_core",
        "llama_index",
    }
)


def _root_of(module: str) -> str:
    """Return the top-level import root for a dotted module path.

    Args:
        module: A dotted module path as written in an `import` statement.

    Returns:
        The first dotted component of `module`.
    """
    return module.split(".", 1)[0]


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return every forbidden import in a single source file.

    The file is parsed with `ast` rather than grepped, so a vendor name appearing in a
    docstring, comment, or string literal does not produce a false positive.

    Args:
        path: Python source file to inspect.

    Returns:
        A list of `(line_number, module_name)` tuples for forbidden imports, sorted by
        line number. Empty when the file is clean.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [(exc.lineno or 0, "<unparseable: " + exc.msg + ">")]

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            # `from google import genai` yields module="google"; a relative import has level>0.
            names.append(node.module)
        for name in names:
            if _root_of(name) in FORBIDDEN:
                found.append((node.lineno, name))
    return sorted(found)


def scan_tree(src: Path) -> list[tuple[Path, int, str]]:
    """Scan every Python file under `src` for forbidden imports.

    Args:
        src: The source root to scan recursively.

    Returns:
        A list of `(path, line_number, module_name)` for every violation found.
    """
    violations: list[tuple[Path, int, str]] = []
    for p in sorted(src.rglob("*.py")):
        violations.extend((p, line, mod) for line, mod in scan_file(p))
    return violations


def main() -> int:
    """Entry point. Returns 0 when clean, 1 when a violation is present.

    Returns:
        Process exit code.
    """
    src = Path(__file__).resolve().parent.parent / "src"
    if not src.is_dir():
        print("error: expected source root at " + str(src), file=sys.stderr)
        return 1

    violations = scan_tree(src)
    if violations:
        print(
            "Endpoint independence violated: vendor SDK imported in core library code.",
            file=sys.stderr,
        )
        for p, line, mod in violations:
            rel = p.relative_to(src.parent)
            print("  " + str(rel) + ":" + str(line) + ": imports " + repr(mod), file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "All model access must go through drh.providers.Provider. Adapters should",
            file=sys.stderr,
        )
        print(
            "speak plain HTTP through httpx, exactly as the shipped adapters do.", file=sys.stderr
        )
        return 1

    print("Endpoint independence OK: no vendor SDK imports under " + str(src) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
