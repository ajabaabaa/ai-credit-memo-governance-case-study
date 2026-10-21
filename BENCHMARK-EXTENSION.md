# Benchmark V1 research extension

KhanShrz's original case study establishes the workflow and its initial negative tests. This separately authored Measure-stage extension asks what happens across controlled statement-quality variation, multiple extraction routes, larger batches, and explicit output-integrity and cost checks. It also identifies controls, especially human Gate 1 effectiveness, that still require measurement. The original case-study, workflow, test, and exhibit files remain unchanged; the research project lives under [`benchmark-v1/`](benchmark-v1/README.md).

## Read the work

- [Executive PDF briefing](benchmark-v1/output/pdf/AI-Assisted-Credit-Memo-Governance-Executive-Brief.pdf)
- [Research extension article and roadmap](benchmark-v1/article/AI-Assisted-Credit-Memo-Governance-Case-Study-and-Benchmark.md)
- [Reproducible benchmark and methods](benchmark-v1/README.md)
- [Interactive benchmark dashboard](benchmark-v1/dashboard/index.html)
- [Original case study PDF](case-study/AI-Assisted-Credit-Memo-Case-Study.pdf)
- Original workflow, schema, answer key, and tests remain in `workflow/` and `testing/`.

## Evidence boundary

The extension uses synthetic financial statements only. It preserves the original linear workflow and deterministic ratio definitions. It does not make credit decisions, and it does not add model swarms, JEV routing, or an alternate architecture.

The 10,000-record deterministic source-quality experiment and matched 24-record model screen are reported in the article. Two full 10,000-request model batches were output-truncated and produced no schema-complete records; they are not model accuracy results. The one-million-record run is simulator-only. Paid inference spend was $1.834534 of the $2 cap.

The one-million-row generated JSONL inputs are intentionally not tracked: their individual sizes exceed GitHub's 100 MiB file limit. The committed fixed seed, generator, manifest hashes, simulator results, and smaller cohorts support regeneration. Do not describe the million-row LLM benchmark as complete.

The mapping key for blinded Gate 1 worksheets is also kept out of the public fork until human review is complete. The blinded worksheets may be shared; publishing the key now would defeat the planned review.

## Attribution and licensing

This repository is a fork of [KhanShrz/ai-credit-memo-governance-case-study](https://github.com/KhanShrz/ai-credit-memo-governance-case-study). The upstream repository has no `LICENSE` file. The original case-study, workflow, testing, and exhibit files remain unchanged in this fork; the fork's root README adds attribution and a qualified summary of the original test log. This extension does not add a license to or claim ownership of the upstream work.
