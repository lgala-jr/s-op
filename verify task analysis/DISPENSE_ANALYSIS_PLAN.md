# Dispense Method Analysis Plan

## Objective

1. **Descriptive analysis**: Understand what types of products use different `dispense_method` values (automation, manual, mixture).
2. **Predictive model**: Develop a method to predict how a product will be dispensed *before* it is processed and shipped.

---

## Part 1: Descriptive Analysis

### Data Source

- **Table**: `clubroom-prod.datamarts.order_lifecycle_nrt` (OLC)
- **Date range**: Prior 6 months (dynamic: first day of month 6 months ago through last day of last month)
- **Scope**: Ohio and Arizona internal pharmacies only (`wh_name IN ('OHIO', 'BEYONDRX_OH', 'BEYONDRX_AZ')`)
- **Grain**: Fill-level (one row per medication/fill); `dispense_method` is observed after the fact

### Recommended Cut Dimensions

| Dimension | Rationale |
|-----------|-----------|
| **product_type** | High-level category (GLP, Tablet, Topical, Gummy, etc.) — primary driver of dispense method |
| **wh_name** | Automation capability varies by pharmacy/location |
| **level_2** | Business category (e.g., Weight Loss, Hair, Sex) — may correlate with form factor |
| **level_3** | Finer product grouping |
| **unit_of_measure** | EACH vs MILLILITER — physical form drives automation feasibility |
| **is_compound** | Compounded vs non-compound — different handling |
| **product_rxcui (product_id)** | Product-level patterns for prediction |

### Summary Statistics to Generate

1. **Overall**: Count and % of fills by `dispense_method`
2. **By product_type**: Count by (product_type, dispense_method); % within each product_type
3. **By wh_name**: Count by (wh_name, dispense_method); % within each pharmacy
4. **By unit_of_measure**: EACH vs MILLILITER breakdown
5. **By level_2**: Category-level patterns

### Distribution Analysis

- **Within-dimension distributions**: For each product_type (and wh_name), what % is automation vs manual vs mixture?
- **Concentration**: Which product types are “pure” (one dispense method dominates) vs mixed?
- **Cross-tabs**: product_type × dispense_method, wh_name × dispense_method

### SQL Artifacts

| File | Purpose |
|------|---------|
| `sql/01_base_data.sql` | Base extraction with partition filter |
| `sql/02_summary_stats.sql` | Overall dispense_method summary |
| `sql/02b_summary_by_dimensions.sql` | Summary by product_type, dispense_method |
| `sql/03_distributions.sql` | % within product_type |
| `sql/03b_distribution_by_wh.sql` | % within wh_name |

---

## Feature Selection (Before Summary Stats)

**Order**: Run feature selection **before** summary stats and distribution generation. Use the selected features to guide which dimensions to cut by in Part 1.

### Python Script: `feature_selection.py`

**Input**: CSV export of `01_base_data.sql` (default: `output/base_data.csv`)

**Output** (saved to `output/feature_selection/`):

| Output | Description |
|-------|-------------|
| `00_dispense_overview.png` | Overall dispense_method distribution + top feature cross-tab |
| `01_feature_distributions.png` | Bar charts of each candidate feature (weighted by order_qty) |
| `02_<feature>_vs_dispense.png` | Stacked bar: each feature value vs dispense_method mix |
| `03_association_strength.png` | Chi-square and mutual information scores per feature |
| `chi_square_scores.csv` | Chi-square statistic and p-value per feature |
| `mutual_info_scores.csv` | Mutual information per feature |
| `selected_features.txt` | Shortlist of features to use downstream |

**Run**:
```bash
# Export base data first (PowerShell):
Get-Content "sql\01_base_data.sql" | bq query --use_legacy_sql=false --format=csv > output\base_data.csv

# Then run feature selection:
python feature_selection.py output/base_data.csv
```

**Methods**: Chi-square test (categorical vs target), mutual information. Features with p &lt; 0.05 (chi-square) or top 5 by MI are selected. Use `selected_features.txt` to focus summary stats and distributions on the most predictive dimensions.

---

## Part 2: Prediction Methodology

### Problem Statement

Predict `dispense_method` (automation / manual / mixture) for a product **before** it is processed. At prediction time we have:

- Product attributes: `product_rxcui`, `level_2`, `level_3`, `unit_of_measure`, `is_compound`, `is_rx`, `SKU`
- Location: `wh_name` (pharmacy)
- No post-dispense data (that is what we are predicting)

### Approach Options

#### Option A: Rule-Based Classification (Fastest to Implement)

1. Use Part 1 distributions to identify rules, e.g.:
   - If `product_type = 'Gummy'` and `wh_name = 'OHIO'` → 95% automation → predict **Automation**
   - If `product_type = 'Topical'` and `unit_of_measure = 'MILLILITER'` → 80% manual → predict **Manual**
2. Define thresholds (e.g., if one method >80% within a bucket, assign that method; else **Mixture**)
3. **Pros**: Interpretable, no ML dependency, easy to maintain  
4. **Cons**: May miss interactions; requires manual rule updates

#### Option B: Logistic Regression / Multinomial Logit

1. **Target**: `dispense_method` (multi-class: automation, manual, mixture)
2. **Features** (all known before dispense):
   - `product_type` (one-hot or label-encoded)
   - `wh_name` (one-hot)
   - `unit_of_measure`
   - `is_compound`, `is_rx`
   - `level_2` (or top N categories)
3. Train on historical fills (prior 6 months)
4. **Pros**: Simple, interpretable coefficients  
5. **Cons**: Assumes linear relationships; may underperform for complex interactions

