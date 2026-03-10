# Dispense Ratio Lookup — Applying to Forecast Volume

The `dispense_ratio_lookup.csv` contains historical ratios from the prior 6 months. Use these to allocate forecast volume across dispense methods (automated, manual, other).

## Lookup Hierarchy

| Level | Dimensions | Use when |
|-------|------------|----------|
| 1 | product_type × wh_name | Forecast has both product_type and wh_name (preferred) |
| 2 | product_type only | Forecast has product_type but not wh_name |
| 3 | wh_name only | Forecast has wh_name but not product_type |
| 4 | overall | Fallback when no dimension match |

**Rule:** Use the most granular level that matches your forecast dimensions.

## Application Formula

```
estimated_dispense_volume = forecast_volume × (pct_of_volume / 100)
```

Example: Forecast 10,000 Tablets at BEYONDRX_OH next week. Lookup level 1:
- automated: 75.67% → 10,000 × 0.7567 = **7,567**
- manual: 24.33% → 10,000 × 0.2433 = **2,433**

## Volume Metric

Ratios are based on `order_qty` (fills × quantity). Ensure your forecast volume uses the same metric for consistency.

## Refresh

Re-run the analysis pipeline monthly or quarterly to refresh ratios from the latest 6 months of data.
