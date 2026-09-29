# ARCHITECTURE.md

Component reference for `deep-research-harness`. For the reasoning behind these choices, see
[DESIGN.md](DESIGN.md). For the decision log, see [DECISIONS.md](DECISIONS.md).

> Components are listed in build order. Each is a merged, green PR; nothing described here is
> aspirational. Current status is in [ROADMAP.md](ROADMAP.md).

---

## Module map

```
src/drh/
  __init__.py        package root, __version__
  cli.py             argparse CLI; thin shell over library code
  errors.py          typed exception hierarchy        [PR 2]
  types.py           pydantic domain models           [PR 3]
  providers/
    base.py          Provider protocol + request/response models   [PR 4]
    mock.py          MockProvider: deterministic, seeded, offline  [PR 4]
    openai_compat.py OpenAI-compatible HTTP adapter   [PR 5]
    anthropic.py     Anthropic Messages API adapter   [PR 5]
    ollama.py        Ollama HTTP adapter              [PR 5]
  store/
    base.py          RunStore protocol                [PR 6]
    sqlite_store.py  WAL-backed implementation        [PR 6]
    resume.py        resume + idempotency             [PR 7]
  executor.py        StepExecutor state machine       [PR 8]
  tools/
    base.py          ToolAdapter protocol             [PR 9]
    http_fetch.py    allowlisted HTTP fetch           [PR 9]
    file_read.py     path-jailed file read           [PR 9]
    subprocess_tool.py opt-in, timeout-bounded        [PR 9]
    blobstore.py     content-addressed evidence store [PR 9]
  ledger.py          VeracityLedger: claims + evidence [PR 10]
  report.py          report generation + gate         [PR 11]
  chaos.py           ChaosRunner crash injection      [PR 12]
```

---

## Component: RunStore

Owns all durable run state. The rest of the system never writes to the database directly.

### Invariants

1. Every state transition appends an event **and** updates the materialized row in one
   transaction. The log and the state cannot disagree.
2. Ordering uses a monotonic sequence number, never wall-clock time. Clock skew cannot reorder
   a run.
3. `resume(run_id)` is a pure function of the committed log.
4. `DONE` and `FAILED` are absorbing. A terminal run cannot transition again.

### Sequence: a single transition

```mermaid
sequenceDiagram
    participant E as StepExecutor
    participant S as RunStore
    participant D as SQLite (WAL)

    E->>S: transition(run_id, from, to, cause, idempotency_key)
    S->>S: guard: is `from` the current state?
    S->>S: guard: is (run_id, idempotency_key) already committed?
    alt key already committed
        S-->>E: prior result (no-op replay)
    else guard fails
        S-->>E: raise IllegalTransition
    else new transition
        S->>D: BEGIN IMMEDIATE
        S->>D: INSERT INTO events (...)
        S->>D: UPDATE runs SET state=?, seq=?
        S->>D: COMMIT
        S-->>E: RunSnapshot
    end
```

The idempotency check is what makes retry-after-crash safe: if the side effect committed but the
process died before recording that fact, the retry recognizes the key and does not repeat the
side effect.

---

## Component: StepExecutor

```mermaid
stateDiagram-v2
    [*] --> PLAN
    PLAN --> FETCH
    FETCH --> EXTRACT
    EXTRACT --> ANALYZE
    ANALYZE --> SYNTHESIZE: more work needed
    ANALYZE --> VERIFY: analysis complete
    SYNTHESIZE --> VERIFY
    VERIFY --> DONE
    PLAN --> FAILED
    FETCH --> FAILED
    EXTRACT --> FAILED
    ANALYZE --> FAILED
    SYNTHESIZE --> FAILED
    VERIFY --> FAILED
    DONE --> [*]
    FAILED --> [*]
```

`DONE` and `FAILED` are absorbing: no outgoing edges. Every transition is validated against
this table *before* it reaches the store, so an illegal transition is a typed error rather than a
corrupted run.

---

## Component: ToolSandbox

```mermaid
sequenceDiagram
    participant E as StepExecutor
    participant R as ToolRegistry
    participant T as ToolAdapter
    participant B as BlobStore

    E->>R: invoke(name, params, idempotency_key)
    R->>T: run(params, deadline, limits)
    T->>T: validate against sandbox policy<br/>(allowlist, size cap, timeout)
    alt policy rejects
        T-->>R: ToolRejected (typed)
    else allowed
        T-->>R: raw bytes (bounded)
        R->>B: put(bytes) -> sha256
        B-->>R: BlobRef(hash, size, content_type)
        R-->>E: ToolResult(ref, digest, truncated)
    end
```

The executor never receives raw bytes for anything over the inline threshold. It receives a
`BlobRef`. This is what keeps context growth sub-linear over a long run.

---

## Component: VeracityLedger

```mermaid
sequenceDiagram
    participant E as StepExecutor
    participant L as VeracityLedger
    participant B as BlobStore

    E->>L: add_claim(text, confidence, evidence_refs)
    L->>B: verify each ref resolves
    alt every ref resolves
        L->>L: supported = true
    else any ref missing
        L->>L: supported = false, status = UNSUPPORTED
    end
    L-->>E: Claim

    Note over E,L: Report generation is gated on<br/>ledger.completeness_report()
```

A claim whose evidence does not resolve is not deleted — it is retained and marked
`UNSUPPORTED`. Deleting it would hide a research failure; the point is to surface it.
