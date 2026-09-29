# CONTRIBUTING.md

Thanks for looking at this. Everything below is verified by CI, so if a command here fails on
your machine but passes on CI, that is a bug in this file — please open an issue or a PR to fix
it.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 0.11+
- (optional) `uvx pre-commit install` for local hooks

**No API key is needed for any development, test, or benchmark command.** If you find yourself
needing one, that is a bug — see [DESIGN.md](DESIGN.md) §3.4.

---

## Setup

```bash
git clone https://github.com/chiragborse1/deep-research-harness.git
cd deep-research-harness
uv sync --all-extras
```

---

## Commands

Every one of these is a `make` target, and every one is also what CI runs.

| Command | What it does |
|---|---|
| `make install` | Sync the dev environment |
| `make build` | Build wheel + sdist, then verify the wheel imports |
| `make test` | Full test suite with coverage (fails under 80%) |
| `make lint` | `ruff check`, `ruff format --check`, docstring gate |
| `make format` | Auto-format and auto-fix |
| `make typecheck` | `mypy --strict` + vendor-SDK gate |
| `make security` | `pip-audit` + `bandit` |
| `make bench` | Committed benchmark suite |
| `make demo` | Offline end-to-end demo, no API key |
| `make quickstart` | Verify the README quickstart is real |
| `make ci` | Everything CI runs, in order |

---

## Project-specific gates

These are not style preferences. Each maps to a stated requirement and each fails the build.

| Gate | Requirement it enforces |
|---|---|
| `scripts/check_endpoint_independence.py` | No vendor LLM SDK may be imported under `src/`. All model access goes through the `Provider` trait. |
| `scripts/assert_offline.py` | The suite must run with no provider credential in the environment. |
| `scripts/check_docs.py` | Every public symbol in `src/drh` needs a docstring. |
| `scripts/verify_quickstart.py` | The README quickstart must exist and contain no network commands. |
| `scripts/verify_build.py` | The built wheel must import and expose `__version__`. |

The endpoint-independence check parses imports with `ast`, not `grep`, so mentioning a vendor name
in a docstring or comment is fine — importing it is not.

---

## Testing conventions

- **Unit tests** for all logic.
- **Property-based tests** (`hypothesis`) for anything that parses, serializes, or round-trips.
- **Golden-file tests** for anything token- or output-sensitive.
- **Integration tests** run against `MockProvider`. No network in CI, ever.
- **No unseeded randomness.** Any test using randomness takes an explicit seed and is
  reproducible.
- Mark slow tests with `@pytest.mark.slow` and network tests with `@pytest.mark.network` so CI
  can deselect them.

---

## PR conventions

**Never commit directly to `main`.** Not for a typo.

1. Branch: `feat/<scope>-<short>`, `fix/<scope>-<short>`, `docs/<scope>`, `test/<scope>`,
   `perf/<scope>`, `chore/<scope>`.
2. One logical change per PR. If the description needs the word "and" twice, split it.
3. Conventional Commits, imperative mood, scoped. The body explains **why**, not what.
4. PR body must contain **What / Why / How to verify / Related issue**.
5. Self-review your own diff before requesting review. Fix your own review comments.
6. `main` requires 1 approval and all five required checks to pass, and is squash-merged to keep
   history readable.

---

## Adding a provider adapter

This is the most common contribution. The rules:

1. Implement the `Provider` protocol in `src/drh/providers/`.
2. **Use `httpx`. Do not add a vendor SDK dependency**, including as an optional extra — the
   gate scans all of `src/`, and adding one will fail CI.
3. Make the adapter accept a base URL so it works against self-hosted gateways (vLLM, llama.cpp,
   Ollama) as well as the vendor cloud.
4. Raise typed errors from `drh.errors`; never raise bare `Exception`.
5. Add a test that runs against a local `MockTransport`, not the live API.
6. Add the adapter to the endpoint-independence allowlist documentation if it needs one.
