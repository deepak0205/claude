CLAUDE.md — Pharma Data Anomaly Detection
1. Purpose

Build an explainable anomaly-detection solution for synthetic pharmaceutical data.

The system should detect:

Data-quality anomalies
Manufacturing batch anomalies
Inventory anomalies
Quality-control anomalies
Shipment anomalies
Temperature excursions
Clinical-trial supply anomalies

The solution must be:

Explainable
Reproducible
Testable
Auditable
Lightweight
Suitable for Streamlit deployment
2. Scope

Synthetic pharma domains:

Product/material master
Manufacturing batches
Inventory movements
Clinical-trial supply
Quality measurements
Shipments
Temperature observations

Supported anomaly types:

Missing or malformed data
Duplicate business keys
Referential-integrity failures
Invalid dates/event sequences
Negative or unusual quantities
Quality measurements outside limits
Temperature excursions
Time-series spikes
Unusual product/site/batch behavior

Out of scope: patient diagnosis, treatment recommendations, and clinical decision-making.

3. Project Structure
pharma-anomaly/
├── CLAUDE.md
├── data/
│   ├── synthetic/
│   ├── raw/
│   └── processed/
├── src/
│   ├── data_generation.py
│   ├── validation.py
│   ├── features.py
│   ├── detection.py
│   ├── scoring.py
│   └── explain.py
├── app/
│   └── streamlit_app.py
├── tests/
│   ├── test_data_quality.py
│   ├── test_detection.py
│   └── test_scoring.py
├── config/
│   └── rules.yml
└── requirements.txt
4. Skills
4.1 Data Engineering
Profile schema, nulls, duplicates, distributions, and relationships.
Validate schema before processing.
Preserve raw/source columns.
Create derived features separately.
Use product, site, batch, and time dimensions for baselines.
Prefer deterministic transformations.
4.2 Anomaly Detection
Use business rules for known constraints.
Use IQR or robust z-score for numerical outliers.
Use rolling baselines for time-series anomalies.
Use Isolation Forest when unsupervised detection is appropriate.
Combine signals into an explainable anomaly score.
Keep thresholds configurable.
4.3 Explainability

Every anomaly should contain:

anomaly_id
business_key
anomaly_type
severity
score
detection_method
reason
observed_value
expected_value
detection_timestamp
4.4 Testing
Test normal records.
Test deliberately injected anomalies.
Test nulls and duplicates.
Test boundary conditions.
Test empty/malformed datasets.
Use fixed seeds for synthetic data.
5. Subagents

Subagents are logical specialized roles used by Claude during development. They do not require separate applications.

5.1 Data Quality Agent

Purpose: Identify data-quality issues before anomaly detection.

Responsibilities:

Profile datasets.
Detect schema violations.
Detect nulls and duplicates.
Validate relationships.
Generate quality findings.

Output:

quality_issue
column
record_key
severity
reason
recommended_action
5.2 Feature Engineering Agent

Purpose: Create reliable anomaly-detection features.

Responsibilities:

Create rolling averages and deviations.
Calculate quantity/frequency changes.
Create product/site/batch aggregates.
Create time-based features.
Prevent data leakage.

Rules:

Never modify raw data.
Store derived features separately.
Keep transformations reproducible.
5.3 Pharma Anomaly Detection Agent

Purpose: Detect operational anomalies.

Responsibilities:

Apply configured business rules.
Detect inventory anomalies.
Detect batch anomalies.
Detect quality anomalies.
Detect shipment anomalies.
Detect temperature excursions.
Detect unusual time-series behavior.

Output:

anomaly_id
business_key
anomaly_type
score
severity
detection_method
reason
observed_value
expected_value
5.4 Statistical Detection Agent

Purpose: Detect anomalies not captured by deterministic rules.

Responsibilities:

Apply IQR/robust z-score.
Build rolling baselines.
Use Isolation Forest where appropriate.
Tune thresholds using the synthetic test set.
Record method and threshold.

