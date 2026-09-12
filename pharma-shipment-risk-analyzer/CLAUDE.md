CLAUDE.md — Mini Pharma Shipment Risk Analyzer
1. Purpose
Build a small, explainable Streamlit app that reads the supplied pharma supply-chain Excel file, identifies high-risk shipments, and provides evidence-based recommendations. Priority: correctness, explainability, simplicity, speed. This is an operational demo, not a clinical system.
2. Requirements
The app must allow Excel upload and display:
    1. Total shipments
    2. High-risk shipment count
    3. Temperature-excursion shipments
    4. Top 5 highest-risk shipments
    5. Risk-distribution chart
    6. Short AI-style recommendation Do not add unnecessary features.
3. Input Data
Inspect the actual workbook before coding. Likely fields: shipment_id, product_id, batch_id, origin, destination, ship_date, delivery_date, temperature_min, temperature_max, allowed_temp_min, allowed_temp_max, delay_days, quantity Validate required columns at runtime. Optional columns must not break the app. Never fabricate business data.
4. Architecture
Use a minimal structure:
project/
├── CLAUDE.md
├── app.py
├── tests/
│   └── test_app.py
├── data/
│   └── synthetic/
└── requirements.txt
Keep business logic separate from Streamlit UI where practical.
5. Risk Detection
Use simple, deterministic, explainable rules.
Temperature
Flag excursion when: temperature_min < allowed_temp_min OR temperature_max > allowed_temp_max
Delay
Flag delay when: delay_days > configured_delay_threshold
Quantity
Detect unusual quantity using IQR or another simple explainable statistical method. Do not introduce ML unless clearly justified by the dataset.
Score
Default weights:
    • Temperature excursion: +50
    • Significant delay: +25
    • Quantity anomaly: +15
    • Critical missing data: +10 Cap at 100. Risk levels:
    • 0–29 LOW
    • 30–59 MEDIUM
    • 60–79 HIGH
    • 80–100 CRITICAL Centralize thresholds/configuration. Do not invent unsupported risk signals.
6. Explainability
Each shipment should produce: shipment_id, risk_score, risk_level, temperature_excursion, delay_risk, quantity_risk, risk_reason Every HIGH/CRITICAL result must state:
    • What happened
    • Why it is risky
    • Detection rule/method
    • Observed value
    • Expected value or threshold Never generate unsupported evidence.
7. Streamlit
Create app.py. Provide:
    • .xlsx / .xls uploader
    • Three KPI cards: total, high-risk, temperature excursions
    • Top-5 table: shipment ID, score, level, reason
    • One LOW/MEDIUM/HIGH/CRITICAL distribution chart
    • One concise recommendation section Run with: streamlit run app.py Keep the UI simple and suitable for a 20-minute demo.
8. Skills Decision
No separate custom Skill is required. The required capabilities are small enough to define here:
    • Excel/data analysis
    • Shipment risk analysis
    • Explainability
    • Streamlit
    • Testing Create a reusable Skill only if this workflow will be repeated across projects.
9. Subagent Decision
Do not create multiple custom subagents. Use one logical role when useful:
Risk Reviewer
Review the completed implementation for:
    • Correct risk calculations
    • Temperature/delay/quantity logic
    • Ranking correctness
    • Missing-value handling
    • Explanation accuracy
    • Evidence-based recommendations
    • Absence of clinical claims The main Claude agent owns implementation. Avoid subagent complexity that does not improve the demo.
10. Hooks
Use only lightweight validation:
    • After code changes: python -m py_compile app.py
    • Before completion: python -m pytest -q If tests do not exist, create them. Do not create complex hooks for this exercise.
11. Guardrails
Data
    • Synthetic/demo pharma data only.
    • Never use or expose patient-identifiable information.
    • Never commit production data.
    • Never modify the source workbook.
    • Never fabricate missing values.
    • Never expose secrets.
Pharma
This is operational shipment-risk analysis only. Do not:
    • Diagnose patients
    • Recommend treatment
    • Make clinical decisions
    • Determine product safety
    • Automatically approve/reject products
    • Claim regulatory compliance Risk results require human review.
