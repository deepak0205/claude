# Pharma Project Analytics

## Project Purpose

A professional Streamlit dashboard for medicine inventory, expiry, and stock-risk analytics. Provides real-time visibility into pharmaceutical stock health, expiry tracking, and automated risk alerts.

**Scope:** Inventory management and operational analytics only. No patient data, clinical data, or medical advice.

## Tech Stack

- **Python 3.9+** — Core language
- **Pandas** — Data manipulation and analysis
- **Plotly** — Interactive visualizations
- **Streamlit** — Dashboard framework
- **Pytest** — Unit and integration testing

## Modular Coding Standards

- Single responsibility: Each module handles one concern (data loading, calculations, UI, validation)
- Clear interfaces: Functions have documented inputs/outputs, no implicit state
- No mixed concerns: Keep data logic separate from UI logic
- Testable units: Functions must be independently testable with known inputs
- Type hints: All public functions include type annotations

## Testing Requirements

- **Unit tests**: All business logic (calculations, validations, risk scoring)
- **Data tests**: File format validation, edge cases, boundary conditions
- **Integration tests**: Data pipeline end-to-end with synthetic fixtures
- **Coverage**: Minimum 80% for critical paths (risk calculations, data validation)
- **Test data**: Synthetic only; no real inventory or pharmaceutical data

## Security Rules

- No credentials in code; use environment variables with validation
- No shell command execution
- No external API calls outside approved domains
- Validate all external data before processing
- Sanitize user inputs before display
- No logging of sensitive values (stock levels of critical medicines require audit trail)

## Data Governance Rules

- **Synthetic data only**: All test and demo data is generated, never from real sources
- **No personal data**: No patient, employee, or facility identifiers
- **No clinical data**: No diagnoses, dosages, treatment protocols, or medical advice
- **Data minimisation**: Only track essential fields (SKU, expiry, current stock, reorder level)
- **Calculation transparency**: All risk calculations are documented and reproducible
- **Data lineage**: Track source of each data point in audit logs
- **Session-only processing**: No persistent storage of sensitive calculations; recompute on each session
- **Human review**: Critical-risk medicines require manual verification before action

## Definition of Done

- Feature has passing unit tests
- Business logic reviewed by pharma-auditor subagent
- Security checklist passed (no credentials, no shell commands, inputs validated)
- Governance compliance verified (synthetic data, no personal/clinical data)
- Code follows modular standards (testable, clear interfaces, type hints)
- UI follows professional standards (accessible, responsive, clear)
- Documentation updated in code comments and docs/
- Test coverage reported in docs/PROGRESS.md
