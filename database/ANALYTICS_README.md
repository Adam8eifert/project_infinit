# 📊 Database Analytics Enhancement

This document describes the enhanced analytical capabilities added to the Project Infinit database for advanced reporting, visualization, and statistical modeling.

## 🆕 New Database Structure

### Enhanced Existing Tables

#### **movements** - Extended Analytics

- `follower_estimate` - Estimated number of followers
- `social_media_presence` - JSON object with social media links
- `legal_status` - Legal status (registered, unregistered, banned, monitored)
- `controversy_level` - Public controversy level (1-5)
- `influence_score` - Calculated influence metric (0-1)
- `growth_trend` - Growth pattern (growing, stable, declining)

#### **sources** - Content Analytics

- `word_count` - Number of words in content
- `reading_time_minutes` - Estimated reading time
- `content_hash` - Hash for duplicate detection
- `scraped_by` - Which spider collected the data
- `social_shares` - Social media shares count
- `backlinks_count` - Number of backlinks

#### **locations** - Geographic Data

- `latitude/longitude` - GPS coordinates for mapping
- `population` - Population of the area
- `location_type` - Type (headquarters, branch, event, meeting_place)
- `activity_level` - Activity level (high, medium, low, inactive)
- `last_activity_date` - Last known activity

### New Analytical Tables

#### **temporal_analysis** - Time-Series Data

Tracks movement metrics over time for trend analysis:

- Daily mention counts and sentiment trends
- Source diversity metrics
- Activity pattern recognition
- Growth trend indicators

#### **geographic_analysis** - Spatial Patterns

Regional analysis and mapping data:

- Movement distribution by region
- Regional risk assessment
- Demographic correlations
- Category dominance patterns

#### **source_quality** - Credibility Metrics

Source reliability and quality assessment:

- Credibility and bias scores
- Fact-checking status
- Domain reputation metrics
- Automated quality flags

## 📈 Analytical Views (PostgreSQL)

### **movement_analytics**

Comprehensive overview of each movement with aggregated metrics:

```sql
SELECT * FROM movement_analytics WHERE risk_level >= 3;
```

### **monthly_trends**

Time-series analysis of overall trends:

```sql
SELECT * FROM monthly_trends WHERE month >= '2024-01-01';
```

### **regional_analysis**

Geographic distribution and regional patterns:

```sql
SELECT * FROM regional_analysis ORDER BY movement_count DESC;
```

### **risk_assessment**

High-risk movement identification:

```sql
SELECT * FROM risk_assessment WHERE risk_category = 'CRITICAL';
```

### **content_quality_analysis**

Source reliability analysis by domain:

```sql
SELECT * FROM content_quality_analysis WHERE avg_credibility > 0.7;
```

### **trend_analysis**

Movement growth pattern analysis:

```sql
SELECT * FROM trend_analysis WHERE mention_change > 10;
```

## 🚀 Running the Migration

To apply these enhancements to your database:

```bash
cd /home/adam/Dokumenty/projects/project_infinit
python database/migrate_analytics.py
```

The migration script will:

1. Add new columns to existing tables
2. Create new analytical tables
3. Set up indexes for performance
4. Create analytical views (PostgreSQL only)
5. Verify the migration success

## 📊 Use Cases for Analytics

### **Dashboard Reporting**

- Real-time movement activity monitoring
- Risk level dashboards
- Geographic heatmaps
- Sentiment trend charts

### **Statistical Modeling**

- Predictive risk modeling
- Growth trend forecasting
- Sentiment analysis over time
- Network analysis of movement connections

### **Research & Analysis**

- Temporal pattern recognition
- Regional risk assessment
- Source credibility analysis
- Comparative movement studies

### **Visualization Examples**

- Time-series plots of movement mentions
- Choropleth maps of regional activity
- Network graphs of movement relationships
- Sentiment distribution histograms

## 🔧 Data Population

After migration, you'll need to populate the analytical tables:

### **Temporal Analysis**

```python
# Example: Daily aggregation script
from database.db_loader import DBConnector
from datetime import datetime, timedelta

db = DBConnector()
with db.get_session() as session:
    # Aggregate daily metrics for each movement
    # Insert into temporal_analysis table
    pass
```

### **Geographic Analysis**

```python
# Example: Regional aggregation
# Calculate regional metrics and risk scores
# Insert into geographic_analysis table
```

### **Source Quality**

```python
# Example: Quality assessment
# Run credibility scoring algorithms
# Insert quality metrics into source_quality table
```

## 📈 Performance Considerations

### **Indexes**

- Composite indexes on `(movement_id, analysis_date)` for time-series queries
- Spatial indexes on geographic coordinates (if using PostGIS)
- Full-text search indexes on content fields

### **Partitioning** (PostgreSQL)

Consider partitioning large analytical tables by date:

```sql
CREATE TABLE temporal_analysis_y2024 PARTITION OF temporal_analysis
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### **Caching**

- Cache frequently accessed analytical views
- Use materialized views for complex aggregations
- Implement result caching for dashboard queries

## 🔍 Query Examples

### **Movement Risk Dashboard**

```sql
SELECT
    canonical_name,
    risk_level,
    controversy_level,
    mentions_last_30_days,
    sentiment_last_30_days,
    regions_covered
FROM movement_analytics
WHERE active_status = 'active'
ORDER BY risk_level DESC, mentions_last_30_days DESC
LIMIT 20;
```

### **Regional Hotspots**

```sql
SELECT
    region,
    movement_count,
    total_mentions,
    avg_risk_level,
    categories_present
FROM regional_analysis
WHERE recent_mentions > 50
ORDER BY total_mentions DESC;
```

### **Trend Analysis**

```sql
SELECT
    canonical_name,
    analysis_date,
    mention_count,
    sentiment_avg,
    activity_trend
FROM trend_analysis
WHERE analysis_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY analysis_date DESC;
```

## 🎯 Next Steps

1. **Run Migration**: Execute the migration script
2. **Data Population**: Implement scripts to populate analytical tables
3. **Dashboard Development**: Build visualization dashboards
4. **Model Training**: Develop predictive models using the analytical data
5. **API Development**: Create REST APIs for analytical queries

This enhanced database structure provides a solid foundation for advanced analytics, reporting, and data-driven insights into religious movement patterns and trends.
