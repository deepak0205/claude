# Elation Health × Claude — HLD & LLD

> Note: Elation's internal architecture isn't publicly documented beyond "Claude reduces chart review time by 61%." This design is a reasonable inferred architecture for how a Claude-in-EHR chart-review feature would be built, based on the public case study, standard EHR integration patterns, and HIPAA-compliant AI deployment practice. Treat implementation-level specifics as assumptions to validate with Elation, not confirmed fact.

---

## High-Level Design (HLD)

### 1. Goal
Reduce clinician time spent on chart review inside Elation's primary-care EHR by having Claude pre-digest a patient's chart (history, notes, labs, meds) into a concise, clinically structured summary the clinician reviews instead of the raw record.

### 2. System Context

```
┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
│  Clinician   │◄────►│  Elation EHR Web  │◄────►│  Elation Backend    │
│  (browser)   │      │  App (existing)   │      │  (patient records,  │
└─────────────┘      └──────────────────┘      │  auth, audit)       │
                                                 └─────────┬───────────┘
                                                           │
                                                 ┌─────────▼───────────┐
                                                 │  Chart-Summary       │
                                                 │  Service (new)       │
                                                 └─────────┬───────────┘
                                                           │ de-identified /
                                                           │ tenant-scoped PHI
                                                           ▼
                                                 ┌──────────────────────┐
                                                 │  Claude API           │
                                                 │  (Bedrock / direct,   │
                                                 │  BAA-covered)         │
                                                 └──────────────────────┘
```

### 3. Major Components
- **Elation EHR Web App** — existing product surface; adds a "Chart Summary" panel to the chart-review screen. No new login, no new workflow.
- **Chart-Summary Service** — new backend service that assembles patient context (encounter notes, problem list, meds, labs, historical visits) into a structured prompt.
- **Claude API layer** — model calls go through a HIPAA-eligible path (AWS Bedrock or Anthropic direct API under a BAA), never client-side.
- **Audit & Logging** — every summary generation logged with prompt/response references (not raw PHI in logs) for compliance traceability.
- **Feedback loop** — clinician can flag an inaccurate/incomplete summary, feeding a quality-monitoring pipeline.

### 4. Key Design Decisions
| Decision | Choice | Rationale |
|---|---|---|
| Where does the model call happen? | Server-side (Chart-Summary Service), never client-side | Keeps PHI off the browser/network edge and centralizes BAA compliance |
| Model access path | Bedrock (managed) over direct API | Matches Carta's pattern of "rapid, secure deployment"; simplifies key management, regional data residency |
| Summary is advisory, not authoritative | Clinician always sees/can expand full chart; summary is a starting point | Regulatory and clinical-safety requirement — AI does not replace clinical judgment |
| Latency budget | Summary generated on chart open, target < 3s perceived latency | Chart review is a high-frequency, time-sensitive workflow |

### 5. User Flow
1. Clinician opens a patient chart in Elation.
2. Chart-Summary Service pulls relevant structured + unstructured data for that patient.
3. Request sent to Claude with a clinical-summarization prompt template.
4. Structured summary (problem list changes, new labs of note, med changes, flagged risks) rendered above/alongside the raw chart.
5. Clinician reviews summary, expands to full chart as needed, signs off.
6. Optional: clinician flags summary quality → feedback pipeline.

---

## Low-Level Design (LLD)

### 1. Data Flow / Payload Construction
- **Input assembly:** Chart-Summary Service queries Elation's data layer for:
  - Active problem list
  - Medications (current + recently changed)
  - Last N encounter notes (structured + free text)
  - Recent labs/vitals outside normal range
  - Upcoming/overdue preventive care items
- **De-identification boundary:** Patient identifiers (name, MRN) are stripped or tokenized before leaving the Chart-Summary Service; a server-side mapping table re-associates the summary with the patient record after the response returns. (Reduces PHI surface even though the transport layer is already BAA-covered — defense in depth.)
- **Prompt template (illustrative):**
  ```
  System: You are assisting a primary care clinician reviewing a patient
  chart. Summarize only what is clinically relevant to today's visit.
  Do not speculate beyond the provided data. Flag any values outside
  normal range and any medication changes in the last 90 days.

  Data: {structured_json_bundle}

  Output format: {problem_list_delta, med_changes, flagged_labs,
  preventive_care_due, narrative_summary}
  ```
- **Output contract:** Claude returns a fixed JSON schema (not free text) so the frontend can render deterministic UI sections rather than parsing prose.

### 2. Service Interfaces
| Interface | Method | Notes |
|---|---|---|
| `POST /internal/chart-summary/{patientId}` | Elation frontend → Chart-Summary Service | Triggered on chart open; cached per encounter to avoid redundant calls |
| Chart-Summary Service → Claude | Model invocation | Server-to-server only; API key/IAM role scoped to this service, not shared broadly |
| `POST /internal/chart-summary/{patientId}/feedback` | Frontend → Chart-Summary Service | Thumbs down / correction reason, stored for QA review |

### 3. Caching & Performance
- Cache the generated summary per (patient, encounter, data-version-hash) — regenerate only if underlying chart data changed since last summary.
- Async pre-generation option: pre-warm the summary when a clinician's schedule loads for the day (reduces perceived latency to near-zero at chart open).

### 4. Security & Compliance
- All PHI in transit encrypted (TLS 1.2+); at rest encryption unchanged from existing Elation storage.
- BAA in place with Anthropic/AWS covering the model provider.
- No PHI used for model training (opt-out / zero-retention API tier).
- Audit log entry per summary: timestamp, clinician ID, patient ID (internal), model version, but **not** the raw prompt/response content in plaintext logs — store a reference ID to a short-retention encrypted store instead.
- Access control: Chart-Summary Service inherits Elation's existing per-clinician/tenant authorization — no new permission model needed.

### 5. Error Handling
| Failure | Behavior |
|---|---|
| Claude API timeout/error | Fall back silently to raw chart view (no summary panel); log incident |
| Malformed/incomplete JSON response | Discard, retry once, then fall back to raw chart view |
| Model flags data as insufficient | Return a "not enough data to summarize" state rather than guessing |

### 6. Rollout Plan
1. **Pilot:** Single specialty (e.g., internal medicine), small clinician cohort, summary shown alongside full chart (non-blocking).
2. **Validation:** Compare clinician time-on-chart before/after; collect flagged-summary feedback for prompt tuning.
3. **Expand:** Roll out specialty-by-specialty (mirrors Banner Health's phased-by-specialty approach), tightening the prompt/schema per specialty's chart conventions.
4. **Steady state:** Default-on for all clinicians on the platform; feedback loop continues to inform prompt/schema revisions.

### 7. Metrics to Track
- Chart review time per encounter (target: validate the reported 61% reduction)
- Summary flag/correction rate (quality proxy)
- Latency (p50/p95 time to render summary)
- Adoption rate (% of chart opens where clinician engages with summary vs. skips to raw chart)

---

## Assumptions to Validate with Elation
- Actual model access path (Bedrock vs. direct API) is not publicly confirmed for Elation specifically — inferred from Carta's stated pattern.
- Exact data elements included in the summarization context are not published.
- Whether de-identification/tokenization is actually used, or whether Elation relies solely on the BAA-covered transport, is unconfirmed.