Engineering
    • Validate before processing.
    • Fail clearly on missing required columns.
    • Do not silently swallow exceptions.
    • Do not automatically delete or alter records.
    • Prefer deterministic, minimal solutions.
12. Data Validation
Before analysis:
    1. Confirm workbook is readable.
    2. Inspect sheets and columns.
    3. Validate required fields.
    4. Parse dates safely.
    5. Convert numeric fields safely.
    6. Handle nulls explicitly.
    7. Detect duplicate shipment IDs.
    8. Report validation errors clearly. Never silently fill missing business values.
13. Synthetic Test Set
Create deterministic cases for:
    1. Normal shipment
    2. Temperature excursion
    3. Delayed shipment
    4. Quantity anomaly
    5. Temperature + delay
    6. Missing temperature
    7. Missing shipment ID
    8. Duplicate shipment
    9. Extreme temperature
    10. Multiple high-risk shipments Use a fixed seed for generated data.
14. Testing
Minimum tests: test_total_shipments test_temperature_excursion test_delay_risk test_quantity_anomaly test_risk_score test_risk_classification test_top_5_shipments test_missing_columns test_missing_values Verify:
    • Counts are correct.
    • Excursions are correctly detected.
    • Scores are reproducible.
    • Risk levels are correct.
    • Top 5 is correctly ranked and contains at most five rows.
    • Invalid input gives a useful error.
15. Configuration
Keep business thresholds in one location, for example:
RISK_CONFIG = {
    "delay_threshold_days": 2,
    "temperature_weight": 50,
    "delay_weight": 25,
    "quantity_weight": 15,
    "missing_data_weight": 10
}
Do not scatter thresholds across the application.
16. Recommendation Logic
Recommendations must be based only on detected evidence. Temperature: "Temperature excursions are the primary risk driver. Review affected shipments and verify cold-chain handling." Delay: "Delivery delays are a significant risk driver. Review affected routes and investigate recurring delivery bottlenecks." Quantity: "Unusual shipment quantities were detected. Review affected shipments against expected product and batch quantities." Low risk: "No major shipment-risk pattern was detected. Continue routine monitoring." Never invent causes, facts, or operational events.
17. Governance
Maintain: dataset_type: synthetic risk_logic_version application_version configuration_version Any risk-logic change requires:
    • Updated tests
    • Version update
    • Change rationale Do not present synthetic results as production validation.
18. Security
Never place API keys, passwords, tokens, database credentials, or production URLs in source code. Use environment variables for external configuration. Do not expose secrets through UI, logs, errors, or downloads.
19. Performance
Preferred stack: Python, Pandas, OpenPyXL, Streamlit, Matplotlib/Plotly, Pytest Avoid large ML frameworks, databases, complex APIs, unnecessary cloud services, and model training that does not add value. Process the demo workbook locally.
20. Definition of Done
Complete only when:
    • Excel upload works.
    • Validation works.
    • All six required outputs are displayed.
    • High-risk records are explainable.
    • Synthetic tests pass.
    • Streamlit starts successfully.
    • No real patient/proprietary data or secrets are present.
21. Claude Working Rules
    1. Inspect the workbook before implementing assumptions.
    2. Build the smallest solution satisfying the requirements.
    3. Prefer deterministic rules over unnecessary ML.
    4. Do not create Skills, subagents, or hooks merely for demonstration.
    5. Reuse existing code where possible.
    6. Centralize risk thresholds.
    7. Add tests for every risk rule.
    8. Never invent data or pharma business rules.
    9. Mark assumptions requiring domain review.
    10. Never make clinical or regulatory claims.
    11. Keep the original workbook unchanged.
    12. Use synthetic data for demonstrations and tests.
    13. Fix implementation errors; never weaken tests to pass.
    14. Verify the Streamlit app before completion.
    15. Report files changed, tests run, risk logic, and known limitations.
22. Success Criteria
Demonstrate this workflow: Understand → Inspect Excel → Validate → Design rules → Score risk → Test → Build Streamlit → Explain risks → Recommend actions Design principle: small, explainable, safe, and production-minded without over-engineering.
