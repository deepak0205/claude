# Data Governance Policy

## Core Principles

This dashboard is designed for **operational inventory management only**. It does not handle patient data, clinical decisions, or regulated medical information.

## Data Requirements

### ✅ Permitted Data
- Medicine SKU/product code
- Expiry dates
- Current stock quantity
- Reorder points and maximum stock levels
- Warehouse/location identifiers
- Synthetic timestamps for testing

### ❌ Prohibited Data
- Patient names, medical record numbers, or identifiers
- Diagnoses, dosages, or treatment protocols
- Prescribing information or clinical guidelines
- Employee personal data
- Supplier payment information or credentials
- Real historical transaction data containing the above

## Data Minimisation

Store only the fields necessary for inventory decisions:

```
medicine_inventory {
  sku: string           # Product identifier
  name: string          # Generic drug name only
  expiry_date: date     # Expiry tracking
  current_stock: int    # Quantity on hand
  reorder_level: int    # Trigger for replenishment
  max_stock: int        # Storage capacity limit
  warehouse: string     # Location identifier
}
```

No other fields are collected or stored.

## File Validation

All input files must be validated before processing:

1. **Schema validation**: Columns match expected structure
2. **Type validation**: Dates are valid, quantities are non-negative integers
3. **Range validation**: Stock levels within reasonable bounds
4. **Encoding validation**: UTF-8 text, no embedded credentials
5. **Rejection**: Invalid files are rejected with clear error messages; no partial processing

## Calculation Transparency

Every risk score and alert must be reproducible:

- Document the formula used (e.g., "Expired or low-stock critical medicine = CRITICAL RISK")
- Show the calculation inputs to the user
- Provide an audit trail showing which rules triggered
- Allow users to understand why an alert was raised

Example:
```
Medicine: Penicillin
Expiry: 2024-12-31
Today: 2024-12-15
Days to expiry: 16
Risk: EXPIRING SOON (within 30 days)
Rule triggered: Days to expiry < 30
```

## Data Lineage

Track the origin of all data:

- Input file name and timestamp
- Processing steps applied (e.g., "Validated schema → Calculated risk scores → Filtered critical items")
- Any transformations or lookups used
- Version of risk calculation rules applied

Store lineage in session memory only; do not persist between sessions.

## Session-Only Processing

- All calculations are recomputed on each session load
- No caching of sensitive intermediate results
- No persistent storage of risk scores or alerts
- Each user session is independent
- No cross-session data retention

## Human Review of Critical-Risk Results

Before any action on critical-risk items (e.g., destruction or reorder of expired or low-stock critical medicines):

1. System raises alert with full calculation details
2. Authorized person reviews the alert
3. Person manually verifies data is correct
4. Person approves or rejects action
5. Audit log records who reviewed and when

Example critical scenarios:
- Any expired medicine (expiry date < today)
- Critical medicine with current stock < reorder level
- Any medicine below reorder level for more than 7 days

## Application Limitations

This application is NOT:
- A regulated medical device
- Suitable for prescribing or clinical decisions
- A substitute for regulatory compliance audits
- Authorized to modify inventory without human approval

This application IS:
- A dashboard for operational visibility
- A source of suggestions for inventory managers
- A tool for identifying stock anomalies
- Subject to local pharmaceutical regulations and audit requirements

**Users must verify all recommendations with their organization's pharmacist or inventory manager before taking action.**