Prefer interpretable methods where possible.

5.5 Pharma Domain Review Agent

Purpose: Review whether detection logic is business-plausible.

Responsibilities:

Review batch lifecycle rules.
Review inventory assumptions.
Review quality limits.
Review shipment/temperature rules.
Identify unrealistic synthetic assumptions.

Do not invent regulatory requirements.

5.6 Anomaly Explanation Agent

Purpose: Explain detected anomalies.

Responsibilities:

Explain why a record was flagged.
Compare observed vs expected behavior.
Identify detection method.
Generate concise investigation notes.

The agent must never invent evidence.

5.7 Test Agent

Purpose: Validate detection quality.

Responsibilities:

Generate normal/anomalous fixtures.
Inject known anomalies.
Run unit/integration tests.
Calculate precision, recall, F1, and false-positive rate.
Detect regressions.
Verify reproducibility.
5.8 Streamlit Review Agent

Purpose: Validate the anomaly dashboard.

Responsibilities:

Review file upload.
Review filters and tables.
Review anomaly summaries.
Review explanations.
Review charts.
Review downloads.
Check for data exposure.
6. Subagent Workflow
Synthetic Data
      ↓
Data Quality Agent
      ↓
Feature Engineering Agent
      ↓
 ┌───────────────┬──────────────────┐
 ↓               ↓                  ↓
Rule Detection   Statistical        Domain
Agent            Detection Agent    Review Agent
 └───────────────┴──────────────────┘
                 ↓
        Explanation Agent
                 ↓
            Test Agent
                 ↓
       Streamlit Review Agent

Rules:

Each subagent has one primary responsibility.
Return structured outputs.
Do not duplicate responsibilities.
Detection agents must not modify raw data.
Explanation agents use only available evidence.
Domain agents flag assumptions rather than invent rules.
Test agents validate every new detection rule.
The main Claude agent coordinates the workflow.
7. Guardrails
7.1 Data
Use synthetic data only.
Never commit real patient or proprietary data.
Never copy production records into test fixtures.
Never store credentials or tokens in source code.
Never expose secrets in Streamlit.
Treat identifiers as synthetic unless verified.
7.2 Pharma
Do not diagnose patients.
Do not recommend treatment.
Do not infer clinical outcomes.
Do not claim regulatory compliance based only on tests.
Escalate regulatory/domain decisions to qualified owners.
7.3 Detection
Flag anomalies; never automatically delete records.
Preserve evidence for every anomaly.
Store rule/model version with results.
Avoid one global threshold when populations have different baselines.
Document assumptions.
7.4 Engineering
No destructive operations without approval.
Do not weaken tests to make them pass.
Do not silently swallow exceptions.
Fail clearly on missing required columns.
Prefer small, reusable functions.
8. Hooks
8.1 Pre-edit
Restrict edits to repository files.
Protect credential files.
Protect production configuration.
8.2 Post-edit

Run targeted tests for changed modules.

8.3 Pre-commit
python -m pytest -q
python -m compileall src app
8.4 Pre-deploy

Verify:

Synthetic-only data
No secrets
Passing tests
Successful Streamlit startup
No production endpoints

Security-sensitive checks should fail closed.

9. Synthetic Data

Generate deterministic synthetic data using a fixed seed.

Products
product_id
product_type
unit
Batches
batch_id
product_id
site_id
manufacture_date
expiry_date
Inventory
batch_id
site_id
event_ts
event_type
quantity
Quality
batch_id
test_name
test_ts
result
lower_limit
upper_limit
Shipments
shipment_id
batch_id
origin
destination
event_ts
temperature_c
10. Anomaly Test Set

Inject at least:

Duplicate batch identifier
Missing product reference
Expiry before manufacture date
Negative inventory quantity
Inventory spike versus rolling baseline
Quality result outside specification
Temperature excursion
Duplicate shipment event
Impossible shipment chronology
Sudden event-frequency increase

