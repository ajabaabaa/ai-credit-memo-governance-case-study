# Credit Memo Governance Benchmark V1 — Measure

This project reproduces the original repository’s linear workflow using synthetic financial statements: fixed-schema intake → Data-Retrieval-Agent extraction → deterministic gross-margin tie-out → Gate 1 human review → deterministic five-ratio calculation. It does not make credit decisions, cascade model outputs, or implement later Measure → Standardize → Optimize → Innovate → Scale phases. The extraction schema, debt definition, EBITDA definition, tie-out, and five formulas follow the original [`workflow/`](../workflow/) files.

## Frozen synthetic corpus

Run from this folder with Python 3.11+:

```powershell
python src/freeze_dataset.py 1 10 100 1000
python src/freeze_dataset.py --profile quality-mix 10000
python src/sample_quality_mix.py
```

This creates versioned JSONL input and separate ground-truth files under `data/`, with SHA-256 hashes in `data/manifest.json`. Inputs passed to a model contain statement text and an ID only; the ground-truth file is never sent to a model. Rows are a deterministic prefix by record count. Use these exact frozen files for every candidate comparison.

The committed repository includes the 10,000- and 100,000-record synthetic cohorts and the full 10,000-record quality-mix inputs/QA sidecar. The one-million-record JSONL payloads are generated locally but excluded from Git because each exceeds GitHub's 100 MiB file limit. Recreate them with the command below; their expected SHA-256 hashes are preserved in `data/manifest.json`.

For scale testing, use `python src/freeze_dataset.py 10000 100000 1000000`. Corpus creation and scoring stream records so the million-record simulator test does not need to hold the corpus or per-record outputs in memory.

## Run the benchmark

```powershell
python src/benchmark.py --records 100 --model simulator
python src/benchmark.py --records 1000 --model simulator
python src/benchmark.py --records 10 --model ollama/qwen3.5-9b-16k:latest
python src/benchmark.py --records 10 --model opencode/deepseek-v4.1-flash-free
python src/benchmark.py --records 10 --model opencode/glm-5.3-flash-free
python src/benchmark.py --records 10 --model opencode/nemotron-3.5-lightning-free
python src/benchmark.py --records 10 --model openrouter/minimax/minimax-m3.1-flash:free
python src/benchmark.py --records 48 --inputs data/statements-quality-mix-sample-48.jsonl --truth data/ground-truth-quality-mix-sample-48.jsonl --model opencode/deepseek-v4.1-flash-free --run-name opencode-deepseek-quality-mix-48
```

Ollama must be running locally and the named model must already be installed. OpenCode must be authenticated and the selected model must be explicitly marked `-free`. Direct OpenRouter model IDs can be passed with `openrouter/` prefix. Provider and model are recorded separately from the local transport. Do not pass the same task through multiple models in sequence: each model receives the same immutable records independently.

Every run writes a result JSON with field exactness, metadata exactness, control failures, tie-out failures, deterministic ratio flag, processing time, throughput, available provider token counts, cost, and input/truth hashes. Model output details are retained for audit. A provider that does not report tokens is recorded as unknown, not zero.

OpenCode reports usage in its local session export on some CLI versions. After a run, `python src/reconcile_opencode_usage.py` reconciles session model, reasoning/cache tokens, and cost against the ordered record batches.

Large simulator-only runs can omit record-level output with `--summary-only`, for example `python src/benchmark.py --records 1000000 --model simulator --summary-only`. This exercises the deterministic pipeline over the fixed million-record corpus; it does not run a million LLM inferences.

### Controlled source-quality sensitivity cohort

The `quality-mix` generator bakes in three per-record exactness tiers before model inference. Each record has 32 CY/PY numeric positions; exactly 16, 24, or 32 match its separately stored clean latent statement at the 50%, 75%, and 100% tiers. Five predefined defect types mimic transcription, decimal/unit, period-alignment, and adjacent-line selection errors. The QA sidecar records every altered field and defect type; models receive only the filing-like statement. The benchmark scores extraction fidelity against the displayed statement separately from agreement with the clean latent values, including downstream deterministic ratios. The 24-record model pilot has 8 records per tier, one from each of eight layouts. It is a screening sample, not 10,000 model inferences. `--responses` checkpoints and replays saved provider outputs through the exact same scorer without repeating calls.

