# DERIVED SPECIFICATION — Project 8: Long-Horizon Research Harness

**Status:** Part B of `08-DEEP-RESEARCH-HARNESS.md` is TRUNCATED in the source file. The file
ends immediately after the header `## PART B - THE PROJECT` with the line
"Everything below is the task specification. Execute it end to end." and no spec body.

Verification (2026-09-29): the file is 171 lines / 8,893 bytes. Files `02`–`09` are all the
same length (171 lines) and share the identical truncation. Only `01-CONTEXT-ENGINEERING-RUNTIME.md`
(411 lines) contains a real Part B, embedded as a fenced prompt block.

Per §A.1 ("Ambiguity is not a blocker; an undocumented decision is"), this spec is reconstructed
from the evidence that IS present and is treated as authoritative going forward.

## Evidence used

| Source | Signal |
|---|---|
| File title | "Project 8 - Long-Horizon Research Harness" |
| Target repo line | `chiragborse1/deep-research-harness` |
| `10-SEQUENCING.md` Wave 3 table | "8. Research Harness — Sandboxing + durable state + live UI. The hardest." |
| Cross-project rules | "Ship the benchmark, always" |
| `00-SHARED-CONVENTIONS.md` §0 | Full operating procedure (unchanged, verbatim) |

## PROJECT

**Repo:** `chiragborse1/deep-research-harness`

A provider-agnostic harness for research agents that must run for hours, not minutes. The
central bet: a research agent fails not because the model is weak, but because the run
**dies** — the process is killed, the network drops, the context overflows, or a tool hangs.
Everything here is about making long runs *durable, resumable, and auditable*.

## Core thesis

**A research run is a durable state machine, not a loop.** State lives in a crash-consistent
store. Every step is a transactional transition with an idempotency key. The agent can be
killed at any instant and resumed with no duplicated side effects and no lost work.

## Architecture — five components, each independently testable

1. **RunStore** — crash-consistent durable state. SQLite in WAL mode with a write-ahead
   event log. Every state transition is a transaction. `resume(run_id)` reconstructs exact
   executor position. Crash-consistency is a *test*, not a claim: kill the process mid-write
   and assert the run resumes correctly.
2. **StepExecutor** — the step state machine. States: PLAN -> FETCH -> EXTRACT -> ANALYZE ->
   SYNTHESIZE -> VERIFY -> DONE | FAILED. Each transition is guarded, typed, and recorded.
   Terminal states are absorbing.
3. **ToolSandbox** — sandboxed tool execution. Pluggable `ToolAdapter` trait. Ships:
   `HttpFetchTool` (allowlist, size cap, content-type gate), `FileReadTool` (path jail),
   `SubprocessTool` (disabled by default, opt-in, timeout + output cap). Every tool result is
   content-addressed and stored out-of-band, so a hung or huge tool call can never blow up
   the run.
4. **Provider** — one trait, four adapters (OpenAI-compatible, Anthropic, Ollama, Mock).
   Zero vendor SDK in core. Everything works offline with no API key.
5. **VeracityLedger** — every claim the run makes gets a `Claim` with a confidence and a
   list of `EvidenceRef`s. Claims with no evidence are marked `unsupported`. The final report
   can therefore be checked mechanically. This is the project's moat and the differentiator
   from every "AI research agent" that hallucinates a bibliography.

## Headline features

**A. CRASH CONSISTENCY AS A TESTABLE PROPERTY.** A `ChaosRunner` injects a crash at a
random instruction boundary (seeded, deterministic), restarts, and asserts the resumed run
produces byte-identical final state to an uninterrupted run. This is the benchmark artifact.

**B. THE VERACITY LEDGER.** Not "the AI wrote a report" but "here is every claim, its
confidence, and the evidence that supports it — or the explicit admission that there is none."
Report generation is gated on ledger completeness.

**C. LONG-HORIZON STABILITY.** Wall-clock benchmarks: hours-long runs, context growth over
thousands of steps, resume-from-crash time. Measures what actually breaks.

## Technical stack

- Python 3.12+, `uv` for dependency management. Pure Python — a Rust core is optional and was
  rejected (see DECISIONS.md ADR-0002).
- pydantic for all public types. mypy strict.
- SQLite (WAL) for durable state. httpx for HTTP. ruff for lint. pytest + hypothesis.
- NO LangChain, NO vendor SDK in core, zero heavy framework deps.

## Deliverables

1. `gh repo create chiragborse1/deep-research-harness --public`, 6 topics, branch protection on
   main (PR + 1 approval + 5 required checks + linear history).
2. DESIGN.md written BEFORE the first line of core code.
3. All 8 docs from §0.7, plus EXAMPLES.md and a social preview image.
4. `make demo` that runs offline with no API key and prints real measured output.
5. Committed, runnable benchmark with real numbers in `bench/results/`.

## Build order (one vertical slice per PR)

| PR | Branch | Scope |
|---|---|---|
| 1 | `chore/repo-scaffold` | repo, CI, tooling, pre-commit, docs skeleton |
| 2 | `feat/errors-typed-exception-hierarchy` | typed errors |
| 3 | `feat/types-run-and-step-models` | pydantic domain models |
| 4 | `feat/provider-provider-trait-and-mock` | Provider trait + MockProvider (offline CI) |
| 5 | `feat/provider-http-and-anthropic-adapters` | OpenAI-compatible + Anthropic + Ollama |
| 6 | `feat/store-crash-consistent-run-store` | WAL store, transactional transitions |
| 7 | `feat/store-resume-and-idempotency` | resume + idempotency keys |
| 8 | `feat/executor-step-state-machine` | typed guarded transitions |
| 9 | `feat/tools-sandboxed-tool-adapters` | HttpFetch/FileRead/Subprocess |
| 10 | `feat/ledger-veracity-claim-ledger` | claims + evidence refs |
| 11 | `feat/report-gated-on-ledger-completeness` | report generation + gate |
| 12 | `test(chaos): crash-injection harness + CI gate` | ChaosRunner |
| 13 | `feat(bench): stability + throughput benchmarks` | committed benchmark |
| 14 | `docs: full doc set, DESIGN.md, ADRs, EXAMPLES.md` | docs |
| 15 | `chore(release): v0.1.0` | release |

Do not skip ahead. Do not batch. Each PR individually reviewable and green.

## Rejected interpretations

- **"Research harness" = a literature-review chatbot.** Rejected: the sequencing doc calls
  this project "the hardest" and names sandboxing + durable state + live UI. A chatbot is
  none of those.
- **Skip straight to a live web UI.** Rejected: the sequencing doc places project 9
  ("Agent Workspace") after this one and says "Depends on 5 and 8 being mature. Do not start
  early." The UI belongs to a later project, not here. Out of scope, recorded in ROADMAP.md.
- **Fabricate a Part B to match the others.** Rejected. This reconstruction is derived from
  evidence and is labelled as such in DECISIONS.md.
