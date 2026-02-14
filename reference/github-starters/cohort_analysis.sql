-- ============================================================
-- Monthly Cohort Retention Analysis
-- ============================================================
-- Groups customers by acquisition month, tracks retention
-- over subsequent months. Output: cohort retention matrix.
-- ============================================================

WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_TRUNC(MIN(order_date), MONTH) AS cohort_month
    FROM {{ ref('fct_orders') }}
    WHERE order_status = 'completed'
    GROUP BY customer_id
),

monthly_activity AS (
    SELECT DISTINCT
        o.customer_id,
        fp.cohort_month,
        DATE_TRUNC(o.order_date, MONTH) AS activity_month
    FROM {{ ref('fct_orders') }} o
    JOIN first_purchase fp ON o.customer_id = fp.customer_id
    WHERE o.order_status = 'completed'
),

cohort_data AS (
    SELECT
        cohort_month,
        activity_month,
        DATE_DIFF(activity_month, cohort_month, MONTH) AS month_number,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM monthly_activity
    GROUP BY cohort_month, activity_month
),

cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
)

SELECT
    cd.cohort_month,
    cs.cohort_size,
    cd.month_number,
    cd.active_customers,
    ROUND(cd.active_customers * 100.0 / cs.cohort_size, 1) AS retention_pct
FROM cohort_data cd
JOIN cohort_sizes cs ON cd.cohort_month = cs.cohort_month
ORDER BY cd.cohort_month, cd.month_number;
