-- database/views.sql
-- Analytical views for reporting and dashboard queries

-- Movement Analytics View: Comprehensive overview of each movement
CREATE OR REPLACE VIEW movement_analytics AS
SELECT
    m.id,
    m.canonical_name,
    m.category,
    m.origin_country,
    m.established_year,
    m.active_status,
    m.legal_status,
    m.risk_level,
    m.controversy_level,
    m.sentiment_overall,
    m.follower_estimate,
    m.influence_score,
    m.growth_trend,

    -- Source metrics
    COUNT(DISTINCT s.id) as total_sources,
    COUNT(DISTINCT CASE WHEN s.publication_date >= CURRENT_DATE - INTERVAL '30 days' THEN s.id END) as recent_sources,
    MAX(s.publication_date) as latest_mention,
    MIN(s.publication_date) as first_mention,

    -- Location metrics
    COUNT(DISTINCT l.id) as total_locations,
    COUNT(DISTINCT l.region) as regions_covered,

    -- Alias metrics
    COUNT(DISTINCT a.id) as total_aliases,

    -- Quality metrics
    AVG(s.sentiment_score) as avg_sentiment,
    AVG(s.toxicity_score) as avg_toxicity,
    AVG(sq.credibility_score) as avg_source_credibility,

    -- Temporal trends (last 30 days)
    COALESCE(ta_recent.mention_count, 0) as mentions_last_30_days,
    COALESCE(ta_recent.sentiment_avg, 0) as sentiment_last_30_days

FROM movements m
LEFT JOIN sources s ON m.id = s.movement_id
LEFT JOIN locations l ON m.id = l.movement_id
LEFT JOIN aliases a ON m.id = a.movement_id
LEFT JOIN source_quality sq ON s.id = sq.source_id
LEFT JOIN temporal_analysis ta_recent ON m.id = ta_recent.movement_id
    AND ta_recent.analysis_date >= CURRENT_DATE - INTERVAL '30 days'
    AND ta_recent.analysis_date = (
        SELECT MAX(analysis_date) FROM temporal_analysis
        WHERE movement_id = m.id AND analysis_date >= CURRENT_DATE - INTERVAL '30 days'
    )
GROUP BY m.id, ta_recent.mention_count, ta_recent.sentiment_avg;

-- Monthly Trends View: Time-series analysis
CREATE OR REPLACE VIEW monthly_trends AS
SELECT
    DATE_TRUNC('month', publication_date) as month,
    COUNT(*) as total_mentions,
    COUNT(DISTINCT movement_id) as unique_movements,
    COUNT(DISTINCT s.id) as unique_sources,
    COUNT(DISTINCT domain) as unique_domains,
    AVG(sentiment_score) as avg_sentiment,
    AVG(toxicity_score) as avg_toxicity,
    SUM(word_count) as total_words,
    AVG(word_count) as avg_words_per_article
FROM sources s
WHERE publication_date IS NOT NULL
GROUP BY DATE_TRUNC('month', publication_date)
ORDER BY month DESC;

-- Regional Analysis View: Geographic patterns
CREATE OR REPLACE VIEW regional_analysis AS
SELECT
    l.region,
    l.district,
    COUNT(DISTINCT m.id) as movement_count,
    COUNT(DISTINCT s.id) as total_mentions,
    COUNT(DISTINCT CASE WHEN s.publication_date >= CURRENT_DATE - INTERVAL '90 days' THEN s.id END) as recent_mentions,
    AVG(s.sentiment_score) as avg_sentiment,
    AVG(m.risk_level) as avg_risk_level,
    AVG(m.follower_estimate) as total_followers_estimate,
    STRING_AGG(DISTINCT m.category, ', ') as categories_present
FROM locations l
JOIN movements m ON l.movement_id = m.id
LEFT JOIN sources s ON m.id = s.movement_id
WHERE l.region IS NOT NULL
GROUP BY l.region, l.district
ORDER BY movement_count DESC;

-- Risk Assessment View: High-risk movements
CREATE OR REPLACE VIEW risk_assessment AS
SELECT
    m.*,
    CASE
        WHEN m.risk_level >= 4 THEN 'CRITICAL'
        WHEN m.risk_level >= 3 THEN 'HIGH'
        WHEN m.risk_level >= 2 THEN 'MEDIUM'
        ELSE 'LOW'
    END as risk_category,
    CASE
        WHEN m.controversy_level >= 4 THEN 'HIGH_CONTROVERSY'
        WHEN m.controversy_level >= 3 THEN 'MODERATE_CONTROVERSY'
        ELSE 'LOW_CONTROVERSY'
    END as controversy_category,
    CASE
        WHEN m.sentiment_overall < -0.3 THEN 'NEGATIVE_SENTIMENT'
        WHEN m.sentiment_overall > 0.3 THEN 'POSITIVE_SENTIMENT'
        ELSE 'NEUTRAL_SENTIMENT'
    END as sentiment_category
FROM movements m
WHERE m.active_status = 'active'
ORDER BY m.risk_level DESC, m.controversy_level DESC;

-- Content Quality View: Source reliability analysis
CREATE OR REPLACE VIEW content_quality_analysis AS
SELECT
    s.domain,
    COUNT(*) as total_articles,
    AVG(s.sentiment_score) as avg_sentiment,
    AVG(s.toxicity_score) as avg_toxicity,
    AVG(sq.credibility_score) as avg_credibility,
    AVG(sq.bias_score) as avg_bias,
    COUNT(CASE WHEN sq.fact_check_status = 'verified' THEN 1 END) as verified_count,
    COUNT(CASE WHEN sq.fact_check_status = 'disputed' THEN 1 END) as disputed_count,
    COUNT(CASE WHEN sq.fact_check_status = 'unverified' THEN 1 END) as unverified_count,
    STRING_AGG(DISTINCT s.source_type, ', ') as source_types
FROM sources s
LEFT JOIN source_quality sq ON s.id = sq.source_id
WHERE s.domain IS NOT NULL
GROUP BY s.domain
HAVING COUNT(*) >= 3
ORDER BY avg_credibility DESC NULLS LAST;

-- Trend Analysis View: Movement growth patterns
CREATE OR REPLACE VIEW trend_analysis AS
SELECT
    ta.movement_id,
    m.canonical_name,
    ta.analysis_date,
    ta.mention_count,
    ta.sentiment_avg,
    ta.activity_trend,

    -- Compare with previous period
    LAG(ta.mention_count, 1) OVER (PARTITION BY ta.movement_id ORDER BY ta.analysis_date) as prev_mention_count,
    LAG(ta.sentiment_avg, 1) OVER (PARTITION BY ta.movement_id ORDER BY ta.analysis_date) as prev_sentiment,

    -- Calculate changes
    ta.mention_count - LAG(ta.mention_count, 1) OVER (PARTITION BY ta.movement_id ORDER BY ta.analysis_date) as mention_change,
    ta.sentiment_avg - LAG(ta.sentiment_avg, 1) OVER (PARTITION BY ta.movement_id ORDER BY ta.analysis_date) as sentiment_change

FROM temporal_analysis ta
JOIN movements m ON ta.movement_id = m.id
ORDER BY ta.movement_id, ta.analysis_date DESC;