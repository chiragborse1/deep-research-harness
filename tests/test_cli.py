"""Tests for the `drh` CLI surface.

The CLI is the project's public entry point, so its argument parsing and help output are part of
the contract. A regression that makes `--help` print a malformed description is a real bug, not
a cosmetic one: the help text is how a first-time user learns what the tool does.
"""

from __future__ import annotations

import pytest

from drh import __version__
from drh.cli import build_parser, main


def test_version_is_semver() -> None:
    """The package exposes a parseable semantic version."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_parser_registers_demo_command() -> None:
    """The parser exposes the `demo` subcommand."""
    parser = build_parser()
    args = parser.parse_args(["demo"])
    assert args.command == "demo"
    assert callable(args.func)


def test_no_command_prints_help_and_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    """Invoking with no subcommand prints help and returns a nonzero exit code."""
    exit_code = main([])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "usage: drh" in captured.out


def test_demo_runs_offline(capsys: pytest.CaptureFixture[str]) -> None:
    """`drh demo` succeeds and prints the version without needing a credential."""
    exit_code = main(["demo"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_description_has_no_missing_space() -> None:
    """Concatenated help-text fragments must not run words together.

        Regression test: the description was originally assembled by implicit string concatenation
        without a trailing space, producing "averacity" and "realmodel" in `--help`. This asserts
    the rendered help contains no such splice.
    """
    help_text = build_parser().format_help()
    for bad in ("averacity", "arealmodel", "realmodel"):
        assert bad not in help_text


def test_help_mentions_offline_guarantee() -> None:
    """The top-level help states the offline guarantee, a headline project property."""
    help_text = build_parser().format_help()
    assert "no API key" in help_text
