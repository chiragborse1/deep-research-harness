#!/usr/bin/env python3
"""Fail if any public symbol in `src/drh` lacks a docstring.

This is the mechanical half of SPEC 0.6 item 4 (public API carries docstrings and typed
signatures). A gate is the cheapest way to keep that from decaying as the surface grows: it
fails the build instead of relying on reviewer memory.

"Public" is defined structurally, not by a naming convention: a module-level class,
function, or method that does not start with a single underscore, plus every module
docstring.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

#: Decorator names that mark a function as intentionally undocumented.
EXEMPT_DECORATORS: frozenset[str] = frozenset({"overload"})

#: Module-level names exempted from the docstring requirement.
EXEMPT_NAMES: frozenset[str] = frozenset({"__all__", "annotations"})


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    """Report whether a definition node carries its own docstring.

    Args:
        node: A parsed function, async function, or class definition.

    Returns:
        True when the node has a non-empty docstring.
    """
    return ast.get_docstring(node) is not None


def _is_exempt(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Report whether a function is exempt via an `@overload` decorator.

    Args:
        node: A parsed function definition.

    Returns:
        True when any decorator is in `EXEMPT_DECORATORS`.
    """
    return any(
        (isinstance(d, ast.Name) and d.id in EXEMPT_DECORATORS)
        or (isinstance(d, ast.Attribute) and d.attr in EXEMPT_DECORATORS)
        for d in node.decorator_list
    )


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return every undocumented public symbol in one file.

    Args:
        path: Python source file to inspect.

    Returns:
        A list of `(line_number, symbol_description)` tuples, sorted by line number.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[tuple[int, str]] = []

    if ast.get_docstring(tree) is None:
        missing.append((1, "module docstring"))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") or node.name in EXEMPT_NAMES or _is_exempt(node):
                continue
            if not _has_docstring(node):
                missing.append((node.lineno, "function " + node.name))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_") or node.name in EXEMPT_NAMES:
                continue
            if not _has_docstring(node):
                missing.append((node.lineno, "class " + node.name))
            # Methods of an undocumented class are still public, so they are checked too.
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name.startswith("_") or _is_exempt(sub):
                        continue
                    if not _has_docstring(sub):
                        label = "method " + node.name + "." + sub.name
                        missing.append((sub.lineno, label))
    return sorted(missing)


def main() -> int:
    """Entry point. Returns 0 when every public symbol is documented, else 1.

    Returns:
        Process exit code.
    """
    src = Path(__file__).resolve().parent.parent / "src"
    if not src.is_dir():
        print("error: expected source root at " + str(src), file=sys.stderr)
        return 1

    total = 0
    for p in sorted(src.rglob("*.py")):
        missing = check_file(p)
        if not missing:
            continue
        rel = p.relative_to(src.parent)
        for line, what in missing:
            print(str(rel) + ":" + str(line) + ": missing docstring for " + what, file=sys.stderr)
        total += len(missing)

    if total:
        print("", file=sys.stderr)
        print("Found " + str(total) + " undocumented public symbol(s).", file=sys.stderr)
        return 1

    print("Docstrings OK: every public symbol under " + str(src) + " is documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
