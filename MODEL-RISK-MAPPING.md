# Prototype controls and supervisory model-risk principles

This is a research crosswalk, not a bank model-risk review, regulatory validation, legal interpretation, or compliance claim. The source case study is a developer-built prototype tested on one public Microsoft filing. Its generative AI workflow is not validated for credit use.

## Current guidance

The Federal Reserve's April 17, 2026 SR 26-2 letter issued revised interagency guidance and **superseded SR 11-7**. The guidance takes a risk-based approach and says practices should fit the model's purpose, exposure, and the organization's risk profile. It is supervisory guidance, not a prescriptive compliance checklist. It also says generative and agentic AI are outside the guidance's scope, while organizations should use their governance practices to determine appropriate controls for systems not covered. The simple deterministic ratio formulas are not themselves models under the guidance's definition of model.

Sources: [SR 26-2 letter](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm) and the [revised model-risk guidance](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm).

## Bounded crosswalk

| Prototype control or evidence | Related supervisory principle | What this project does not establish |
| --- | --- | --- |
| Stated purpose: retrieve filing figures for a memo; the AI does not decide credit or assign risk ratings | Align development and use to the stated purpose; make limitations clear | Suitability for any production purpose, portfolio, exposure, or bank risk tier |
| Seeded synthetic source defects, held-out clean truth, exact extraction checks, and negative tests | Development testing should assess performance, data relevance, inputs, assumptions, and limitations | Real-world defect prevalence, filing diversity, external validity, or outcomes against actual lending results |
| Versioned prompts/schema, run logs, fixed answer key, and regression checks | Documentation and reproducible validation evidence support model governance | Independent validation or effective challenge by an appropriately expert and independent reviewer |
| Gate 1 checklist, approval/send-back, missing-data block, and escalation path | Clear roles, accountability, and controls around model use | Reviewer effectiveness, workload, false approvals, or independence; benchmark review worksheets remain uncompleted |
| Deterministic tie-out, ratio formulas, input guards, and separate scoring | Process verification and controls can help detect failures; deterministic arithmetic is distinct from a statistical model | That a passed tie-out proves source authenticity, semantic mapping, or correct extraction |
| Explicitly recorded failures, output truncation, and known limitations | Validation should identify limitations and errors and inform appropriate use | Ongoing monitoring, production thresholds, drift detection, back-testing, or outcome analysis; no production series exists |
| Foundry workflow retirement notice and migration planning | Governance should account for lifecycle changes and third-party dependencies | A completed or tested migration; the Foundry workflow has not been ported |

The source guidance's applicability depends on the banking organization's profile, exposure, and use. This crosswalk only identifies relevant ideas to investigate; it does not say the prototype satisfies them.
