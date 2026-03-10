-- Base data extraction for dispense method analysis
-- Date range: Prior 6 months (dynamic)
-- Scope: Ohio and Arizona internal pharmacies only (OHIO, BEYONDRX_OH, BEYONDRX_AZ)
-- CRITICAL: Filter on last_dispatched_at for OLC partition pruning

WITH base AS (
  SELECT
    ord.fill_id,
    ord.order_id,
    ord.product_rxcui AS product_id,
    ord.dispense_method,
    DATE(ord.order_status_datetime) AS order_status_date,
    ord.wh_name,
    ord.is_rx,
    ord.is_compound,
    ord.is_multi,
    ord.level_2,
    ord.level_3,
    COALESCE(nndc.unit_of_measure, ndc.unit_of_measure) AS unit_of_measure,
    ord.item_number,
    ord.SKU,
    COALESCE(ord.order_qty, 1) AS order_qty,
    -- Product type (aligned with Order Type Classification from rules)
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
  WHERE 1 = 1
    -- Partition pruning (REQUIRED for OLC) + prior 6 months
    AND ord.last_dispatched_at >= TIMESTAMP(DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH))
    AND ord.last_dispatched_at < TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
    -- Analysis date window (when dispense occurred)
    AND DATE(ord.order_status_datetime) >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH)
    AND DATE(ord.order_status_datetime) <= LAST_DAY(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))
    AND ord.wh_name IN ('OHIO', 'BEYONDRX_OH', 'BEYONDRX_AZ')
    -- Exclude Zofran from order-level dedup if counting orders (keep for fill-level)
    -- AND (ord.product_rxcui <> '104894' OR ord.product_rxcui IS NULL)
)
SELECT * FROM base
WHERE dispense_method IS NOT NULL  -- Exclude rows with no dispense method
ORDER BY order_status_date, wh_name, product_type, dispense_method;
