"""Command-line entry point for the research harness.

This module exists in the scaffold PR so the console script and the `make demo` target are
wired up and CI can verify packaging end to end. Subcommands are added incrementally by later
PRs; each stays a thin shell over library code so the CLI remains testable.
"""

from __future__ import annotations

import argparse
import sys

from drh import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    Returns:
        A parser carrying the global flags and every registered subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="drh",
        description=(
            "Long-horizon research agent harness: durable runs, sandboxed tools, "
            "and a veracity ledger for every claim."
        ),
        epilog=(
            "Every command runs offline by default and needs no API key. "
            "Point it at a real model with --provider and --model."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="drh " + __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    demo = sub.add_parser(
        "demo",
        help="Run the offline end-to-end demo (no API key required).",
        description=(
            "Execute a complete research run against the deterministic MockProvider "
            "and print real measured output."
        ),
    )
    demo.set_defaults(func=cmd_demo)

    return parser


def cmd_demo(_args: argparse.Namespace) -> int:
    """Run the offline end-to-end demo.

    Args:
        _args: Parsed command-line arguments. The scaffold demo reads none of them yet;
            the leading underscore marks the deliberately unused parameter so lint does
            not flag it. Later PRs give this command real options.

    Returns:
        Process exit code; 0 on success.
    """
    print("drh " + __version__ + " - offline demo")
    print("Research pipeline lands in a later PR; see ROADMAP.md for the build order.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to a subcommand.

    Args:
        argv: Argument vector excluding the program name. Defaults to `sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    result: int = func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
