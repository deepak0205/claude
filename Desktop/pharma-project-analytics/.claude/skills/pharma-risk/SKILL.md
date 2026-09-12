# Pharma Risk Calculation Rules

## Expiry Date Rules

All medicines are categorized by days remaining until expiry:

| Rule | Condition | Category |
|------|-----------|----------|
| **EXPIRED** | Expiry date < Today | Critical |
| **EXPIRING SOON** | 0 ≤ Days to expiry ≤ 30 | Warning |
| **SAFE** | Days to expiry > 30 | Normal |

**Formula:**
```
days_to_expiry = (expiry_date - today).days
if days_to_expiry < 0:
    status = EXPIRED
elif days_to_expiry <= 30:
    status = EXPIRING SOON
else:
    status = SAFE
```

## Stock Level Rules

All medicines are categorized by current stock vs. thresholds:

| Rule | Condition | Category |
|------|-----------|----------|
| **LOW STOCK** | Current stock < Reorder level | Warning |
| **OVERSTOCK** | Current stock > Max stock | Warning |
| **NORMAL** | Reorder level ≤ Current stock ≤ Max stock | Normal |

**Formula:**
```
if current_stock < reorder_level:
    stock_status = LOW STOCK
elif current_stock > max_stock:
    stock_status = OVERSTOCK
else:
    stock_status = NORMAL
```

## Critical Risk Definition

A medicine is flagged as **CRITICAL RISK** if ANY of these conditions hold:

1. Expiry date is EXPIRED (expiry date < today)
2. Expiry date is EXPIRING SOON (0 ≤ days to expiry ≤ 30) AND current stock < reorder level
3. Current stock is LOW STOCK AND medicine is classified as critical/urgent

**What triggers CRITICAL RISK:**
- Expired stock (immediate disposal risk)
- Low stock of a critical medicine (operational risk)
- Medicine expiring within 30 days AND already low stock (inefficient use)

**Examples:**

| SKU | Expiry | Today | Days to expiry | Current | Reorder | Risk | Reason |
|-----|--------|-------|----------------|---------|---------|------|--------|
| MED-001 | 2026-09-01 | 2026-09-15 | -14 | 50 | 100 | ✓ CRITICAL | Expired |
| MED-002 | 2026-10-01 | 2026-09-15 | 16 | 20 | 100 | ✓ CRITICAL | Expiring soon + low stock |
| MED-003 | 2026-10-15 | 2026-09-15 | 30 | 200 | 100 | - | Expiring soon but adequate stock |
| MED-004 | 2027-03-01 | 2026-09-15 | 168 | 30 | 100 | ✓ CRITICAL | Low stock (critical medicine) |
| MED-005 | 2027-06-01 | 2026-09-15 | 259 | 150 | 100 | - | Normal |

## Implementation Checklist

When implementing risk calculations:

- [ ] Expiry date is always compared to current date (use `datetime.now().date()`)
- [ ] Days to expiry calculation is accurate (handles year boundaries)
- [ ] Stock levels are validated as non-negative integers
- [ ] Risk status is logged with the calculation inputs
- [ ] Edge cases are tested: expiry today, negative days, zero stock
- [ ] Medicine criticality is documented (input data or configuration)
- [ ] Results are reproducible with the same inputs
- [ ] Audit trail shows which rule triggered the risk flag

## Testing Requirements

- **Unit tests**: Each rule in isolation
- **Boundary tests**: Exactly 0 days, exactly 30 days, negative days
- **Integration tests**: Multiple medicines with different statuses
- **Edge cases**: Missing data, invalid dates, extreme quantities
- **Reproducibility**: Same input always produces same output
