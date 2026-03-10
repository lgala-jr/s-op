-- Summary statistics: Dispense method by product type and other dimensions
-- Run 01_base_data first and save to temp table, or run as CTE

WITH base AS (
  -- Same base logic as 01_base_data (inline for standalone run)
  SELECT
    ord.fill_id,
    ord.order_id,
    COALESCE(ord.order_qty, 1) AS order_qty,
    ord.dispense_method,
    ord.wh_name,
    ord.is_rx,
    ord.is_compound,
    ord.level_2,
    ord.level_3,
    COALESCE(nndc.unit_of_measure, ndc.unit_of_measure) AS unit_of_measure,
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

totals AS (
  SELECT
    COUNT(DISTINCT fill_id) AS total_fills,
    SUM(order_qty) AS total_order_qty
  FROM base
)

-- 1. Overall dispense_method summary (by fill count and by order_qty)
SELECT
  'Overall' AS cut_dimension,
  dispense_method,
  COUNT(DISTINCT fill_id) AS fill_count,
  SUM(order_qty) AS order_qty_sum,
  ROUND(COUNT(DISTINCT fill_id) * 100.0 / (SELECT total_fills FROM totals), 2) AS pct_of_total_fills,
  ROUND(SUM(order_qty) * 100.0 / (SELECT total_order_qty FROM totals), 2) AS pct_of_total_order_qty
FROM base
GROUP BY dispense_method
ORDER BY order_qty_sum DESC;
