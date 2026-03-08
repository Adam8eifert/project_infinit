# 📁 scraping/reddit_spider.py
# Reddit Spider for collecting discussions about New Religious Movements
# Collects both: discussions ABOUT NRM and content FROM NRM
# Project: Religious Movements Research Database

import praw
import pandas as pd
from datetime import datetime
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from extracting.keywords import contains_relevant_keywords, match_movement_from_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedditSpider:
    """
    Spider for collecting Reddit posts and comments about religious movements.
    
    Collects from:
    - Relevant subreddits (r/cults, r/exmormon, r/scientology, etc.)
    - Keyword searches across Reddit
    - Specific movement discussions
    """
    
    def __init__(self, output_csv="export/csv/reddit_raw.csv"):
        self.output_csv = output_csv
        self.posts = []
        
        # Initialize Reddit API client (requires credentials in environment or config)
        try:
            self.reddit = praw.Reddit(
                client_id="YOUR_CLIENT_ID",  # Set in environment
                client_secret="YOUR_CLIENT_SECRET",
                user_agent="NRM_Research_Bot/1.0"
            )
            logger.info("✓ Reddit API client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Reddit API: {e}")
            self.reddit = None
    
    def scrape_subreddit(self, subreddit_name, limit=100):
        """Scrape posts from a specific subreddit"""
        if not self.reddit:
            logger.error("Reddit API not initialized")
            return
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            logger.info(f"Scraping r/{subreddit_name}...")
            
            for submission in subreddit.new(limit=limit):
                combined_text = f"{submission.title} {submission.selftext}"
                
                # Filter by relevance
                if not contains_relevant_keywords(combined_text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(combined_text)
                
                post_data = {
                    'platform': 'reddit',
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'text': f"{submission.title}\n\n{submission.selftext}",
                    'url': f"https://reddit.com{submission.permalink}",
                    'created_at': datetime.fromtimestamp(submission.created_utc),
                    'likes': submission.score,
                    'comments': submission.num_comments,
                    'shares': 0,  # Reddit doesn't track shares
                    'query': f"subreddit:{subreddit_name}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'id': submission.id,
                        'subreddit': subreddit_name,
                        'upvote_ratio': submission.upvote_ratio,
                        'is_self': submission.is_self,
                        'link_flair_text': submission.link_flair_text,
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
                logger.info(f"  ✓ Collected: {submission.title[:60]}...")
            
            logger.info(f"Collected {len(self.posts)} relevant posts from r/{subreddit_name}")
            
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit_name}: {e}")
    
    def search_reddit(self, keyword, limit=50):
        """Search Reddit globally for a keyword"""
        if not self.reddit:
            logger.error("Reddit API not initialized")
            return
        
        try:
            logger.info(f"Searching Reddit for: {keyword}")
            
            for submission in self.reddit.subreddit('all').search(keyword, limit=limit, sort='new'):
                combined_text = f"{submission.title} {submission.selftext}"
                
                # Filter by relevance
                if not contains_relevant_keywords(combined_text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(combined_text)
                
                post_data = {
                    'platform': 'reddit',
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'text': f"{submission.title}\n\n{submission.selftext}",
                    'url': f"https://reddit.com{submission.permalink}",
                    'created_at': datetime.fromtimestamp(submission.created_utc),
                    'likes': submission.score,
                    'comments': submission.num_comments,
                    'shares': 0,
                    'query': f"search:{keyword}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'id': submission.id,
                        'subreddit': submission.subreddit.display_name,
                        'upvote_ratio': submission.upvote_ratio,
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
            
            logger.info(f"Collected {len(self.posts)} posts for keyword: {keyword}")
            
        except Exception as e:
            logger.error(f"Error searching Reddit for '{keyword}': {e}")
    
    def collect_top_movements_discussion(self):
        """Collect discussions about major NRM movements"""
        # Major movements to track
        movements = [
            "scientology", "jehovah", "mormon", "hare krishna",
            "bhakti marga", "allatra", "anastasia", "osho"
        ]
        
        for movement in movements:
            self.search_reddit(movement, limit=30)
    
    def collect_from_cult_subreddits(self):
        """Collect from subreddits dedicated to cult discussions"""
        subreddits = [
            'cults',
            'exmormon',
            'exjw',  # Ex Jehovah's Witnesses
            'scientology',
            'religiousfruitcake',
        ]
        
        for subreddit in subreddits:
            self.scrape_subreddit(subreddit, limit=50)
    
    def save_to_csv(self):
        """Save collected posts to CSV"""
        if not self.posts:
            logger.warning("No posts to save")
            return
        
        df = pd.DataFrame(self.posts)
        df['collected_at'] = datetime.utcnow()
        
        # Ensure output directory exists
        Path(self.output_csv).parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(self.output_csv, index=False, encoding='utf-8')
        logger.info(f"✓ Saved {len(df)} posts to {self.output_csv}")
    
    def run(self):
        """Main execution method"""
        logger.info("Starting Reddit spider...")
        
        # Collect from multiple sources
        self.collect_from_cult_subreddits()
        self.collect_top_movements_discussion()
        
        # Save results
        self.save_to_csv()
        
        logger.info(f"Reddit spider finished. Total posts collected: {len(self.posts)}")


def main():
    """Standalone execution"""
    spider = RedditSpider()
    spider.run()


if __name__ == "__main__":
    main()