| Model (24-record sample) | Extraction vs displayed values (50/75/100%) | Clean latent ratio agreement (50/75/100%) | Time | Tokens | Notes |
|---|---:|---:|---:|---:|---|
| OpenCode DeepSeek V4.1 Flash Free | 100% / 100% / 100% | 16.3% / 43.8% / 100% | 190.1 s | 395,075 | 1 metadata mismatch; 0 failed calls |
| Ollama Qwen 3.5 9B | 99.2% / 99.6% / 99.2% | 13.8% / 45.0% / 87.5% | 427.9 s | 40,500 | 2 schema failures; 24 Gate 1 control flags |
| OpenRouter MiniMax M3.1 Flash Free | 100% / 100% / 100% | 16.3% / 43.8% / 100% | 318.4 s | 59,775 | 0 failed calls |
| OpenCode GLM 5.3 Flash Free | 87.5% / 100% / 25% | 15.0% / 43.8% / 25% | 250.6 s | N/A | Six 429 quota errors in the last tier; incomplete and excluded from the comparison chart |
| OpenCode Nemotron 3.5 Lightning Free | 0% / 0% / 0% | 0% / 0% / 0% | 343.5 s | N/A | Three-record probe; all responses were empty/invalid JSON; screening only |

The 10,000-record deterministic readback matched 100% of values displayed in the statements. Ratios computed from those values matched the clean latent ratios on 17.6%, 47.4%, and 100% of ratio-year values at the 50%, 75%, and 100% tiers. This demonstrates source-quality sensitivity; defect rates are controlled stress points, not empirical estimates of real filing error prevalence. Complete model curves are in `results/quality_sensitivity.csv` and `.svg`; the dashboard also plots them interactively.

The model comparison uses 8 records per tier, selected to cover all eight layouts once. Results are exploratory. The first 48-record DeepSeek prompt-calibration run used an underspecified schema-key prompt and is excluded from charts. GLM was stopped from further retries after free-tier rate limiting; Nemotron was not expanded after invalid responses. Those pilot runs used local or free routes; a later paid-call probe and the full-corpus batch follow-up are recorded separately below.

### Full-corpus OpenRouter Batch comparison

The OpenRouter Batch runner sends one independent request per record, preserving the same prompt, schema, extraction normalizer, deterministic ratios, and scorer while allowing provider-side asynchronous processing. Each model receives the same frozen 10,000-record cohort. The runner pre-reserves against live `:batch` model rates and a 20% prompt-token buffer before submitting any job; the combined reservations must fit the remaining $2 ledger.

```powershell
python -m pip install -r requirements.txt
python src/openrouter_batch.py submit
python src/openrouter_batch.py poll
python src/openrouter_batch.py score
```

The first full-corpus batch attempt used OpenAI GPT-OSS 20B Batch and Ministral 8B Batch on identical hashes. Both providers completed all 10,000 requests, but the 640-token output cap truncated JSON: GPT-OSS had 10,000 length-limited responses; Ministral had 9,462 length-limited responses and 9,461 JSON parse failures. Neither produced a schema-complete extraction, so these runs are retained for audit and excluded from model-accuracy charts. Charges were $0.883748 and $0.948817; with the earlier $0.001969 probe charge, the ledger records $1.834534 paid and no reservation. Batch durations were 2,271 seconds and 1,440 seconds. The [batch output integrity chart](results/batch_output_integrity.svg) and [CSV](results/batch_output_integrity.csv) show completion and truncation outcomes. The runner's safe default output cap is now 1,600 tokens; the current $0.165466 remaining cap will reject another full-corpus paid run at that setting. Provider batches are asynchronous, can run concurrently, and have a completion window up to 24 hours. Batch IDs and charges are in `results/openrouter-batch-state.json` and `results/spend-ledger.json`; scored results retain the same input/truth hashes. Do not resubmit when a batch state is pending.

## Gate 1 human review

The source Gate 1 occurs after extraction and the gross-margin tie-out, before ratio calculation. A reviewer checks that the borrower matches the intake, the fiscal year is the latest, no required data is missing, both tie-outs pass, and two figures match their cited statements. The reviewer approves or sends back the extraction with a reason. After two send-backs, the source workflow escalates on its next failure.

