-- Task Productivity: verify tasks with Auto Dispensed flag
-- Joins auto_dispense_fills CTE on fill_id to identify fills that went through 08 Dispensing - Automated.
-- Exports for analysis with Auto Dispensed cut (Yes/No).
-- Date range: Prior 1 month (dynamic)

WITH auto_dispense_fills AS (
  -- List of fill_ids for automated dispense tasks, so we can exclude them from PV2 calculations.
  SELECT DISTINCT
    fill_id AS auto_dispense_fill_id
    , CONCAT(fill_id, ' - ', task, ' - ', task_performed_by) AS auto_dispense_identifier_key
  FROM `himsdata-dev.retool.Task_Productivity`
  WHERE task = '08 Dispensing - Automated'
),
verify_tasks AS (
  SELECT *
  FROM `himsdata-dev.retool.Task_Productivity`
  WHERE 1 = 1
    AND LOWER(task) LIKE '%verify%'
    AND task_ended_at >= TIMESTAMP(DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH))
    AND task_ended_at < TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
)
SELECT v.*
  , CASE WHEN a.auto_dispense_fill_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS is_auto_dispensed
FROM verify_tasks v
LEFT JOIN auto_dispense_fills a ON v.fill_id = a.auto_dispense_fill_id
