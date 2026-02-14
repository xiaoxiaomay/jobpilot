-- ============================================================
-- Customer Segmentation using RFM Analysis
-- ============================================================
-- Computes Recency, Frequency, Monetary scores per customer
-- and assigns segments based on RFM quartiles.
-- Works with: PostgreSQL, BigQuery, Snowflake
-- ============================================================

WITH customer_metrics AS (
    SELECT
        customer_id,
        -- Recency: days since last purchase
        DATE_DIFF(CURRENT_DATE, MAX(order_date), DAY) AS recency_days,
        -- Frequency: number of orders
        COUNT(DISTINCT order_id) AS frequency,
        -- Monetary: total spend
        SUM(order_total) AS monetary
    FROM {{ ref('fct_orders') }}
    WHERE order_status = 'completed'
    GROUP BY customer_id
),

-- Assign quartile scores (1-4, where 4 is best)
rfm_scores AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- Recency: lower is better (more recent = higher score)
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
        -- Frequency: higher is better
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
        -- Monetary: higher is better
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM customer_metrics
),

rfm_segments AS (
    SELECT
        *,
        -- Combined RFM score (concatenation for segment mapping)
        CONCAT(r_score, f_score, m_score) AS rfm_combined,
        -- Weighted composite score
        (r_score * 0.3 + f_score * 0.35 + m_score * 0.35) AS rfm_weighted,
        -- Segment labels
        CASE
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal'
            WHEN r_score >= 3 AND f_score = 1 THEN 'New Customers'
            WHEN r_score = 2 AND f_score >= 2 THEN 'At Risk'
            WHEN r_score = 1 AND f_score >= 2 THEN 'Cant Lose Them'
            WHEN r_score = 1 AND f_score = 1 THEN 'Lost'
            ELSE 'Others'
        END AS segment
    FROM rfm_scores
)

SELECT * FROM rfm_segments
ORDER BY rfm_weighted DESC;