Each completed run creates a blinded `results/gate1-review-*.csv` with the statement, extraction, checklist, correction, decision, send-back count, and escalation fields. The mapping from blind run ID to model is held separately in `results/gate1-review-key.csv`; keep that key from reviewers until their decisions are recorded. Human decisions are intentionally left blank and are not simulated. Ratios remain deterministic and are calculated after review approval in the source process; V1 reports extraction and control measurements only.

## Spending control

The approved maximum total paid inference spend for this benchmark is **$2.00**. `results/spend-ledger.json` records the cap, conservative reservations, and settled actual or conservative charges. Direct paid OpenRouter calls are preflighted against the live model catalog and a conservative per-call token bound; a call is rejected if its reservation would exceed the remaining cap. Failed or unknown paid calls consume the reservation conservatively. OpenCode routes are accepted only when explicitly marked free. Ollama and explicitly free routes record $0. The current cohort used local or free routes; paid spend remains $0.00.

Never copy API keys into files or results. Set `OPENROUTER_API_KEY` in the process environment. Synthetic data only; do not use borrower information.

## Plots

Refresh the interactive dashboard and static accuracy plot after runs:

```powershell
python src/build_graph_data.py
python src/plot_results.py
python -m http.server 8765 --directory dashboard
```

Open `http://localhost:8765`. The tech-style interactive chart supports metric toggles, model filters, log/linear record scale, hover details, and run selection. Token points are unavailable for transports that do not expose usage. The static SVG and CSV are written under `results/`.

## Current measurements and evidence boundary

| Cohort | Size | Numeric field accuracy | Ratio agreement | Control failures | Elapsed |
|---|---:|---:|---:|---:|---:|
| Offline simulator | 100 | 100% | 100% | 0 | 0.007 s |
| Offline simulator | 1,000 | 100% | 100% | 0 | 0.066 s |
| Offline simulator | 10,000 | 100% | 100% | 0 | 0.733 s |
| Offline simulator | 100,000 | 100% | 100% | 0 | 8.315 s |
| Offline simulator | 1,000,000 | 100% | 100% | 0 | 80.516 s |
| OpenCode / DeepSeek V4.1 Flash Free | 10 | 100% | 100% | 1 | 61.810 s |
| OpenCode / GLM 5.3 Flash Free | 10 | 100% | 100% | 5 | 72.734 s |
| OpenCode / Nemotron 3.5 Lightning Free | 10 | 70% | 70% | 8 | 422.343 s |
| Ollama / Qwen 3.5 9B | 10 | 70% | 70% | 1 | 158.462 s |
| OpenCode / DeepSeek V4.1 Flash Free | 100 | 99% | 99% | 6 | 746.011 s |

The simulator million-record result verifies the deterministic parser, tie-out, and ratio-scoring path at that scale. It is **not** a million-record LLM benchmark. Model results at 10 records remain small pilots; DeepSeek’s 100-record result is the only 100-record LLM run. No 1,000-record or 1,000,000-record LLM run has been completed. The synthetic statement format uses plainly labeled line items, so this cohort measures line-item retrieval rather than full 10-K layout, notes search, or citation fidelity. Human Gate 1 decisions remain pending in the blinded review worksheets.

OpenCode usage was reconciled from its local session exports; totals include reported input, cache, output, and reasoning tokens. Paid spend is tracked in `results/spend-ledger.json` against the approved $2.00 cap.

## Paid-call budget probe and matched-cohort rule

On October 21, 2026, a DeepSeek V3.2 OpenRouter budget probe made one completed synthetic-record call ($0.000681; 733 prompt and 614 completion tokens) and one interrupted in-flight call charged at its conservative reservation ($0.001288). Total ledger spend is $0.001969, with no reservation outstanding. The first call projects to about $6.81 for 10,000 records at the observed usage, while the preflight maximum-output reservation is about $12.48. The 10,000-record corpus cannot be run through a paid model within the $2 cap. The interrupted run produced no benchmark result and must not be charted. All future cross-model comparisons must use identical input and ground-truth hashes for every model; do not compare different sample sizes or cohort types.
