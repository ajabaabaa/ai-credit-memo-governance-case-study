# Governing an AI-Assisted Credit Memo Workflow

## Fork notice and attribution

This is a research fork of [KhanShrz/ai-credit-memo-governance-case-study](https://github.com/KhanShrz/ai-credit-memo-governance-case-study). The original case study, Foundry workflow, agent instructions, schema, test logs, answer key, exhibits, and PDF are KhanShrz's work and are retained in their original folders. This fork adds the separate `benchmark-v1/` research extension. First-person statements in the original case-study materials refer to their original author.

**Reuse:** the upstream repository did not include a license, and this fork does not grant reuse rights to the original materials. No license has been added to the extension; contact the respective authors before reusing either body of work.

The original case study describes a developer-led prototype and negative testing. It is not an independent bank model-risk review, regulatory validation, or evidence of compliance with supervisory guidance. See [the control-to-guidance mapping](MODEL-RISK-MAPPING.md) for a bounded discussion of related principles and evidence gaps.

> **Platform lifecycle:** Microsoft says Foundry declarative workflows retire on **December 1, 2026**. The original Foundry implementation is a research prototype and is not approved for production use. Portable materials include the exported workflow definition, prompts, JSON schema, formulas, and test cases; Foundry visual-canvas configuration, node bindings, retrieval-index connections, and runtime settings require deliberate migration and revalidation. Microsoft's current migration guidance points new development toward Microsoft Agent Framework. [Retirement and migration guidance](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/vs-code-agents-workflow-low-code).

The original case study by KhanShrz documents a small AI-assisted workflow that prepares the financial data behind a commercial credit memo, then subjects it to developer-led negative testing and control changes.

## Benchmark extension

- [Extension overview and evidence notes](BENCHMARK-EXTENSION.md)
- [Executive brief (PDF)](benchmark-v1/output/pdf/AI-Assisted-Credit-Memo-Governance-Executive-Brief.pdf)
- [Expanded article and research roadmap](benchmark-v1/article/AI-Assisted-Credit-Memo-Governance-Case-Study-and-Benchmark.md)
- [Architecture and Gate 1 approval diagram](benchmark-v1/figures/architecture-approval-flow.svg)
- [Interactive benchmark dashboard](benchmark-v1/dashboard/index.html)
- [Synthetic benchmark methods and reproduction guide](benchmark-v1/README.md)

## Read the original evidence

- [Original case study PDF](case-study/AI-Assisted-Credit-Memo-Case-Study.pdf)
- [Full test log](testing/test-log.md)
- [Workflow logic and formulas](workflow/workflow-logic.md)
- [Agent instructions](workflow/agent-instructions.md)
- [Financial extraction schema](workflow/schemas/financial_extract.json)
- [Answer keys](testing/answer-keys.md)
- [Exported Foundry workflow files](workflow/)

**Read the case study:** [case-study/AI-Assisted-Credit-Memo-Case-Study.pdf](case-study/AI-Assisted-Credit-Memo-Case-Study.pdf)

![Workflow diagram](exhibits/workflow-diagram.png)

## What it does

1. **Intake (AI):** captures the loan request and flags anything missing or suspicious.
2. **Data retrieval (AI):** pulls 16 financial figures from a company's 10-K, each with a page citation, or says NOT FOUND.
3. **Tie-out check (formula):** confirms the income statement figures add up before anyone reviews them.
4. **Gate 1 (human):** a reviewer approves the data or sends it back. After two send-backs, the case escalates to a senior credit officer. The system blocks approval if any figure is missing.
5. **Ratio calculator (formula):** computes five credit ratios, only after approval.

Test borrower: Microsoft Corporation, using its public FY2026 10-K ([SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019&type=10-K)). No customer or personal data was used.

## What testing found

- **The AI made up a number and cited a real page for it:** operating income of $188.3B instead of $155.2B. Fixed with a self-check, a formula tie-out and human spot checks.
- **It mapped the wrong line item:** lease interest reported as interest expense, which would have overstated interest coverage (60.9x vs. 50.9x).
- **A reviewer approved data that was entirely missing.** The workflow now blocks approval automatically when any figure is NOT FOUND.
- **A formula "passed" on empty data.** It now shows INPUT MISSING - FAIL instead.
- **Qualified result:** on one Microsoft FY2026 10-K, the test log records 36/36 checks for 12 requested values across three independent v4 text runs. A later v6 JSON playground retest recorded 96/96 checks for 16 items across three outputs, but the log says outputs two and three were identical and freshness was not confirmed. In workflow integration, the first v8 run returned 0/16 items; a rerun returned 16/16. Subsequent v9 normal and restoration runs matched all five deterministic ratios to the answer key. Correctness was version- and context-dependent; these single-borrower development tests are not an “every run” guarantee or a general accuracy estimate.

An independent review then pointed out the core dependency: every control still trusts a dataset the AI created. A governed financial-data source is the top step toward production (case study, section 8).

## Repository contents

| Folder | Contents |
| --- | --- |
| `case-study/` | The full case study (PDF) |
| `exhibits/` | Workflow diagram and test screenshots (Exhibits A to F) |
| `workflow/` | Exported Foundry workflow (YAML), agent instructions, JSON output schema, Power Fx formulas and workflow logic |
| `testing/` | Full test log and answer keys |

## Built with

- Microsoft Foundry (agents and visual workflows), no code
- Model: gpt-5.4-mini, version 2026-03-17
- Ratio and tie-out logic: Power Fx formulas inside the workflow

Note: Foundry workflows are scheduled for retirement on December 1, 2026. A production version would move to Azure Logic Apps or Microsoft Agent Framework.

## Status

Prototype. Developer testing complete for four built steps; research, memo drafting, a critic step and the final credit decision (Gate 2) are designed but not built. Not validated or approved for production use.

## Contributing

Please work on a branch and open a pull request rather than editing `main` directly, so each change can be reviewed.

## Disclaimer

A learning and portfolio project. Nothing here is credit, investment or financial advice.