#### Option C: Tree-Based Model (Random Forest / XGBoost)

1. Same target and features as Option B
2. Handles non-linearities and interactions (e.g., Gummy + Ohio → automation)
3. **Pros**: Often better accuracy; feature importance for validation  
4. **Cons**: Less interpretable; need Python/R environment

#### Option D: Product-Level Lookup Table

1. Build a table: `(product_id, wh_name) → dominant_dispense_method`
2. For **new products** not in the table, fall back to `product_type` + `wh_name` rules
3. **Pros**: Exact for known products; simple fallback  
4. **Cons**: Cold start for new products

### Recommended Hybrid Approach

1. **Build base data** (`sql/01_base_data.sql`) and **run feature selection** (`feature_selection.py`):
   - Feature selection runs first; outputs visualizations and `selected_features.txt`
   - Use selected features to guide summary stats and distribution cuts

2. **Build training data** (`sql/04_prediction_training_data.sql`):
   - Aggregate at `(product_id, wh_name)` with dominant `dispense_method` (mode)
   - Include features from `selected_features.txt` (or full candidate set)

3. **Phase 1 – Lookup + rules**:
   - For known `(product_id, wh_name)`: use historical dominant method
   - For new products: use rule-based classification from Part 1 distributions

4. **Phase 2 – ML model** (optional):
   - Train multinomial model (logistic or tree) on fill-level data
   - Use **selected features** from `output/feature_selection/selected_features.txt`
   - Validate on holdout period (e.g., Apr 2026 if available)

### Feature Selection Details

**Purpose**: Identify which candidate features actually predict `dispense_method` and remove redundant or noisy ones. Run **before** summary stats so distributions can focus on selected dimensions.

**Candidate features** (all known before dispense):

| Feature | Type | Notes |
|---------|------|-------|
| `product_type` | Categorical | Derived; may subsume level_2/level_3 |
| `wh_name` | Categorical | Location-specific automation |
| `level_2` | Categorical | Business category |
| `level_3` | Categorical | Finer grouping; high cardinality |
| `unit_of_measure` | Categorical | EACH vs MILLILITER |
| `is_compound` | Binary | Compounded vs not |
| `is_rx` | Binary | Rx vs non-Rx |

**Methods** (run in Python/R or equivalent):

1. **Univariate**:
   - Chi-square test (categorical vs categorical): rank features by association with `dispense_method`
   - Mutual information: captures non-linear relationships
   - Keep features above a threshold (e.g., p &lt; 0.05 or top 5 by MI)

2. **Model-based**:
   - Train a simple model (e.g., logistic regression or single tree); use coefficients or feature importance
   - Drop features with near-zero importance
   - Tree models: `feature_importances_`; logistic: absolute coefficient magnitude

3. **Wrapper** (optional, more compute):
   - Forward/backward stepwise: add or remove features based on validation performance
   - Recursive Feature Elimination (RFE): iteratively drop least important feature

4. **Domain checks**:
   - **Multicollinearity**: `product_type` is derived from `level_2`, `level_3`, `unit_of_measure`, `is_compound` — consider dropping redundant raw features if `product_type` is strong
   - **Cardinality**: `level_3` or `product_id` may have many levels; consider grouping or excluding if sparse
   - **Cold start**: Features used at prediction time must exist for new products (e.g., `product_type` is fine; `product_id` lookup handles known products separately)

**Output**: A shortlist of features to use in Phase 2 (e.g., `product_type`, `wh_name`, `unit_of_measure`, `is_compound`).

### Handling “Mixture”

- **Definition**: Same product sometimes automated, sometimes manual (e.g., by shift or capacity)
- **Prediction options**:
  - Predict **dominant** method (mode) for planning
  - Predict **probability distribution** (e.g., 60% automation, 40% manual) for stochastic planning
  - Flag as **Mixture** when no single method exceeds a threshold (e.g., 70%)

### Validation

- **Temporal holdout**: Train on first 5 months, validate on 6th month
- **Product holdout**: Hold out 20% of product_ids, measure accuracy on unseen products
- **Metrics**: Accuracy, macro F1 (for class imbalance), confusion matrix

---

## Execution Checklist

1. **Base data**
   - [ ] Run `01_base_data.sql`; confirm `dispense_method` values and volume
   - [ ] Export to `output/base_data.csv`

2. **Feature selection** (before summary stats)
   - [ ] Run `python feature_selection.py output/base_data.csv`
   - [ ] Review `output/feature_selection/` visualizations and `selected_features.txt`

3. **Summary stats & distributions** (use selected features to prioritize cuts)
   - [ ] Run `02_summary_stats.sql` and `02b_summary_by_dimensions.sql`
   - [ ] Run `03_distributions.sql` and `03b_distribution_by_wh.sql`
   - [ ] Export results to Sheets/Excel for visualization

4. **Prediction**
   - [ ] Run `python build_prediction_model.py` to train Random Forest and evaluate fit
   - [ ] Run `python generate_prediction_report.py` to create `output/Prediction_Process_Report.docx`
   - [ ] Implement Phase 1 (lookup + rules) in Sheets or SQL for deployment
   - [ ] (Optional) Run `04_prediction_training_data.sql` for product-level lookup table

5. **Reports**
   - [ ] Run `python generate_report.py` → `output/Dispense_Method_Analysis_Report.docx`
   - [ ] Run `python generate_prediction_report.py` → `output/Prediction_Process_Report.docx` (steps + model fit)
