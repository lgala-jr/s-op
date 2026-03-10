-- Training dataset for dispense method prediction
-- Aggregates at product_id (product_rxcui) level: dominant dispense_method + features
-- Use for building a model that predicts dispense_method from product attributes

WITH base AS (
  SELECT
    ord.product_rxcui AS product_id,
    COALESCE(ord.order_qty, 1) AS order_qty,
    ord.dispense_method,
    ord.wh_name,
    ord.is_rx,
    ord.is_compound,
    ord.level_2,
    ord.level_3,
    COALESCE(nndc.unit_of_measure, ndc.unit_of_measure) AS unit_of_measure,
    ord.item_number,
    ord.SKU,
    CASE
      WHEN LOWER(ord.level_2) = 'testosterone - lab' THEN 'TRT Lab'
      WHEN LOWER(ord.product_rxcui) LIKE '%gummy%' OR LOWER(ord.SKU) LIKE '%gummy%' THEN 'Gummy'
      WHEN LOWER(ord.level_2) LIKE '%injectable%' THEN 'GLP'
      WHEN (ord.is_multi AND LOWER(ord.level_2) LIKE '%weight loss%' AND ord.is_rx) THEN 'Multis Orders'
      WHEN (LOWER(ord.level_2) LIKE '%weight loss%' AND NOT ord.is_rx) THEN 'Meal Kit'
      WHEN (ord.is_compound AND COALESCE(nndc.unit_of_measure, ndc.unit_of_measure) = 'MILLILITER'
           AND (LOWER(ord.SKU) NOT LIKE '%pill%' AND LOWER(ord.SKU) NOT LIKE '%chew%')) THEN 'Topical'
      WHEN (ord.is_compound AND LOWER(ord.level_3) NOT LIKE '%non-rx%') THEN 'Tablet'
      WHEN ord.wh_name = 'CUREXA' THEN 'Rx'
      WHEN ord.is_rx THEN 'Rx'
      ELSE 'Non-Rx'
    END AS product_type
  FROM `clubroom-prod.datamarts.order_lifecycle_nrt` AS ord
  LEFT JOIN `clubroom-prod.datamarts.pms_non_phi_non_ndc_product_catalog` nndc ON ord.item_number = nndc.item_number
  LEFT JOIN (SELECT DISTINCT item_number, unit_of_measure FROM `clubroom-prod.datamarts.pms_non_phi_ndc_product_catalog`) ndc ON ord.item_number = ndc.item_number
  WHERE ord.last_dispatched_at >= TIMESTAMP(DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH))
    AND ord.last_dispatched_at < TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
    AND DATE(ord.order_status_datetime) >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH)
    AND DATE(ord.order_status_datetime) <= LAST_DAY(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))
    AND ord.wh_name IN ('OHIO', 'BEYONDRX_OH', 'BEYONDRX_AZ')
    AND ord.dispense_method IS NOT NULL
),

-- For products dispensed at multiple locations, we may need wh_name in the model
-- Here: aggregate by (product_id, wh_name) to capture location-specific patterns
-- Dominant dispense_method = mode by order_qty (quantity-weighted)
fill_counts AS (
  SELECT
    product_id,
    wh_name,
    product_type,
    level_2,
    level_3,
    unit_of_measure,
    is_compound,
    is_rx,
    dispense_method,
    COUNT(*) AS fill_count,
    SUM(order_qty) AS order_qty_sum
  FROM base
  GROUP BY product_id, wh_name, product_type, level_2, level_3, unit_of_measure, is_compound, is_rx, dispense_method
),

-- Dominant dispense_method per product per wh (mode by order_qty — quantity-weighted)
ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY product_id, wh_name ORDER BY order_qty_sum DESC) AS rn
  FROM fill_counts
)

SELECT
  product_id,
  wh_name,
  product_type,
  level_2,
  level_3,
  unit_of_measure,
  is_compound,
  is_rx,
  dispense_method AS dominant_dispense_method,
  fill_count,
  order_qty_sum
FROM ranked
WHERE rn = 1
ORDER BY product_id, wh_name;
