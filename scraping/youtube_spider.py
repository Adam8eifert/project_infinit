# 📁 scraping/youtube_spider.py
# YouTube Spider for collecting videos and comments about New Religious Movements
# Collects both: discussions ABOUT NRM and content FROM NRM channels
# Project: Religious Movements Research Database

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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


class YouTubeSpider:
    """
    Spider for collecting YouTube videos and comments about religious movements.
    
    Collects:
    - Videos about NRM (documentaries, discussions, investigations)
    - Videos FROM NRM channels (official movement content)
    - Comments on relevant videos
    """
    
    def __init__(self, api_key=None, output_csv="export/csv/youtube_raw.csv"):
        self.output_csv = output_csv
        self.posts = []
        self.api_key = api_key or "YOUR_YOUTUBE_API_KEY"  # Set in environment
        
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            logger.info("✓ YouTube API client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize YouTube API: {e}")
            self.youtube = None
    
    def search_videos(self, query, max_results=50):
        """Search for videos by keyword"""
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return
        
        try:
            logger.info(f"Searching YouTube for: {query}")
            
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                order="date",
                relevanceLanguage="cs",  # Czech language preference
                regionCode="CZ"
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = item['id']['videoId']
                
                # Get video statistics
                stats = self.get_video_stats(video_id)
                
                combined_text = f"{snippet['title']} {snippet['description']}"
                
                # Filter by relevance
                if not contains_relevant_keywords(combined_text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(combined_text)
                
                post_data = {
                    'platform': 'youtube',
                    'author': snippet['channelTitle'],
                    'text': f"{snippet['title']}\n\n{snippet['description']}",
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'created_at': datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                    'likes': stats.get('likeCount', 0),
                    'comments': stats.get('commentCount', 0),
                    'shares': 0,  # Not directly available
                    'query': query,
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'video_id': video_id,
                        'channel_id': snippet['channelId'],
                        'view_count': stats.get('viewCount', 0),
                        'thumbnails': snippet.get('thumbnails', {}),
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
                logger.info(f"  ✓ Collected: {snippet['title'][:60]}...")
            
            logger.info(f"Collected {len(response.get('items', []))} videos for query: {query}")
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
    
    def get_video_stats(self, video_id):
        """Get detailed statistics for a video"""
        try:
            request = self.youtube.videos().list(
                part="statistics",
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                stats = response['items'][0]['statistics']
                return {
                    'viewCount': int(stats.get('viewCount', 0)),
                    'likeCount': int(stats.get('likeCount', 0)),
                    'commentCount': int(stats.get('commentCount', 0)),
                }
            return {}
        except Exception as e:
            logger.warning(f"Could not fetch stats for video {video_id}: {e}")
            return {}
    
    def scrape_channel_videos(self, channel_id, max_results=20):
        """Scrape videos from a specific channel (e.g., official NRM channel)"""
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return
        
        try:
            logger.info(f"Scraping channel: {channel_id}")
            
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                maxResults=max_results,
                order="date"
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = item['id']['videoId']
                stats = self.get_video_stats(video_id)
                
                combined_text = f"{snippet['title']} {snippet['description']}"
                movement_id = match_movement_from_text(combined_text)
                
                post_data = {
                    'platform': 'youtube',
                    'author': snippet['channelTitle'],
                    'text': f"{snippet['title']}\n\n{snippet['description']}",
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'created_at': datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                    'likes': stats.get('likeCount', 0),
                    'comments': stats.get('commentCount', 0),
                    'shares': 0,
                    'query': f"channel:{channel_id}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'video_id': video_id,
                        'channel_id': channel_id,
                        'view_count': stats.get('viewCount', 0),
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
            
            logger.info(f"Collected {len(response.get('items', []))} videos from channel")
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
        except Exception as e:
            logger.error(f"Error scraping channel: {e}")
    
    def collect_nrm_content(self):
        """Collect content about major NRM movements"""
        keywords = [
            "scientologie dokumentární",
            "svědkové jehovovi dokumentární",
            "hare krishna česko",
            "bhakti marga česko",
            "allatra sekta",
            "anastasia hnutí",
            "osho rajneesh",
            "sekty česko",
            "nová náboženská hnutí"
        ]
        
        for keyword in keywords:
            self.search_videos(keyword, max_results=20)
    
    def collect_from_official_channels(self):
        """
        Collect content FROM official NRM channels
        Add channel IDs of known NRM YouTube channels here
        """
        # Example channel IDs (these would need to be researched)
        official_channels = [
            # Add real channel IDs here
            # "UCxxxxxxxxxxxxxxxxxxxxxx",  # Example: Bhakti Marga CZ
        ]
        
        for channel_id in official_channels:
            self.scrape_channel_videos(channel_id, max_results=30)
    
    def save_to_csv(self):
        """Save collected posts to CSV"""
        if not self.posts:
            logger.warning("No videos to save")
            return
        
        df = pd.DataFrame(self.posts)
        df['collected_at'] = datetime.utcnow()
        
        # Ensure output directory exists
        Path(self.output_csv).parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(self.output_csv, index=False, encoding='utf-8')
        logger.info(f"✓ Saved {len(df)} videos to {self.output_csv}")
    
    def run(self):
        """Main execution method"""
        logger.info("Starting YouTube spider...")
        
        # Collect from multiple sources
        self.collect_nrm_content()
        self.collect_from_official_channels()
        
        # Save results
        self.save_to_csv()
        
        logger.info(f"YouTube spider finished. Total videos collected: {len(self.posts)}")


def main():
    """Standalone execution"""
    spider = YouTubeSpider()
    spider.run()


if __name__ == "__main__":
    main()
