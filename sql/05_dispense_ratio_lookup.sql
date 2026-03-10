-- Dispense ratio lookup: historical % split by dispense_method for forecast allocation
-- Date range: Prior 6 months (dynamic)
-- Scope: Ohio and Arizona internal pharmacies only
-- Levels: 1=product_type×wh_name, 2=product_type, 3=wh_name, 4=overall
-- Application: forecast_volume × (pct_of_volume / 100) = estimated dispense volume

WITH base AS (
  SELECT
    ord.fill_id,
    ord.dispense_method,
    ord.wh_name,
    COALESCE(ord.order_qty, 1) AS order_qty,
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
  LEFT JOIN (
    SELECT DISTINCT item_number, unit_of_measure
    FROM `clubroom-prod.datamarts.pms_non_phi_ndc_product_catalog`
  ) ndc ON ord.item_number = ndc.item_number
  WHERE ord.last_dispatched_at >= TIMESTAMP(DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH))
    AND ord.last_dispatched_at < TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
    AND DATE(ord.order_status_datetime) >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH)
    AND DATE(ord.order_status_datetime) <= LAST_DAY(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))
    AND ord.wh_name IN ('OHIO', 'BEYONDRX_OH', 'BEYONDRX_AZ')
    AND ord.dispense_method IS NOT NULL
),

-- Level 1: product_type × wh_name (primary for forecast)
l1_agg AS (
  SELECT
    product_type,
    wh_name,
    dispense_method,
    COUNT(DISTINCT fill_id) AS fill_count,
    SUM(order_qty) AS order_qty_sum
  FROM base
  GROUP BY product_type, wh_name, dispense_method
),
l1 AS (
  SELECT
    1 AS level,
    product_type,
    wh_name,
    dispense_method,
    fill_count,
    order_qty_sum,
    ROUND(order_qty_sum * 100.0 / SUM(order_qty_sum) OVER (PARTITION BY product_type, wh_name), 2) AS pct_of_volume
  FROM l1_agg
),

-- Level 2: product_type only (fallback when wh not in forecast)
l2_agg AS (
  SELECT
    product_type,
    dispense_method,
    COUNT(DISTINCT fill_id) AS fill_count,
    SUM(order_qty) AS order_qty_sum
  FROM base
  GROUP BY product_type, dispense_method
),
l2 AS (
  SELECT
    2 AS level,
    product_type,
    '(all)' AS wh_name,
    dispense_method,
    fill_count,
    order_qty_sum,
    ROUND(order_qty_sum * 100.0 / SUM(order_qty_sum) OVER (PARTITION BY product_type), 2) AS pct_of_volume
  FROM l2_agg
),

-- Level 3: wh_name only (fallback when product not in forecast)
l3_agg AS (
  SELECT
    wh_name,
    dispense_method,
    COUNT(DISTINCT fill_id) AS fill_count,
    SUM(order_qty) AS order_qty_sum
  FROM base
  GROUP BY wh_name, dispense_method
),
l3 AS (
  SELECT
    3 AS level,
    '(all)' AS product_type,
    wh_name,
    dispense_method,
    fill_count,
    order_qty_sum,
    ROUND(order_qty_sum * 100.0 / SUM(order_qty_sum) OVER (PARTITION BY wh_name), 2) AS pct_of_volume
  FROM l3_agg
),

-- Level 4: overall
l4_agg AS (
  SELECT
    dispense_method,
    COUNT(DISTINCT fill_id) AS fill_count,
    SUM(order_qty) AS order_qty_sum
  FROM base
  GROUP BY dispense_method
),
l4 AS (
  SELECT
    4 AS level,
    '(all)' AS product_type,
    '(all)' AS wh_name,
    dispense_method,
    fill_count,
    order_qty_sum,
    ROUND(order_qty_sum * 100.0 / SUM(order_qty_sum) OVER (), 2) AS pct_of_volume
  FROM l4_agg
)

SELECT level, product_type, wh_name, dispense_method, pct_of_volume, fill_count, order_qty_sum
FROM l1
UNION ALL
SELECT level, product_type, wh_name, dispense_method, pct_of_volume, fill_count, order_qty_sum
FROM l2
UNION ALL
SELECT level, product_type, wh_name, dispense_method, pct_of_volume, fill_count, order_qty_sum
FROM l3
UNION ALL
SELECT level, product_type, wh_name, dispense_method, pct_of_volume, fill_count, order_qty_sum
FROM l4
ORDER BY level, product_type, wh_name, order_qty_sum DESC;
