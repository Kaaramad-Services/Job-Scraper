#!/usr/bin/env python3
"""
Job Tracker - Main Application
Monitors expatriates.com for job postings with specific keywords
Sends Discord notifications for new matches
"""

import os
import time
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from scraper import ExpatriatesScraper
from notifier import DiscordNotifier
from storage import JobStorage

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JobTracker:
    def __init__(self):
        self.keywords = os.getenv('JOB_KEYWORDS', '').split(',')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '600'))  # Default 10 minutes
        
        if not self.keywords or self.keywords[0] == '':
            raise ValueError("Please set JOB_KEYWORDS environment variable")
        
        if not self.discord_webhook:
            raise ValueError("Please set DISCORD_WEBHOOK_URL environment variable")
        
        self.scraper = ExpatriatesScraper()
        self.notifier = DiscordNotifier(self.discord_webhook)
        self.storage = JobStorage()
        
        logger.info(f"Job Tracker initialized with keywords: {self.keywords}")
    
    def contains_keywords(self, text):
        """Check if text contains any of our keywords"""
        text_lower = text.lower()
        found_keywords = []
        for keyword in self.keywords:
            keyword = keyword.strip().lower()
            if keyword and keyword in text_lower:
                found_keywords.append(keyword)
        return found_keywords
    
    async def check_for_new_jobs(self):
        """Main function to check for new job postings"""
        logger.info("Starting job check...")
        
        try:
            # Scrape the website
            jobs = await self.scraper.scrape_jobs()
            logger.info(f"Found {len(jobs)} total job postings")
            
            # Filter by keywords
            matching_jobs = []
            for job in jobs:
                # Check title and description
                title_keywords = self.contains_keywords(job.get('title', ''))
                desc_keywords = self.contains_keywords(job.get('description', ''))
                
                all_keywords = list(set(title_keywords + desc_keywords))
                
                if all_keywords:
                    job['matched_keywords'] = all_keywords
                    
                    # Extract contacts
                    contacts = self.scraper.extract_contacts(job.get('description', ''))
                    job.update(contacts)
                    
                    matching_jobs.append(job)
            
            logger.info(f"Found {len(matching_jobs)} jobs matching keywords")
            
            # Check for new jobs
            new_jobs = []
            for job in matching_jobs:
                job_id = job.get('url', '')  # Use URL as ID
                if not self.storage.job_exists(job_id):
                    new_jobs.append(job)
                    self.storage.save_job(job_id)
            
            # Send notifications for new jobs
            if new_jobs:
                logger.info(f"Sending notifications for {len(new_jobs)} new jobs")
                for job in new_jobs:
                    await self.notifier.send_job_alert(job)
            else:
                logger.info("No new jobs found")
            
            # Cleanup old entries (older than 24 hours)
            self.storage.cleanup_old_entries()
            
        except Exception as e:
            logger.error(f"Error during job check: {e}")
            # Send error notification to Discord
            await self.notifier.send_error_notification(str(e))
    
    async def run(self):
        """Main loop"""
        logger.info("Job Tracker started!")
        
        # Send startup notification
        await self.notifier.send_startup_notification(self.keywords)
        
        while True:
            try:
                await self.check_for_new_jobs()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            # Wait for next check
            logger.info(f"Waiting {self.check_interval} seconds until next check...")
            await asyncio.sleep(self.check_interval)

async def main():
    """Entry point"""
    try:
        tracker = JobTracker()
        await tracker.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ ERROR: {e}")
        print("\nPlease set the following environment variables:")
        print("1. JOB_KEYWORDS=driver,engineer,teacher (comma-separated)")
        print("2. DISCORD_WEBHOOK_URL=your_discord_webhook_url")
        print("\nFor Render.com, set these in your dashboard under Environment")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())