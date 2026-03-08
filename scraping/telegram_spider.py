# 📁 scraping/telegram_spider.py
# Telegram Spider for collecting posts from Telegram channels about NRM
# Collects both: discussions ABOUT NRM and content FROM official NRM channels
# Project: Religious Movements Research Database

from telethon import TelegramClient
from telethon.tl.types import Channel
import pandas as pd
from datetime import datetime
import json
import logging
import sys
from pathlib import Path
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from extracting.keywords import contains_relevant_keywords, match_movement_from_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramSpider:
    """
    Spider for collecting Telegram channel posts about religious movements.
    
    Telegram is important because:
    - Many NRM have official channels
    - Conspiracy/alternative groups use Telegram heavily
    - Czech alternative spirituality communities are active there
    """
    
    def __init__(self, api_id=None, api_hash=None, output_csv="export/csv/telegram_raw.csv"):
        self.output_csv = output_csv
        self.posts = []
        self.api_id = api_id or "YOUR_API_ID"  # Get from https://my.telegram.org
        self.api_hash = api_hash or "YOUR_API_HASH"
        
        try:
            self.client = TelegramClient('nrm_research_session', int(self.api_id), self.api_hash)
            logger.info("✓ Telegram client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram client: {e}")
            self.client = None
    
    async def scrape_channel(self, channel_username, limit=100):
        """Scrape messages from a Telegram channel"""
        try:
            logger.info(f"Scraping Telegram channel: {channel_username}")
            
            # Get channel entity
            channel = await self.client.get_entity(channel_username)
            
            # Fetch messages
            async for message in self.client.iter_messages(channel, limit=limit):
                if not message.text:
                    continue
                
                # Filter by relevance
                if not contains_relevant_keywords(message.text, min_hits=1):
                    continue
                
                # Check for movement match
                movement_id = match_movement_from_text(message.text)
                
                # Get engagement metrics
                views = message.views if message.views else 0
                forwards = message.forwards if message.forwards else 0
                
                post_data = {
                    'platform': 'telegram',
                    'author': channel.title if isinstance(channel, Channel) else channel_username,
                    'text': message.text,
                    'url': f"https://t.me/{channel_username}/{message.id}",
                    'created_at': message.date,
                    'likes': 0,  # Telegram doesn't have likes
                    'comments': 0,  # Would need to fetch replies separately
                    'shares': forwards,
                    'query': f"channel:{channel_username}",
                    'movement_id': movement_id,
                    'raw_json': json.dumps({
                        'message_id': message.id,
                        'views': views,
                        'forwards': forwards,
                        'has_media': message.media is not None,
                        'channel_id': channel.id,
                    }, ensure_ascii=False)
                }
                
                self.posts.append(post_data)
                logger.info(f"  ✓ Collected message from {channel_username}: {message.text[:50]}...")
            
            logger.info(f"Collected {len(self.posts)} messages from {channel_username}")
            
        except Exception as e:
            logger.error(f"Error scraping channel {channel_username}: {e}")
    
    async def search_channels(self, keyword, limit=20):
        """Search for channels by keyword"""
        try:
            logger.info(f"Searching Telegram for channels: {keyword}")
            
            # Search for channels
            result = await self.client.get_dialogs(limit=None)
            
            matching_channels = []
            for dialog in result:
                if isinstance(dialog.entity, Channel):
                    if keyword.lower() in dialog.title.lower():
                        matching_channels.append(dialog.entity.username)
            
            logger.info(f"Found {len(matching_channels)} matching channels")
            
            # Scrape matching channels
            for channel in matching_channels[:limit]:
                if channel:
                    await self.scrape_channel(channel, limit=50)
            
        except Exception as e:
            logger.error(f"Error searching channels: {e}")
    
    async def collect_from_known_nrm_channels(self):
        """
        Collect from known NRM Telegram channels
        These would be official channels FROM movements
        """
        # Known Czech/Slovak NRM and alternative spirituality channels
        # You would need to research and add real channel usernames
        known_channels = [
            # Example channels (replace with real ones after research):
            # "allatra_cz",
            # "bhaktimarga_czech",
            # Add more as you discover them
        ]
        
        for channel in known_channels:
            await self.scrape_channel(channel, limit=100)
    
    async def collect_conspiracy_spirituality_channels(self):
        """
        Collect from conspiracy/alternative spirituality channels
        These often discuss or promote NRM without being official channels
        """
        # Channels that discuss alternative spirituality, conspiracies
        # which often overlap with NRM topics
        channels = [
            # Add discovered channels related to:
            # - Alternative medicine
            # - Conspiracy theories
            # - New age spirituality
            # - Czech alternative communities
        ]
        
        for channel in channels:
            await self.scrape_channel(channel, limit=50)
    
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
    
    async def run_async(self):
        """Main async execution method"""
        logger.info("Starting Telegram spider...")
        
        await self.client.start()
        
        try:
            # Collect from multiple sources
            await self.collect_from_known_nrm_channels()
            await self.collect_conspiracy_spirituality_channels()
            
            # Save results
            self.save_to_csv()
            
            logger.info(f"Telegram spider finished. Total posts collected: {len(self.posts)}")
        
        finally:
            await self.client.disconnect()
    
    def run(self):
        """Synchronous wrapper for async execution"""
        if not self.client:
            logger.error("Telegram client not initialized")
            return
        
        asyncio.run(self.run_async())


def main():
    """Standalone execution"""
    spider = TelegramSpider()
    spider.run()


if __name__ == "__main__":
    main()
