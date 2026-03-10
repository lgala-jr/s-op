-- Task Productivity: verify tasks only
-- Exports for histogram analysis of logic_adjusted_new_step_duration_minutes
-- Date range: Prior 1 month (dynamic)
-- Date filter uses task_ended_at (when task completed)

SELECT *
FROM `himsdata-dev.retool.Task_Productivity`
WHERE 1 = 1
  AND LOWER(task) LIKE '%verify%'
  AND task_ended_at >= TIMESTAMP(DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH))
  AND task_ended_at < TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
