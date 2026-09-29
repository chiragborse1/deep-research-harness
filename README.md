# deep-research-harness

**Long-horizon research runs that survive being killed.**

Research agents do not fail because the model is weak. They fail because the run *dies* — the
process is killed, the network drops, the context overflows, a tool hangs forever, and after
hours of work you are left with nothing. Every framework treats the agent loop as the product.
We treat the **durable state machine around it** as the product.

`drh` is a provider-agnostic harness for research agents that must run for hours, not minutes:

- **Crash-consistent run state** — every step transition is a transaction. Kill the process at
  any instruction boundary and resume with no duplicated side effects and no lost work.
- **Sandboxed tool execution** — allowlisted HTTP, jailed file reads, subprocess off by default.
  Every result is content-addressed and stored out-of-band, so a hung tool cannot kill a run.
- **A veracity ledger** — every claim the run makes carries a confidence and a list of evidence
  references. Claims with no evidence are marked `unsupported` and the report says so out loud.
- **Zero vendor lock-in** — no LLM SDK in core. OpenAI-compatible, Anthropic, Ollama, and a
  deterministic mock ship as adapters behind one `Provider` trait. Everything works with no API
  key at all.

---

## Quickstart

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). No API key, no network.

```bash
git clone https://github.com/chiragborse1/deep-research-harness.git
cd deep-research-harness
uv sync --all-extras
uv run drh demo
```

`uv run drh demo` executes a complete research run against the deterministic mock provider and
prints real measured output. The quickstart above is verified on every push by CI.

---

## Why this exists

Every "AI research agent" demo runs for ninety seconds. That is not because ninety seconds is
enough, but because a longer run is hard: state lives in process memory, so the run dies with
the process; tool calls are synchronous, so one slow URL stalls everything; and the final report
is prose, so its claims cannot be checked.

The failure is structural, not a tuning problem. This project fixes the structure:

| Failure mode | What most harnesses do | What `drh` does |
|---|---|---|
| Process killed mid-run | Lose everything | Every transition is a transaction; `resume()` reconstructs exact position |
| Duplicate side effects on retry | Re-fetch, re-pay, re-post | Idempotency keys make every step replay-safe |
| One slow tool call | Stalls the whole agent | Sandboxed tools with timeouts and output caps |
| A 10 MB web page | Blows the context window | Content-addressed, streamed, never fully materialized |
| Report says "studies show..." | Unverifiable prose | Veracity ledger: claim -> confidence -> evidence refs |

---

## Status

`v0.1.0` is in progress. The build order is published in [ROADMAP.md](ROADMAP.md); each entry is
a merged, green PR. Nothing marked as working in this README is aspirational — see
[CHANGELOG.md](CHANGELOG.md) for what has actually shipped.

## Documentation

| Document | Purpose |
|---|---|
| [DESIGN.md](DESIGN.md) | Architecture and tradeoff analysis, written before the code |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Component map and sequence diagrams |
| [DECISIONS.md](DECISIONS.md) | Every autonomous decision, with reasoning and rejected alternatives |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, commands, PR conventions |
| [ROADMAP.md](ROADMAP.md) | Build order, what is out of scope, and why |
| [EXAMPLES.md](EXAMPLES.md) | End-to-end usage scenarios |
| [CHANGELOG.md](CHANGELOG.md) | Keep a Changelog format |

## License

Apache-2.0. See [LICENSE](LICENSE).

## Part of a coherent thesis

This is one of several projects on agent infrastructure, context integrity, and AI veracity:

- [context-engineering-runtime](https://github.com/chiragborse1/context-engineering-runtime) —
  treats LLM context as a managed, budgeted, evictable resource rather than an append-only log.

Shared ideas, shared conventions, real dependencies over time. Nine unconnected repositories read
as a hobby project; a connected set reads as a thesis.

---
Built by [Chirag Borse](https://github.com/chiragborse1).
