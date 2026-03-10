# Dispense Method Analysis — SQL Queries

## Run Order

1. **01_base_data.sql** — Base extraction. Export to `output/base_data.csv`.
2. **Feature selection** (Python) — Run `python feature_selection.py output/base_data.csv` **before** summary stats. Produces visualizations and `selected_features.txt`.
3. **02_summary_stats.sql** — Overall dispense_method counts and %
4. **02b_summary_by_dimensions.sql** — By product_type × dispense_method
5. **03_distributions.sql** — % within product_type
6. **03b_distribution_by_wh.sql** — % within wh_name
7. **04_prediction_training_data.sql** — Product-level training data for prediction model

## BigQuery Execution (PowerShell)

Export to `output/` for report generation:

```powershell
Get-Content "sql\01_base_data.sql" | bq query --use_legacy_sql=false --format=csv --max_rows=1000000 > output\base_data.csv
Get-Content "sql\02_summary_stats.sql" | bq query --use_legacy_sql=false --format=csv --max_rows=1000000 > output\summary_stats.csv
Get-Content "sql\02b_summary_by_dimensions.sql" | bq query --use_legacy_sql=false --format=csv --max_rows=1000000 > output\summary_by_dimensions.csv
Get-Content "sql\03_distributions.sql" | bq query --use_legacy_sql=false --format=csv --max_rows=1000000 > output\distribution_by_product_type.csv
Get-Content "sql\03b_distribution_by_wh.sql" | bq query --use_legacy_sql=false --format=csv --max_rows=1000000 > output\distribution_by_wh.csv
```

## Report Generation

After running feature selection and SQL exports:

```powershell
python generate_report.py
```

Output: `output/Dispense_Method_Analysis_Report.docx`

## Partition Note

All queries filter on `last_dispatched_at` for OLC partition pruning. Adjust date range in each file if needed.
