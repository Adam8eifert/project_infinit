# 📁 scraping/mastodon_spider.py
# Mastodon Spider for collecting posts from Mastodon/Fediverse about NRM
# Mastodon is important for Czech alternative/progressive communities
# Project: Religious Movements Research Database

from mastodon import Mastodon as MastodonAPI
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


class MastodonSpider:
    """
    Spider for collecting Mastodon (Fediverse) posts about religious movements.
    
    Mastodon/Fediverse is relevant because:
    - Czech progressive/alternative communities use it
    - Ex-members of cults often discuss there
    - More open discussion than mainstream social media
    """
    
    def __init__(self, instance_url="https://mastodon.social", output_csv="export/csv/mastodon_raw.csv"):
        self.output_csv = output_csv
        self.posts = []
        self.instance_url = instance_url
        
        try:
            # Initialize Mastodon client (public API, no auth needed for reading)
            self.mastodon = MastodonAPI(
                api_base_url=instance_url
            )
            logger.info(f"✓ Mastodon client initialized for {instance_url}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Mastodon client: {e}")
            self.mastodon = None
    
    def search_hashtag(self, hashtag, limit=100):
        """Search for posts with a specific hashtag"""
        if not self.mastodon:
            logger.error("Mastodon client not initialized")
            return
        
        try:
            logger.info(f"Searching Mastodon for hashtag: #{hashtag}")
            
            # Search using timeline_hashtag
            statuses = self.mastodon.timeline_hashtag(
                hashtag,
                limit=limit
            )
            
            for status in statuses:
                # Extract text content
                text = self.clean_html(status['content'])
                combined_text = text
                
                # Filter by relevance
                if not contains_relevant_keywords(combined_text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(combined_text)
                
                post_data = {
                    'platform': 'mastodon',
                    'author': status['account']['username'],
                    'text': text,
                    'url': status['url'] if status['url'] else status['uri'],
                    'created_at': status['created_at'],
                    'likes': status['favourites_count'],
                    'comments': status['replies_count'],
                    'shares': status['reblogs_count'],
                    'query': f"hashtag:{hashtag}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'id': status['id'],
                        'account_id': status['account']['id'],
                        'instance': self.instance_url,
                        'language': status.get('language'),
                        'sensitive': status.get('sensitive', False),
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
                logger.info(f"  ✓ Collected post: {text[:50]}...")
            
            logger.info(f"Collected {len(statuses)} posts for #{hashtag}")
            
        except Exception as e:
            logger.error(f"Error searching hashtag #{hashtag}: {e}")
    
    def search_keyword(self, keyword, limit=40):
        """Search for posts containing a keyword"""
        if not self.mastodon:
            logger.error("Mastodon client not initialized")
            return
        
        try:
            logger.info(f"Searching Mastodon for keyword: {keyword}")
            
            # Use search API
            results = self.mastodon.search_v2(
                keyword,
                result_type="statuses",
                resolve=False
            )
            
            statuses = results.get('statuses', [])[:limit]
            
            for status in statuses:
                text = self.clean_html(status['content'])
                
                # Filter by relevance
                if not contains_relevant_keywords(text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(text)
                
                post_data = {
                    'platform': 'mastodon',
                    'author': status['account']['username'],
                    'text': text,
                    'url': status['url'] if status['url'] else status['uri'],
                    'created_at': status['created_at'],
                    'likes': status['favourites_count'],
                    'comments': status['replies_count'],
                    'shares': status['reblogs_count'],
                    'query': f"search:{keyword}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'id': status['id'],
                        'account_id': status['account']['id'],
                        'instance': self.instance_url,
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
            
            logger.info(f"Collected {len(statuses)} posts for keyword: {keyword}")
            
        except Exception as e:
            logger.error(f"Error searching keyword '{keyword}': {e}")
    
    def clean_html(self, html_content):
        """Remove HTML tags from Mastodon content"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Decode HTML entities
        import html
        text = html.unescape(text)
        return text.strip()
    
    def collect_nrm_discussions(self):
        """Collect discussions about NRM using relevant hashtags and keywords"""
        # Relevant Czech/international hashtags
        hashtags = [
            'sekta',
            'kult',
            'cult',
            'scientology',
            'exmo',  # Ex-Mormon
            'exjw',  # Ex-JW
            'cultsurvivor',
        ]
        
        for hashtag in hashtags:
            self.search_hashtag(hashtag, limit=50)
        
        # Also search by keywords
        keywords = [
            "scientologie",
            "svědkové jehovovi",
            "nové náboženství",
            "sekty",
        ]
        
        for keyword in keywords:
            self.search_keyword(keyword, limit=30)
    
    def collect_from_czech_instances(self):
        """
        Collect from Czech Mastodon instances
        Czech users cluster on specific instances
        """
        czech_instances = [
            "https://mastodon.online",  # Has Czech community
            # Add more Czech instances as discovered
        ]
        
        for instance in czech_instances:
            try:
                # Switch to different instance
                self.instance_url = instance
                self.mastodon = MastodonAPI(api_base_url=instance)
                logger.info(f"Switched to instance: {instance}")
                
                # Collect from public timeline
                self.collect_nrm_discussions()
                
            except Exception as e:
                logger.error(f"Error with instance {instance}: {e}")
    
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
        logger.info("Starting Mastodon spider...")
        
        # Collect from multiple sources
        self.collect_nrm_discussions()
        self.collect_from_czech_instances()
        
        # Save results
        self.save_to_csv()
        
        logger.info(f"Mastodon spider finished. Total posts collected: {len(self.posts)}")


def main():
    """Standalone execution"""
    spider = MastodonSpider()
    spider.run()


if __name__ == "__main__":
    main()
