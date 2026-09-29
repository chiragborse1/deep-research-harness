# DESIGN.md — Long-Horizon Research Harness

> **Status:** living document. Written before the first line of core library code, updated as
> decisions are made. Every "Rejected" entry below is a decision that was actually considered and
> dropped, not a strawman.

---

## 1. The problem

A research agent is a loop: plan, fetch, read, analyze, write. Ninety-second demos of that loop
are everywhere and mostly work. Runs that last hours mostly do not, and they do not fail for
the reason people expect.

They fail **structurally**:

| What actually happens | Why the loop architecture cannot handle it |
|---|---|
| The process is killed (OOM, deploy, laptop sleep) at hour 3 | State is in process memory. There is no state. |
| A tool call hangs | One synchronous call, no timeout, no cap. The agent waits forever. |
| The same fetch runs twice after a retry | No idempotency key. Double the API spend, double the side effects. |
| One page is 10 MB | It lands in the context window and the run dies of token overflow. |
| The report asserts "studies show X" | Prose cannot be checked. The hallucination is indistinguishable from the finding. |

Each of these is a missing mechanism, not a model-capability problem. Making the model better
does not fix any of them.

## 2. Thesis

**A research run is a durable state machine, not a loop.**

The loop is a small part of the system. The product is everything that makes the loop survive:
persisted state, transactional transitions, bounded and sandboxed side effects, and an auditable
trail from every claim back to the bytes that support it.

Concretely, three commitments:

1. **Durability is a testable property, not a claim.** A `ChaosRunner` kills the process at a
   seeded instruction boundary and asserts the resumed run reaches byte-identical final state. If
   that test does not pass, the harness is broken, regardless of what the demo shows.
2. **Every lossy or synthesized thing is traceable.** Evidence is content-addressed and never
   silently dropped. Claims reference evidence. Claims with no evidence are labeled
   `unsupported` in the output rather than smoothed over.
3. **Nothing is vendor-locked.** The core does not import a model SDK. This is a correctness
   property (it is what makes the offline guarantee possible), not a style preference.

## 3. Architecture

Five components. Each is independently testable, and each is a PR-sized vertical slice.

```
  +-------------------+
  |  StepExecutor     |  typed state machine: PLAN -> FETCH -> EXTRACT ->
  |  (state machine)  |  ANALYZE -> SYNTHESIZE -> VERIFY -> DONE|FAILED
  +---------+---------+
            | every transition is a transaction
  +---------v---------+        +------------------+\
  |  RunStore         |<------>| VeracityLedger   |  claim -> confidence -> evidence refs
  |  (durable state)  |        +------------------+\
  +---------+---------+                 ^
            |                           | claims are checked for completeness
            | resume(run_id)            |
  +---------v---------+        +------------------+\
  |  ToolSandbox      |------->| Provider          |  one trait, 4 adapters, 0 SDKs in core
  |  (bounded effects) |        +------------------+\
  +-------------------+
```

### 3.1 RunStore — crash-consistent durable state

SQLite in WAL mode. Every state transition is a single transaction that appends an event and
updates the materialized row, so the event log and the current state can never disagree.

`resume(run_id)` reconstructs the exact executor position. Idempotency keys make replay safe:
if a step is retried after a crash, the store recognizes the key and returns the prior result
instead of re-executing the side effect.

**Why SQLite and not Postgres or a bespoke log?** The harness is a single-process,
single-writer tool in the overwhelmingly common case. SQLite gives real ACID transactions and
crash recovery with zero operational burden, and it runs in CI with no service container. The
abstraction is a `RunStore` protocol, so swapping in Postgres later is a bounded change, not a
rewrite.

### 3.2 StepExecutor — the state machine

Transitions are guarded, typed, and recorded. Terminal states (`DONE`, `FAILED`) are absorbing.
Every transition records its cause, so a run's history is reconstructible from the event log
alone.

### 3.3 ToolSandbox — bounded side effects

A `ToolAdapter` trait with three shipped implementations:

- `HttpFetchTool` — host allowlist, response size cap, content-type gate, hard timeout.
- `FileReadTool` — path jail; escapes are rejected, not sanitized.
- `SubprocessTool` — **disabled by default.** Opt-in, hard timeout, output cap.

Every result is content-addressed (sha256) and stored out-of-band, so a 10 MB page never
occupies the context window and a repeated fetch of the same bytes is free.

### 3.4 Provider — one trait, zero lock-in

```
class Provider(Protocol):
    async def complete(self, req: CompletionRequest) -> CompletionResponse: ...
```

