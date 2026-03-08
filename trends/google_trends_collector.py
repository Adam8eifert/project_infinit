# 📁 trends/google_trends_collector.py
# Google Trends Data Collector for tracking search interest in NRM
# Tracks search trends for religious movements over time
# Project: Religious Movements Research Database

from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_loader import DBConnector, GoogleTrend, Movement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleTrendsCollector:
    """
    Collector for Google Trends data about religious movements.
    
    Tracks search interest over time for:
    - Known NRM movements
    - Related keywords
    - Regional patterns (CZ, SK, etc.)
    """
    
    def __init__(self, output_csv="export/csv/google_trends_raw.csv"):
        self.output_csv = output_csv
        self.trends_data = []
        
        try:
            # Initialize pytrends client
            self.pytrends = TrendReq(hl='cs-CZ', tz=60)  # Czech locale
            logger.info("✓ Google Trends client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Trends: {e}")
            self.pytrends = None
        
        # Database connection for movement lookup
        self.db = DBConnector()
        self.session = self.db.get_session()
    
    def collect_trend_data(self, keyword, timeframe='today 12-m', region='CZ'):
        """
        Collect trend data for a specific keyword
        
        Args:
            keyword: Search term
            timeframe: Time range (e.g., 'today 12-m', 'today 5-y', 'all')
            region: Country code (CZ, SK, etc.)
        """
        if not self.pytrends:
            logger.error("Google Trends client not initialized")
            return
        
        try:
            logger.info(f"Collecting trends for: {keyword} (region: {region})")
            
            # Build payload
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe=timeframe,
                geo=region
            )
            
            # Get interest over time
            interest_df = self.pytrends.interest_over_time()
            
            if interest_df.empty:
                logger.warning(f"No trend data found for: {keyword}")
                return
            
            # Try to match keyword to a movement
            movement_id = self.match_keyword_to_movement(keyword)
            
            # Process each data point
            for date_index, row in interest_df.iterrows():
                interest_value = int(row[keyword])
                
                trend_record = {
                    'keyword': keyword,
                    'date': date_index.to_pydatetime(),
                    'interest_value': interest_value,
                    'region': region,
                    'movement_id': movement_id,
                }
                
                self.trends_data.append(trend_record)
            
            logger.info(f"  ✓ Collected {len(interest_df)} data points for {keyword}")
            
            # Rate limiting - Google Trends has strict limits
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error collecting trends for '{keyword}': {e}")
    
    def match_keyword_to_movement(self, keyword):
        """Try to match keyword to a known movement in database"""
        try:
            # Simple fuzzy matching against movement names
            movements = self.session.query(Movement).all()
            
            keyword_lower = keyword.lower()
            for movement in movements:
                if movement.name and keyword_lower in movement.name.lower():
                    logger.info(f"  → Matched to movement: {movement.name} (ID: {movement.id})")
                    return movement.id
                if movement.alias and keyword_lower in movement.alias.lower():
                    logger.info(f"  → Matched to movement: {movement.name} (ID: {movement.id})")
                    return movement.id
            
            return None
        except Exception as e:
            logger.warning(f"Could not match keyword to movement: {e}")
            return None
    
    def collect_top_nrm_keywords(self, timeframe='today 12-m'):
        """Collect trends for major NRM movements"""
        # Major movements to track
        keywords = [
            # International movements with Czech presence
            'scientologie',
            'svědkové jehovovi',
            'mormoni',
            'hare krishna',
            
            # Newer movements
            'bhakti marga',
            'allatra',
            
            # Historical/known movements
            'osho',
            'transcendentální meditace',
            
            # General terms
            'sekty česko',
            'nová náboženská hnutí',
        ]
        
        for keyword in keywords:
            self.collect_trend_data(keyword, timeframe=timeframe, region='CZ')
            
            # Also collect for Slovakia
            self.collect_trend_data(keyword, timeframe=timeframe, region='SK')
    
    def collect_related_queries(self, seed_keyword):
        """Get related queries that people search for"""
        if not self.pytrends:
            return
        
        try:
            self.pytrends.build_payload(kw_list=[seed_keyword], geo='CZ')
            
            related = self.pytrends.related_queries()
            
            if seed_keyword in related and related[seed_keyword]['top'] is not None:
                top_queries = related[seed_keyword]['top']
                logger.info(f"Related queries for '{seed_keyword}':")
                for query in top_queries['query'].head(5):
                    logger.info(f"  - {query}")
                    # Optionally collect trends for related queries too
            
        except Exception as e:
            logger.error(f"Error getting related queries: {e}")
    
    def collect_regional_interest(self, keyword, timeframe='today 12-m'):
        """Collect regional distribution within Czech Republic"""
        if not self.pytrends:
            return
        
        try:
            self.pytrends.build_payload(kw_list=[keyword], timeframe=timeframe, geo='CZ')
            
            regional_df = self.pytrends.interest_by_region(resolution='REGION')
            
            if not regional_df.empty:
                logger.info(f"Regional interest for '{keyword}' in CZ:")
                top_regions = regional_df.sort_values(by=keyword, ascending=False).head(5)
                for region, row in top_regions.iterrows():
                    logger.info(f"  {region}: {row[keyword]}")
            
        except Exception as e:
            logger.error(f"Error getting regional interest: {e}")
    
    def save_to_csv(self):
        """Save collected trends to CSV"""
        if not self.trends_data:
            logger.warning("No trends data to save")
            return
        
        df = pd.DataFrame(self.trends_data)
        df['collected_at'] = datetime.utcnow()
        
        # Ensure output directory exists
        Path(self.output_csv).parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(self.output_csv, index=False, encoding='utf-8')
        logger.info(f"✓ Saved {len(df)} trend data points to {self.output_csv}")
    
    def save_to_database(self):
        """Save trends data directly to database"""
        if not self.trends_data:
            logger.warning("No trends data to save")
            return
        
        try:
            saved_count = 0
            
            for trend_record in self.trends_data:
                # Check if record already exists
                existing = self.session.query(GoogleTrend).filter(
                    GoogleTrend.keyword == trend_record['keyword'],
                    GoogleTrend.date == trend_record['date'],
                    GoogleTrend.region == trend_record['region']
                ).first()
                
                if existing:
                    # Update existing record
                    existing.interest_value = trend_record['interest_value']
                    existing.movement_id = trend_record['movement_id']
                    existing.collected_at = datetime.utcnow()
                else:
                    # Create new record
                    new_trend = GoogleTrend(**trend_record)
                    self.session.add(new_trend)
                
                saved_count += 1
            
            self.session.commit()
            logger.info(f"✓ Saved {saved_count} trend records to database")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving to database: {e}")
        finally:
            self.session.close()
    
    def run(self, save_to_db=True):
        """Main execution method"""
        logger.info("Starting Google Trends collector...")
        
        # Collect trends data
        self.collect_top_nrm_keywords(timeframe='today 12-m')
        
        # Optionally analyze related queries
        self.collect_related_queries('sekty česko')
        
        # Save results
        self.save_to_csv()
        
        if save_to_db:
            self.save_to_database()
        
        logger.info(f"Google Trends collection finished. Total data points: {len(self.trends_data)}")


def main():
    """Standalone execution"""
    collector = GoogleTrendsCollector()
    collector.run(save_to_db=True)


if __name__ == "__main__":
    main()
