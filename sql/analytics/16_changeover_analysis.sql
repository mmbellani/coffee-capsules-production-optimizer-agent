-- title: Changeover Analysis (transition matrix)
-- category: Quality & Output
-- description: Product-to-product changeovers per line: frequency and lost
--   minutes, exposing the costliest transitions to schedule around.
SELECT
    line_id,
    from_product,
    to_product,
    COUNT(*)                    AS changeovers,
    SUM(duration_min)           AS total_lost_min,
    ROUND(AVG(duration_min), 1) AS avg_lost_min,
    ROUND(100.0 * SUM(duration_min)
          / SUM(SUM(duration_min)) OVER (PARTITION BY line_id), 2) AS pct_line_changeover_time
FROM fact_changeover_episode
WHERE from_product <> to_product
GROUP BY line_id, from_product, to_product
ORDER BY total_lost_min DESC;
