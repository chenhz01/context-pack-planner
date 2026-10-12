# context-pack-planner

Pack prioritized documents into a fixed context budget deterministically:
greedy first-fit with a must-include reserve, deterministic tie-breaking
(priority, then cost, then name), partial fitting for truncatable documents,
and a `plan_hash` so the same manifest always yields a byte-reproducible
plan. Pure standard library, single file, offline.

## Problem

Assembling a context window from a system prompt, retrieved documents, and
history is a bin-packing decision made ad hoc in application code every
time. The result is irreproducible — rerun the assembly and you may get a
different mix — and when the window overflows, what got dropped is usually
invisible. A packing plan should be a inspectable artifact: here is what
fits, here is what was skipped and why, and here is a hash proving the plan
is the one you reviewed.

## How it works

1. **Manifest** — a JSON object: `budget` (tokens), optional `reserve`
   (tokens held back, e.g. for the system prompt or the reply), and `docs`:
   `{"name", "tokens", "priority", "must", "truncate"}`.
2. **Reserve first** — `usable = budget - reserve`; a reserve larger than
   the budget is rejected.
3. **Must-include pass** — `must` docs are packed in (cost, name) order; one
   that cannot fit is skipped with reason `must_doc_exceeds_budget` — the
   plan fails loudly instead of silently dropping something marked must.
4. **Priority pass** — the rest are packed by (priority asc, tokens asc,
   name asc) greedy first-fit. A doc with `"truncate": true` that does not
   fit takes whatever room remains (recorded as `partial` with
   `dropped_tokens`); otherwise it is skipped with `insufficient_budget`.
5. **Reproducibility** — the plan's core (budget, reserve, used, included,
   skipped) is canonical-JSON hashed (SHA-256, first 16 hex chars) into
   `plan_hash`. Identical manifests → identical hashes; any change in
   inputs changes the hash.

## Quickstart

```bash
# plan.json manifest → plan to stdout (~0.2 s)
python context_pack_planner.py --manifest plan.json

# write the plan as a file
python context_pack_planner.py --manifest plan.json --out packed.json

# stdin works too:
cat plan.json | python context_pack_planner.py
```

Self-test suite: 57/57 passing in under a second (measured: `python
self_test.py`; all seven sibling tool suites together took 4.4 s wall clock on
Python 3.13 / Windows 10, including interpreter startup).

## Why not X

| Alternative | Stars (as of 2026-10-11) | How this differs |
| --- | --- | --- |
| [reaatech/context-window-planner](https://github.com/reaatech/context-window-planner) | 0 | Frames packing as a resource-allocation problem with the same inputs (system prompts, history, RAG chunks). This tool's contribution is the *auditable, hashed plan artifact* and a strict no-dependency CLI, not an allocation solver. |
| [Zion-support/zion-context-window-planner](https://github.com/Zion-support/zion-context-window-planner) | 0 | A vendor-branded planner for budgeting prompts per model. This tool is model-agnostic — you supply the budget number — and emits a reproducible plan hash for CI assertions. |
| [mertcanaltin/composto](https://github.com/mertcanaltin/composto) | 78 | An AST-first IR engine that compresses source code to cut ~89% of tokens [per its README]. Compression changes content; this planner changes *which* whole documents ship and records what was left out — it never rewrites text. |

## Minimal Fallback

Sort by priority and take documents until the budget runs out — one list
comprehension:

```python
picked = []
left = budget
for d in sorted(docs, key=lambda d: d["priority"]):
    if d["tokens"] <= left:
        picked.append(d); left -= d["tokens"]
```

You lose the must-include pass, partial/truncated fitting, skip reasons, and
the plan hash — i.e. everything that makes the plan auditable.

## Design Trade-offs

- **Greedy first-fit over optimal bin-packing.** Optimal (0/1 knapsack DP) is
  O(budget × docs) and pointless when costs are approximate anyway; greedy in
  priority order is O(n log n) and matches the human expectation "highest
  priority first".
- **Whole documents over sentence compression.** Partial fitting cuts a
  document at a token count but the tool does not rewrite prose (pair it with
  a compression tool if wanted). Plans stay explainable: "doc X shipped, 200
  tokens short".
- **Tokens are declared, not estimated.** The planner trusts the manifest's
  `tokens` field — it composes with token-budget-clamp (estimator) or any
  tokenizer, instead of embedding one.
- **Fail-loud must docs.** A `must` doc that cannot fit is recorded as
  skipped, not quietly omitted — the caller decides whether to abort.

## Limits & Second-order Effects

- **Declared costs can lie.** If upstream token estimates are wrong, the plan
  is confidently wrong; assert plan totals against your real tokenizer at
  least once per pipeline change.
- **Priority inflation.** Once priority drives inclusion, everything becomes
  priority 1 [estimated risk]; mitigate by treating `plan_hash` diffs as the
  review artifact — priority churn becomes visible.
- **Greedy can strand budget**: a large mid-priority doc may leave room that
  only `truncate` docs can use; when nothing truncates, budget goes unused by
  design.
- **Second order**: because skipped reasons are structured, dashboards will
  eventually alert on `insufficient_budget` — teams then raise budgets rather
  than prune documents. Watch total token spend, not just plan success rate.

## FAQ

**Is the plan guaranteed optimal?** No — deterministic and auditable, not
optimal. For near-optimal packing of hundreds of same-priority docs, add a
DP pass; for prompt assembly, greedy is enough.

**Can two docs share a name?** No — duplicate names are a validation error,
because the plan references docs by name.

**When NOT to use this?** When documents are few and tiny (packing logic is
overhead), or when content-level compression is what you need (use a
compressor; this tool ships documents, not sentences).

**What does the hash cover?** Everything except `plan_hash` itself: budget,
reserve, used, included, skipped — not input file paths or formatting.

## Core Assumptions

1. Per-document token costs are knowable before packing (measured or
   estimated upstream).
2. Priority is a real, maintained ordering — the tool's output quality is
   bounded by it.
3. Day-to-day prompt assembly benefits more from reproducibility and skip
   reasons than from a few percent of packing optimality.
4. Budget and reserve are expressed in the same token unit as `tokens`
   fields; the tool does no unit conversion.

Confidence: high on packing determinism and validation (57 self-tests),
medium on cost-input quality assumption. As of 2026-10-11.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [llm-cache-key-spec](https://github.com/chenhz01/llm-cache-key-spec) · [fewshot-picker-bench](https://github.com/chenhz01/fewshot-picker-bench) · [instruction-dsl-lint](https://github.com/chenhz01/instruction-dsl-lint)