Recommended split:

70% Normal
15% Rule anomalies
10% Statistical/time-series anomalies
5% Edge cases

Ground-truth labels must remain separate from production detection inputs.

11. Testing
11.1 Unit Tests

Test:

Schema validation
Null handling
Duplicate detection
Date validation
Quantity validation
Quality limits
Temperature excursions
Rolling baselines
Anomaly scoring
Explanation generation
11.2 Integration Tests

Verify:

Generation
    ↓
Validation
    ↓
Features
    ↓
Detection
    ↓
Scoring
    ↓
Explanation
    ↓
Output

Verify that:

Every anomaly has a reason.
Every anomaly has a detection method.
Results are reproducible.
Empty inputs fail predictably.
Malformed schemas fail clearly.
Streamlit loads results.
12. Test Metrics

Track:

Precision
Recall
F1 score
False-positive rate
Anomaly coverage by type

Initial synthetic targets:

Rule anomaly recall       >= 95%
Overall false-positive    <= 10%
Explanation completeness  = 100%

These are engineering benchmarks only and are not production validation criteria.

13. Detection Pipeline
Synthetic Data
      ↓
Schema Validation
      ↓
Data Quality Checks
      ↓
Feature Engineering
      ↓
Rule Detection
      ↓
Statistical Detection
      ↓
Anomaly Scoring
      ↓
Severity Classification
      ↓
Explanation
      ↓
CSV/Parquet Output
      ↓
Streamlit Dashboard

Severity:

LOW      → Unusual but limited impact
MEDIUM   → Requires investigation
HIGH     → Strong anomaly / potential process impact
CRITICAL → Immediate review
14. Configuration

Never hard-code business thresholds.

Example:

quality:
  enabled: true

temperature:
  excursion_c: 8

inventory:
  rolling_window: 30
  z_threshold: 3.5

scoring:
  high: 0.75
  critical: 0.90

These are synthetic defaults and require domain review before reuse.

15. Governance

Track:

Dataset version
Schema version
Rule/model version
Configuration version
Synthetic-data seed
Code commit/version
Run timestamp
Detection method
Thresholds

Retain:

Input metadata
Validation summary
Detection output
Warnings
Errors

Any detection-logic change requires:

Change rationale
Impacted anomaly types
Test evidence
Reviewer/owner
Effective version

Never present synthetic performance as production validation.

16. Streamlit Deployment

The application should provide:

CSV/Parquet upload
Dataset preview
Data-quality summary
Total anomaly count
Anomaly count by severity/type
Filterable anomaly table
Basic trend chart
Explanation panel
Downloadable anomaly results

Run locally:

streamlit run app/streamlit_app.py

Keep deployment lightweight:

CPU-friendly algorithms
Minimal dependencies
Cached reference data
Environment variables for configuration
No secrets in UI
Synthetic data for demos

Suitable deployment:

Streamlit Community Cloud
or
Containerized Streamlit deployment
17. Definition of Done

A feature is complete only when:

Synthetic data is used.
Schema validation exists.
Detection logic has positive/negative tests.
Results are explainable.
Results are reproducible.
Thresholds are configurable.
No secrets are introduced.
No real pharma/patient data is introduced.
Relevant tests pass.
Streamlit starts successfully.
Governance/version information is updated.
18. Claude Working Rules
Inspect existing code before adding modules.
Reuse existing utilities before adding dependencies.
Prefer small, reusable functions.
Keep detection explainable.
Keep synthetic data deterministic.
Add tests whenever detection logic changes.
Never invent pharma business rules.
Document assumptions requiring domain review.
Preserve compatibility unless a breaking change is requested.
Use synthetic examples in documentation.
Prefer safe, minimal changes over broad refactoring.
Never trade data integrity or security for convenience.
After implementation, summarize changed files, tests run, and known limitations.