# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

Nothing yet.

## [0.1.0] - Unreleased

### Added

- Project scaffold: `uv`-managed Python 3.12 package, mypy strict, ruff, pytest with an 80%
  coverage floor.
- CI enforcing five required checks (`build`, `test`, `lint`, `typecheck`, `security-scan`)
  plus a README quickstart verifier.
- Mechanical endpoint-independence gate (`scripts/check_endpoint_independence.py`) that fails
  the build if a vendor LLM SDK is imported under `src/`.
- Offline guarantee gate (`scripts/assert_offline.py`) that fails CI if any provider credential
  is present in the environment.
- Public-API docstring gate (`scripts/check_docs.py`).
- `drh` console script with a `demo` subcommand that runs with no API key.

[Unreleased]: https://github.com/chiragborse1/deep-research-harness/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/chiragborse1/deep-research-harness/releases/tag/v0.1.0
