#!/usr/bin/env python3
"""
RSS Feed Monitor with Discord Notifications

This script monitors RSS feeds for new publications and sends notifications
to Discord when new items are found. Designed to run via crontab.

Requirements:
    pip install feedparser requests

Setup:
    1. Configure feeds and Discord webhook in the script
    2. Make executable: chmod +x rss_monitor.py
    3. Add to crontab: */15 * * * * /path/to/rss_monitor.py

"""

import feedparser
import requests
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib

# Configuration
CONFIG = {
    # Discord webhook URL - replace with your actual webhook URL
    'discord_webhook': 'https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE',
    
    # RSS feeds to monitor
    'feeds': [
        {
            'name': 'bioRxiv Ecology',
            'url': 'https://connect.biorxiv.org/biorxiv_xml.php?subject=ecology',
            'color': 0x00ff00  # Green color for Discord embed
        },
        # Add more feeds here as needed
        # {
        #     'name': 'Another Journal',
        #     'url': 'https://example.com/rss',
        #     'color': 0x0099ff
        # }
    ],
    
    # Directory to store state files
    'data_dir': os.path.expanduser('~/.rss_monitor'),
    
    # Logging configuration
    'log_file': os.path.expanduser('~/.rss_monitor/monitor.log'),
    'log_level': logging.INFO
}

class RSSMonitor:
    def __init__(self, config):
        self.config = config
        self.data_dir = Path(config['data_dir'])
        self.data_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=config['log_level'],
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_state_file(self, feed_name):
        """Get the state file path for a specific feed"""
        safe_name = "".join(c for c in feed_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        return self.data_dir / f"{safe_name}_state.json"
    
    def load_seen_items(self, feed_name):
        """Load previously seen items for a feed"""
        state_file = self.get_state_file(feed_name)
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('seen_items', []))
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Error loading state for {feed_name}: {e}")
                return set()
        return set()
    
    def save_seen_items(self, feed_name, seen_items):
        """Save seen items for a feed"""
        state_file = self.get_state_file(feed_name)
        try:
            data = {
                'seen_items': list(seen_items),
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            self.logger.error(f"Error saving state for {feed_name}: {e}")
    
    def generate_item_id(self, entry):
        """Generate a unique ID for a feed entry"""
        # Use DOI if available, otherwise use link, otherwise use title+date
        if hasattr(entry, 'id') and entry.id:
            return entry.id
        elif hasattr(entry, 'link') and entry.link:
            return entry.link
        else:
            # Fallback: hash of title and published date
            content = f"{entry.get('title', '')}{entry.get('published', '')}"
            return hashlib.md5(content.encode()).hexdigest()
    
    def extract_doi_url(self, entry):
        """Extract DOI URL from entry"""
        # Try to get DOI from identifier
        if hasattr(entry, 'id') and 'doi:' in entry.id:
            doi = entry.id.replace('doi:', '')
            return f"https://doi.org/{doi}"
        
        # Try to extract from description or other fields
        for field in ['link', 'id', 'identifier']:
            if hasattr(entry, field):
                value = getattr(entry, field)
                if 'doi.org' in str(value):
                    return value
                elif 'doi:' in str(value):
                    doi = str(value).split('doi:')[1].strip()
                    return f"https://doi.org/{doi}"
        
        # Fallback to the entry link
        return getattr(entry, 'link', '')
    
    def clean_description(self, description, max_length=1000):
        """Clean and truncate description for Discord"""
        if not description:
            return "No description available"
        
        # Remove HTML tags and extra whitespace
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = re.sub(r'\s+', ' ', description).strip()
        
        if len(description) > max_length:
            description = description[:max_length-3] + "..."
        
        return description
    
    def send_discord_notification(self, feed_name, entries, feed_color):
        """Send Discord notification for new entries"""
        if not entries:
            return
        
        webhook_url = self.config['discord_webhook']
        if not webhook_url or 'YOUR_WEBHOOK_URL_HERE' in webhook_url:
            self.logger.error("Discord webhook URL not configured")
            return
        
        for entry in entries:
            title = entry.get('title', 'Untitled')
            description = self.clean_description(entry.get('description', ''))
            doi_url = self.extract_doi_url(entry)
            published = entry.get('published', 'Unknown date')
            authors = entry.get('dc_creator', 'Unknown authors')
            
            # Create Discord embed
            embed = {
                "title": title[:256],  # Discord title limit
                "description": description,
                "url": doi_url,
                "color": feed_color,
                "fields": [
                    {
                        "name": "Authors",
                        "value": authors[:1024] if authors else "Unknown",
                        "inline": False
                    },
                    {
                        "name": "Published",
                        "value": published,
                        "inline": True
                    },
                    {
                        "name": "Source",
                        "value": feed_name,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "RSS Monitor",
                    "icon_url": "https://cdn.discordapp.com/embed/avatars/0.png"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            payload = {
                "content": f"🔬 **New Publication Alert!**",
                "embeds": [embed]
            }
            
            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                self.logger.info(f"Sent notification for: {title[:50]}...")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to send Discord notification: {e}")
    
    def process_feed(self, feed_config):
        """Process a single RSS feed"""
        feed_name = feed_config['name']
        feed_url = feed_config['url']
        feed_color = feed_config.get('color', 0x0099ff)
        
        self.logger.info(f"Processing feed: {feed_name}")
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                self.logger.warning(f"Feed {feed_name} has parsing issues: {feed.bozo_exception}")
            
            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {feed_name}")
                return
            
            # Load previously seen items
            seen_items = self.load_seen_items(feed_name)
            new_entries = []
            
            # Check for new entries
            for entry in feed.entries:
                item_id = self.generate_item_id(entry)
                if item_id not in seen_items:
                    new_entries.append(entry)
                    seen_items.add(item_id)
            
            if new_entries:
                self.logger.info(f"Found {len(new_entries)} new entries in {feed_name}")
                self.send_discord_notification(feed_name, new_entries, feed_color)
            else:
                self.logger.info(f"No new entries in {feed_name}")
            
            # Save updated state
            self.save_seen_items(feed_name, seen_items)
            
        except Exception as e:
            self.logger.error(f"Error processing feed {feed_name}: {e}")
    
    def run(self):
        """Main execution method"""
        self.logger.info("Starting RSS monitor")
        
        for feed_config in self.config['feeds']:
            self.process_feed(feed_config)
        
        self.logger.info("RSS monitor completed")

def main():
    """Main function"""
    try:
        monitor = RSSMonitor(CONFIG)
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitor interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
