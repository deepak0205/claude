# Data Dictionary - Pharmaceutical Inventory

## Overview

This document defines all data fields used in the pharma inventory management system. All data is **synthetic** for testing and development purposes only. No real pharmaceutical or personal data is included.

## Input Data Columns

### Required Fields

| Field | Type | Description | Example | Rules |
|-------|------|-------------|---------|-------|
| **Batch_ID** | String | Unique identifier for each medicine batch | BATCH-0001 | Must be unique, non-empty |
| **Expiry_Date** | Date (YYYY-MM-DD) | Date when batch expires and must be discarded | 2026-12-31 | Must be valid date, no future validation |
| **Current_Stock** | Integer | Number of units currently in inventory | 150 | Must be non-negative |
| **Reorder_Level** | Integer | Minimum threshold before reordering | 100 | Must be non-negative, typically < Maximum_Stock |
| **Maximum_Stock** | Integer | Maximum capacity for storage | 500 | Must be non-negative, typically > Reorder_Level |
| **Warehouse** | String | Physical location code | WH-North | Non-empty identifier |
| **Critical_Medicine** | String | Whether medicine is critical/life-saving | Yes / No | "Yes", "No", "true", "false" (case-insensitive) |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Medicine_Name** | String | Common or generic drug name | Aspirin |
| **Category** | String | Therapeutic category | Analgesic |
| **Manufacturer** | String | Company manufacturing the medicine | PharmaCorp |
| **Manufacturing_Date** | Date (YYYY-MM-DD) | Date of manufacture | 2025-01-15 |
| **Unit_Price** | Decimal | Cost per unit | 10.50 |

## Calculated Fields (Output)

All calculated fields are deterministic and reproducible based on input data and current date.

### Expiry Calculations

| Field | Type | Formula | Example |
|-------|------|---------|---------|
| **Days_To_Expiry** | Integer | (Expiry_Date - Today).days | -14, 0, 30, 365 |
| **Expiry_Status** | String | EXPIRED \| EXPIRING_SOON \| SAFE \| UNKNOWN | EXPIRED |

**Expiry Status Rules:**
- **EXPIRED**: Days_To_Expiry < 0
- **EXPIRING_SOON**: 0 ≤ Days_To_Expiry ≤ 30
- **SAFE**: Days_To_Expiry > 30
- **UNKNOWN**: Invalid or missing expiry date

### Stock Level Calculations

| Field | Type | Formula | Example |
|-------|------|---------|---------|
| **Stock_Status** | String | LOW_STOCK \| NORMAL \| OVERSTOCK \| UNKNOWN | LOW_STOCK |

**Stock Status Rules:**
- **LOW_STOCK**: Current_Stock < Reorder_Level
- **NORMAL**: Reorder_Level ≤ Current_Stock ≤ Maximum_Stock
- **OVERSTOCK**: Current_Stock > Maximum_Stock
- **UNKNOWN**: Invalid or missing stock levels

### Inventory Value

| Field | Type | Formula | Example |
|-------|------|---------|---------|
| **Inventory_Value** | Decimal | Current_Stock × Unit_Price | 1500.00 |

Represents total monetary value of current stock for this batch.

### Risk Scoring

| Field | Type | Range | Example |
|-------|------|-------|---------|
| **Risk_Score** | Integer | 0-100 | 90 |
| **Risk_Level** | String | CRITICAL \| HIGH \| MEDIUM \| LOW | CRITICAL |

**Risk Level Definition:**

The following conditions determine risk level:

**CRITICAL Risk** - Immediate action required:
- Expiry_Status = EXPIRED, OR
- Expiry_Status = EXPIRING_SOON AND Stock_Status = LOW_STOCK, OR
- Stock_Status = LOW_STOCK AND Critical_Medicine = Yes

**HIGH Risk** - Action needed soon:
- Expiry_Status = EXPIRING_SOON (with adequate stock), OR
- Stock_Status = OVERSTOCK, OR
- Stock_Status = LOW_STOCK (non-critical medicine)

**MEDIUM Risk** - Monitor and verify:
- Data quality issues detected (missing or invalid fields)

**LOW Risk** - No action needed:
- All other cases with valid, normal-range data

### Recommended Action

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Recommended_Action** | String | Human-readable action suggestion | Immediate disposal required. Verify with pharmacist before action. |

**Action categories:**
- Disposal/Destruction (for expired items)
- Reordering (for low stock)
- Usage acceleration (for expiring soon)
- Verification (for data quality issues)

## Data Quality Rules

### Validation Rules

1. **Date Validation**
   - Format: YYYY-MM-DD only
   - No future dates beyond reasonable bounds (365+ days in future acceptable)
   - Manufacturing_Date should be before Expiry_Date (warning if violated)

