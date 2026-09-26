# Development Plan — Elation Health Chart-Summary Feature (Claude Integration)

Based on [elation-health-hld-lld.md](elation-health-hld-lld.md). Each phase produces a concrete deliverable and a go/no-go checkpoint before the next phase starts.

---

### Phase 0 — Requirements & Compliance Sign-off
- Confirm BAA coverage (Anthropic direct or Bedrock) before any real PHI touches the model.
- Security/privacy review of the de-identification approach in the LLD.
- Define the non-functional targets to hit: <3s perceived latency, 61%-reduction target as the success bar.
- **Deliverable:** signed-off requirements doc + compliance checklist.
- **Go/no-go:** no PHI flows until this phase is approved.

### Phase 1 — Prompt & Data-Contract Prototyping (no real PHI)
- Build the prompt template and output JSON schema from the LLD against **synthetic** patient records.
- Iterate until summaries are consistently accurate, correctly flag med/lab changes, and never hallucinate beyond provided data.
- **Deliverable:** finalized prompt template + output schema, validated against a synthetic test set.
- **Go/no-go:** summary quality meets a defined accuracy bar on synthetic cases.

### Phase 2 — Chart-Summary Service Skeleton
- Stand up the service with a mocked Elation data layer (`GET` patient bundle → assemble context → call model → return structured JSON).
- Implement the de-identification/tokenization boundary described in the LLD.
- **Deliverable:** working service behind `POST /internal/chart-summary/{patientId}`, backed by mock data.

### Phase 3 — Claude Integration
- Wire the real model call (Bedrock or direct API) with the finalized prompt/schema from Phase 1.
- Implement caching (per patient/encounter/data-version-hash) and the async pre-warm option.
- Implement error handling table from the LLD (timeout, malformed response, insufficient-data case).
- **Deliverable:** service returns live model-generated summaries end-to-end against mock/staging data.

### Phase 4 — Security & Audit Layer
- Encrypted short-retention store for prompt/response references; audit log entries (clinician ID, patient ID, model version, timestamp) without raw PHI in plaintext logs.
- Access control inherited from existing Elation tenant/clinician auth.
- **Deliverable:** audit trail verified end-to-end in a security review.

### Phase 5 — Frontend Integration
- Add the "Chart Summary" panel to the chart-review screen, rendering the structured JSON deterministically (not raw prose).
- Add the feedback control (flag inaccurate/incomplete summary).
- **Deliverable:** clinician-facing UI wired to the live service in a staging environment.

### Phase 6 — Pilot
- Single specialty, small clinician cohort, summary shown non-blocking alongside full chart.
- Measure: chart-review time before/after, flag rate, latency (p50/p95), adoption rate.
- **Deliverable:** pilot metrics report against the Phase 0 success bar.
- **Go/no-go:** pilot metrics must approach the target reduction before wider rollout.

### Phase 7 — Phased Rollout
- Expand specialty-by-specialty (mirrors Banner Health's phased approach), tuning prompt/schema per specialty's chart conventions.
- Continuous feedback loop from flagged summaries into prompt/schema revisions.
- **Deliverable:** default-on rollout across the platform, with metrics dashboard live.

---

## Sequencing note
Phases 0–1 have no PHI exposure and can start immediately. Phase 2 onward requires the compliance sign-off from Phase 0. Frontend work (Phase 5) can be built in parallel with Phase 3–4 against mocked service responses to shorten the critical path.

## Decision point for review
This plan assumes we're building a **prototype/demo** of the feature described in the HLD/LLD (not modifying Elation's actual production system, which we don't have access to). Confirm that's the right scope before Phase 2 starts — if the goal is a real production integration with Elation, this plan would need their actual API/data contracts substituted in for the mocked assumptions.
