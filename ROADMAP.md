# ROADMAP.md

## Scope note (read this first)

The source specification for this project (`08-DEEP-RESEARCH-HARNESS.md`) has a truncated Part B —
it ends immediately after the `## PART B - THE PROJECT` header with no specification body. The
project scope below was therefore **reconstructed** from the file title, the target repository name,
and the sequencing notes in `10-SEQUENCING.md`, which describe project 8 as "Sandboxing + durable
state + live UI. The hardest."

This is recorded in full in [DECISIONS.md](DECISIONS.md) as **D-0001**. It is stated prominently
because the honest position is that this scope is inferred, not given. If the original
specification resurfaces and differs, the corrections are localized to decisions, not to a
codebase rewrite.

---

## Build order

One vertical slice per PR, each merged green. Status is updated as work lands.

| # | Branch | Scope | Status |
|---|---|---|---|
| 1 | `chore/repo-scaffold` | Repo, CI, tooling, pre-commit, docs skeleton | in progress |
| 2 | `feat/errors-typed-exception-hierarchy` | Typed errors, no bare `except:` | not started |
| 3 | `feat/types-run-and-step-models` | pydantic domain models | not started |
| 4 | `feat/provider-trait-and-mock` | `Provider` protocol + `MockProvider` | not started |
| 5 | `feat/provider-http-adapters` | OpenAI-compatible, Anthropic, Ollama | not started |
| 6 | `feat/store-crash-consistent-run-store` | WAL store, transactional transitions | not started |
| 7 | `feat/store-resume-and-idempotency` | Resume + idempotency keys | not started |
| 8 | `feat/executor-step-state-machine` | Guarded, typed transitions | not started |
| 9 | `feat/tools-sandboxed-adapters` | HttpFetch / FileRead / Subprocess + blob store | not started |
| 10 | `feat/ledger-veracity-claim-ledger` | Claims, evidence refs, support status | not started |
| 11 | `feat/report-gated-on-ledger` | Report generation + completeness gate | not started |
| 12 | `test(chaos)-crash-injection-harness` | `ChaosRunner` + CI gate | not started |
| 13 | `feat(bench)-stability-benchmarks` | Committed benchmark, real numbers | not started |
| 14 | `docs-full-doc-set` | Docs, ADRs, EXAMPLES.md, social preview | not started |
| 15 | `chore(release)-v0.1.0` | Release | not started |

---

## Deliberately out of scope

Recording what is *not* being built is as important as recording what is.

### A live web UI

`10-SEQUENCING.md` mentions "live UI" in its one-line description of this project, but the same
document places the UI-bearing project 9 ("Agent Workspace") *after* this one and states it
"depends on 5 and 8 being mature. Do not start early."

This project ships a library, a CLI, and an offline demo. A UI built now would be built against a
run-state API that the next ten PRs change. Recorded in [DECISIONS.md](DECISIONS.md) as D-0005.

Run observation is still available — the event log and the CLI cover it.

### A Rust core

Considered and rejected for now; revisit only if benchmarks show the store is the bottleneck.
See D-0002.

### A vector store / embedding index

The veracity ledger in this project tracks *provenance*, not semantic similarity. Embedding-based
retrieval is a real need for a research agent, but it is a retrieval problem, and building a
half-baked one would be worse than not having it. When it is built it should be a pluggable
`Retriever` behind a protocol, not a core dependency.

### Multi-agent orchestration

Out of scope. This harness makes *one* run durable. Orchestrating many concurrent runs is a
coordination problem layered on top, and it deserves its own design rather than being an
incidental feature here.

### Production deployment

This is a library and a CLI, not a service. There is no daemon, no server, and no multi-tenant
auth.

---

## Later

Once the vertical slice is complete, in rough priority order:

1. **Additional `Retriever` implementations** behind a protocol (BM25, embeddings).
2. **Distributed `RunStore`** backed by Postgres, for multi-worker runs.
3. **Budget enforcement** — token and wall-clock budgets per run, halting gracefully rather than
   being killed.
4. **OpenTelemetry export** of run traces.
5. **A live run viewer** consuming the event log (belongs with project 9).