2. **Numeric Validation**
   - Stock levels must be non-negative integers
   - Unit prices must be positive decimals
   - Logical relationship: Reorder_Level < Maximum_Stock (warning if violated)

3. **Field Relationships**
   - Current_Stock should typically be between Reorder_Level and Maximum_Stock
   - Current_Stock > Maximum_Stock triggers OVERSTOCK warning
   - Current_Stock < Reorder_Level triggers LOW_STOCK warning

4. **Uniqueness**
   - Batch_ID must be unique per inventory snapshot
   - Duplicate Batch_IDs trigger warning

5. **Critical Field Validation**
   - Batch_ID: Required, non-empty
   - Expiry_Date: Required, valid date format
   - Current_Stock: Required, non-negative
   - Reorder_Level, Maximum_Stock: Required, non-negative

## Data Quality Issues & Handling

### Errors (Record Rejected)

| Issue | Impact | Example | Action |
|-------|--------|---------|--------|
| Missing Batch_ID | Cannot identify record | Empty Batch_ID field | Skip record in processing |
| Invalid Expiry_Date | Cannot calculate expiry status | "2026-13-45" | Flag error, use "UNKNOWN" status |
| Missing Current_Stock | Cannot calculate stock status | Empty field | Flag error, use "UNKNOWN" status |
| Negative Current_Stock | Inventory integrity issue | -50 | Flag error, investigate source |

### Warnings (Record Processed, Flagged)

| Issue | Impact | Example |
|-------|--------|---------|
| Overstock | Possible storage/waste issue | Current_Stock > Maximum_Stock |
| Duplicate Batch_ID | Possible data entry error | BATCH-0001 appears twice |
| Missing optional fields | Reduced analytics capability | No Unit_Price for value calc |
| Manufacturing_Date > Expiry_Date | Data quality question | Mfg: 2026-06-01, Exp: 2026-05-01 |

## Field Examples by Scenario

### Scenario 1: Normal Stock (Low Risk)

```
Batch_ID: BATCH-0001
Medicine_Name: Aspirin
Expiry_Date: 2027-09-15 (180 days away)
Current_Stock: 250
Reorder_Level: 100
Maximum_Stock: 500

Calculated:
Days_To_Expiry: 180
Expiry_Status: SAFE
Stock_Status: NORMAL
Risk_Level: LOW
Risk_Score: 15
Recommended_Action: No action required. Stock and expiry within normal ranges.
```

### Scenario 2: Expired Batch (Critical Risk)

```
Batch_ID: BATCH-0002
Medicine_Name: Penicillin
Critical_Medicine: Yes
Expiry_Date: 2026-09-01
Current_Stock: 50
Reorder_Level: 100

Calculated:
Days_To_Expiry: -10 (expired 10 days ago)
Expiry_Status: EXPIRED
Stock_Status: LOW_STOCK
Risk_Level: CRITICAL
Risk_Score: 100
Recommended_Action: Immediate disposal required. Verify with pharmacist before action.
```

### Scenario 3: Expiring Soon + Low Stock (Critical Risk)

```
Batch_ID: BATCH-0003
Medicine_Name: Warfarin
Critical_Medicine: Yes
Expiry_Date: 2026-09-25 (14 days away)
Current_Stock: 30
Reorder_Level: 100

Calculated:
Days_To_Expiry: 14
Expiry_Status: EXPIRING_SOON
Stock_Status: LOW_STOCK
Risk_Level: CRITICAL
Risk_Score: 90
Recommended_Action: Expedite usage or disposal. Expiring soon with insufficient stock.
```

## Data Processing Pipeline

1. **Load** → Read CSV file
2. **Validate** → Check required fields, formats, ranges
3. **Clean** → Handle missing values, remove duplicates
4. **Enrich** → Calculate all derived fields
5. **Score** → Apply risk algorithms
6. **Report** → Generate insights and alerts

## Calculation Transparency

All calculations use deterministic Python rules with no external dependencies:

- **Expiry status**: Simple date comparison
- **Stock status**: Numeric range checks
- **Risk level**: Boolean logic on status combinations
- **Risk score**: Numeric mapping based on risk level

Results are **identical** for the same input data and reference date.

## Session-Only Data

Per data governance policy, all calculations are:
- Recomputed on each session load
- Not persisted between sessions
- Valid only for the current analysis snapshot
- Dependent on the reference date (defaults to current date)

## Audit Trail

Each processed record includes implicit traceability:
- Source file and timestamp (from load metadata)
- Processing version (risk engine version used)
- Calculation inputs (original data fields)
- Calculation outputs (derived fields)

This allows any result to be independently verified and reproduced.
