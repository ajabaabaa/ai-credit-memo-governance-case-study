# Benchmark V1 — Measure protocol

## Decision under study

How accurately and reliably does a single Data-Retrieval-Agent-shaped LLM extract the fixed 16-field, two-year financial schema from the same synthetic statement records, while the five ratios remain deterministic? This is extraction and control measurement only. It makes no credit decision and uses no model cascade, swarm, or JEV routing.

The original workflow's AI Intake-Agent is outside this measurement boundary. Each benchmark run starts from a frozen fixed-schema statement after intake; Gate 1 worksheets remain blank until a human reviewer acts.

## Corpus and comparability

- Seed: `20261020`; record IDs are stable and increasing.
- Input and ground truth are separate JSONL files. Only statement text and ID go to the extractor.
- Every result records input SHA-256, truth SHA-256, and prompt SHA-256.
- Dataset sizes are prefixes of the same seeded sequence. All model runs at a given size must use the same hashes.
- The five ratio formulas, gross-margin tie-out, and debt/EBITDA definitions follow the original [`workflow/workflow-logic.md`](../workflow/workflow-logic.md).

## Fixed processing order

1. Send one record to one model through its declared route.
2. Parse and normalize keys to the repository’s strict JSON schema; do not repair numeric values.
3. Compare 32 CY/PY numeric fields with hidden ground truth.
4. Run the deterministic gross-margin tie-out and required metadata/control checks.
5. Calculate the five ratios deterministically; compare them offline with ratios derived independently from ground truth.
6. Produce a blinded Gate 1 worksheet for the human reviewer. Do not simulate or infer approval.

Models receive the same records independently, never sequentially. Routes are recorded separately from model IDs. OpenRouter calls use the OpenRouter API; OpenCode calls use the OpenCode CLI and its local session usage metadata; Ollama calls use the local Ollama API.

## Gate 1 human review

Gate 1 follows extraction and the gross-margin tie-out, before operational ratio calculation. The reviewer checks borrower match, latest fiscal year, missing items, both tie-outs, and two figures against the statement. The worksheet records APPROVE or SEND BACK with reason and correction. The source workflow permits two send-backs and escalates after the next failure. The model-to-review-ID key is separate from the review CSV. No review decisions have been supplied yet; review-burden results are therefore pending.

## Measures

- **Field accuracy:** exact CY/PY numeric matches / 32 fields per record.
- **Record exact accuracy:** share of records with all 32 numeric values exact.
- **Ratio agreement:** exact-to-1e-12 agreement across five ratios × two years against independent truth calculations.
- **Metadata accuracy:** exact company, form type, and fiscal-year-end match.
- **Control failures:** records with a call error, missing value, nonempty `not_found`, metadata mismatch, or gross-margin tie-out failure. Tie-out errors are also reported by year.
- **Latency and throughput:** total elapsed pipeline time and records / total elapsed time. Local and CLI process overhead are included.
- **Tokens:** provider-reported input plus output, reasoning, and cache counts when available; otherwise N/A, never zero by assumption.
- **Cost:** provider-reported actual cost, $0 for explicit free/local routes, and conservative pre-call reservations for paid OpenRouter routes. Total paid-spend cap is $2.

## Progression and evidence boundary

- Offline deterministic cohort: 100 → 1,000 → 10,000 → 100,000 → 1,000,000 records.
- Model cohort: one-record route smoke → 10-record pilot → selected model at 100 records. More model records are added only when provider reliability and latency support it.
- A simulator result at 1,000,000 verifies deterministic parsing, tie-outs, and formula scoring at that scale. It is not LLM inference and must not be described as a million-record model benchmark.
- The present synthetic statement format uses plainly labeled line items. It does not represent the full layout variance, notes search, or citation fidelity of a real 10-K; no real borrower data is used.

## Controlled source-quality sensitivity experiment

- A separate frozen 10,000-record `quality-mix` cohort assigns every record to 50%, 75%, or 100% exact numeric source quality. Each statement has 32 CY/PY amounts; the generator alters exactly 16, 8, or 0 values, respectively.
- The predeclared defect mix cycles through OCR-like digit changes, decimal shifts, unit-scale mistakes, period misalignment, and adjacent-line value substitution. The hidden QA sidecar records each mutation and tier; the model receives only statement text.
- Statements cycle through eight filing-like layouts, reordered lines, alternate labels, currency and comma formatting, consolidated/segment distractors, lease-interest distractors, and note references. Ground truth retains both the values shown and the clean latent values.
- Score each model twice: extraction fidelity against the presented values, and fidelity of extracted ratios against the clean latent statements. This distinguishes accurate copying from the effect that defective source data has on deterministic ratio outputs.
- For cross-model screening, use the fixed 24-record stratified sample (8 per tier; one example per tier/layout). Extend the sample if results warrant; do not describe it as a full 10,000-record LLM run. A preceding 48-record run was only prompt calibration and is excluded from comparisons because its schema-key instruction was under-specified.

## Safety and spend

The ledger caps paid inference at $2.00, checks live OpenRouter per-token pricing, reserves a conservative call estimate, and refuses a call that would exceed the remaining cap. A DeepSeek V3.2 budget probe made one completed call ($0.000681 for 733 prompt / 614 completion tokens) and one interrupted call charged its conservative $0.001288 reservation. Total spend is $0.001969 with no outstanding reservation. The first call projects approximately $6.81 for a 10,000-record pass; conservative max-output reservations project $12.48. Paid full-corpus inference therefore does not fit the current cap. The interrupted probe is not a benchmark result. Every model comparison must use the same frozen input and ground-truth hashes; differing cohort sizes or cohort types are not comparable. API keys remain in process environment variables and are never written to corpus or result files.

An OpenRouter Batch follow-up then ran the full 10,000-record cohort simultaneously through GPT-OSS 20B and Ministral 8B. Both providers completed 10,000 requests with zero provider-level request failures, at costs $0.883748 and $0.948817. The 640-token completion cap truncated all GPT-OSS outputs and 9,462 Ministral outputs; strict JSON parsing failed on all GPT-OSS and 9,461 Ministral responses. These runs measure configuration/output-format failure and are excluded from model accuracy comparisons. Combined with the probe, ledger spend is $1.834534 with $0 reserved. Re-running a full cohort with a sufficient output budget is blocked by the remaining $0.165466 cap; the Batch runner default is now 1,600 output tokens so it will refuse rather than repeat the truncation configuration. The full cohort hashes are identical for both models.