Adapters: OpenAI-compatible (covers vLLM, Together, Groq, and most gateways), Anthropic,
Ollama, and `MockProvider` (deterministic, seeded, offline). The mock is what makes the entire
test suite and the CI benchmark runnable with no API key.

### 3.5 VeracityLedger — the differentiator

```
Claim { id, text, confidence, evidence: list[EvidenceRef], supported: bool }
```

Report generation is **gated** on ledger completeness: a claim with no evidence cannot be
presented as a finding. It can be presented as an unsupported observation, clearly labeled.

This is the part that distinguishes a research harness from a research chatbot, and it is the
reason the project is worth building.

## 4. Data flow

```
  user goal
    |
    v
  PLAN ---------> RunStore.create_run()            [transaction 1]
    |
    v
  FETCH --> ToolSandbox.fetch() --> content-addressed store
    |         |
    |         +-- result is a ref, not a blob
    |
    v
  EXTRACT --> Provider.complete() --> claims -------> VeracityLedger
    |                                                       |
    v                                                       v
  ANALYZE --> more claims, refs to earlier claims    completeness check
    |                                                       |
    v                                                       v
  SYNTHESIZE --> draft report <----------- GATED on ledger completeness
    |
    v
  VERIFY --> cross-check claims against evidence
    |
    v
  DONE / FAILED                                [transaction N, absorbing]
```

At any arrow, the process may die. On restart, `resume(run_id)` reads the last committed
transaction and continues. Idempotency keys make the retried step a no-op if it already
committed.

## 5. Edge cases (designed for, not discovered later)

| Edge case | Design response |
|---|---|
| Crash between tool side effect and state commit | Idempotency key on the step; the retried step detects the completed side effect and skips it. |
| Two workers resume the same run | Run lease with a heartbeat; the second worker refuses to start. |
| Tool returns 10 MB | Size cap; over the cap the result is stored as a ref and only a digest is passed to the model. |
| Tool hangs forever | Hard timeout; the step transitions to `FAILED` with a typed error, the run is resumable. |
| Provider returns garbage / non-JSON | Typed `ProviderResponseError`; the step retries with backoff, then fails visibly. |
| Context window overflow | Offload-by-default: evidence is referenced, not inlined. |
| A claim has no evidence | Marked `unsupported`; the report says so; the gate does not fail, but the count is surfaced. |
| Two claims contradict | Both retained with a `CONTRADICTS` edge; the verifier flags it rather than silently picking one. |
| Clock skew / non-monotonic timestamps | Event log uses a monotonically increasing sequence number, not wall-clock, for ordering. |

## 6. Performance

Measured, not guessed. The benchmark suite is committed as code and its results are written to
`bench/results/`. The headline metrics this project cares about:

- **Crash-resume overhead** — time to resume a long run from its last committed transaction.
- **State-transition throughput** — transitions per second sustained over a long run.
- **Context growth** — tokens over steps, demonstrating that offload-by-default keeps it
  sub-linear rather than unbounded.

Numbers appear in the README only after they are produced by `make bench` on a real run.

## 7. Tradeoffs consciously accepted

**Pure Python, no Rust core.** A Rust store could be faster. It would also be a second language, a
second build system, and a slower path to a *correct* crash-consistency story — which is the
project's actual differentiator. Correctness of the durability layer matters more than
throughput of the blob store. Revisit only if `make bench` shows the store is the bottleneck.

**SQLite over Postgres.** See §3.1. Zero-ops wins for a single-writer tool; the protocol
boundary keeps the door open.

**No live web UI.** The sequencing notes place the UI in a later project that depends on this
one being mature. Building it now would be building against a moving API. Recorded in
ROADMAP.md as out of scope, not forgotten.

**Subprocess execution off by default.** A research harness that can run arbitrary commands by
default is a security liability, not a feature. Opt-in, jailed, timeout-bounded.

## 8. What would make this fail

Stated up front so it can be measured against:

1. Durability guarantees that hold in tests but not under real crash patterns (power loss vs.
   `SIGKILL` vs. OOM). Mitigation: the chaos runner covers all three, not just process kill.
2. A veracity ledger that is technically complete but practically ignored. Mitigation: the
   report is *gated* on it, so it cannot be bypassed without changing code.
3. Benchmarks that measure the mock provider rather than the harness. Mitigation: benchmarks
   measure harness overhead (transition, store, sandbox) with the provider stubbed, and the
   numbers say so.

---
Related: [ARCHITECTURE.md](ARCHITECTURE.md) (component reference) ·
[DECISIONS.md](DECISIONS.md) (decision log) · [ROADMAP.md](ROADMAP.md) (build order)
