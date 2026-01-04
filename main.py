#!/usr/bin/env python3
"""
Job Tracker - Main Application
FIXED for Render.com deployment
"""

import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web  # IMPORTANT: For HTTP server
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules
try:
    from scraper import ExpatriatesScraper
    from notifier import DiscordNotifier
    from storage import JobStorage
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Create dummy classes for testing
    class ExpatriatesScraper:
        async def scrape_jobs(self):
            return []
    
    class DiscordNotifier:
        def __init__(self, url):
            pass
        async def send_job_alert(self, job):
            logger.info(f"Would send Discord alert for: {job.get('title', 'Untitled')}")
            return True
    
    class JobStorage:
        def __init__(self):
            self.seen_jobs = {}
        def job_exists(self, job_id):
            return False
        def save_job(self, job_id):
            pass

class JobTracker:
    def __init__(self):
        self.keywords = os.getenv('JOB_KEYWORDS', '').split(',')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutes default
        
        # Clean keywords
        self.keywords = [k.strip().lower() for k in self.keywords if k.strip()]
        
        if not self.keywords:
            logger.warning("No keywords set. Using default: 'driver'")
            self.keywords = ['driver']
        
        logger.info(f"Tracking keywords: {self.keywords}")
        
        if not self.discord_webhook:
            logger.warning("No Discord webhook set. Notifications disabled.")
            self.notifications_enabled = False
        else:
            self.notifications_enabled = True
        
        self.scraper = ExpatriatesScraper()
        self.notifier = DiscordNotifier(self.discord_webhook)
        self.storage = JobStorage()
    
    def contains_keywords(self, text):
        """Check if text contains any of our keywords"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        for keyword in self.keywords:
            if keyword and keyword in text_lower:
                found_keywords.append(keyword)
        return found_keywords
    
    async def check_for_new_jobs(self):
        """Check for new job postings"""
        logger.info("Checking for new jobs...")
        
        try:
            # Scrape jobs
            jobs = await self.scraper.scrape_jobs()
            logger.info(f"Found {len(jobs)} total jobs")
            
            # Filter by keywords
            matching_jobs = []
            for job in jobs:
                # Check title and description
                title_keywords = self.contains_keywords(job.get('title', ''))
                desc_keywords = self.contains_keywords(job.get('description', ''))
                
                all_keywords = list(set(title_keywords + desc_keywords))
                
                if all_keywords:
                    job['matched_keywords'] = all_keywords
                    matching_jobs.append(job)
            
            logger.info(f"Found {len(matching_jobs)} jobs matching keywords")
            
            # Check for new jobs
            new_jobs = []
            for job in matching_jobs:
                job_id = job.get('url', job.get('title', ''))
                if not self.storage.job_exists(job_id):
                    new_jobs.append(job)
                    self.storage.save_job(job_id)
            
            # Send notifications
            if new_jobs and self.notifications_enabled:
                logger.info(f"Sending notifications for {len(new_jobs)} new jobs")
                for job in new_jobs:
                    await self.notifier.send_job_alert(job)
            elif new_jobs:
                logger.info(f"Found {len(new_jobs)} new jobs (notifications disabled)")
            
            return len(new_jobs)
            
        except Exception as e:
            logger.error(f"Error checking jobs: {e}")
            return 0
    
    async def health_check(self, request):
        """Health check endpoint for Render"""
        return web.Response(text='OK', status=200)
    
    async def status_check(self, request):
        """Status endpoint showing current configuration"""
        status = {
            'status': 'running',
            'keywords': self.keywords,
            'check_interval': self.check_interval,
            'notifications_enabled': self.notifications_enabled,
            'last_check': datetime.now().isoformat()
        }
        return web.json_response(status)
    
    async def manual_check(self, request):
        """Manually trigger a job check"""
        new_jobs = await self.check_for_new_jobs()
        return web.json_response({
            'message': f'Manual check completed. Found {new_jobs} new jobs.',
            'new_jobs': new_jobs
        })

async def background_task(tracker):
    """Background task that runs job checks periodically"""
    logger.info("Background task started")
    
    while True:
        try:
            await tracker.check_for_new_jobs()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
        
        # Wait for next check
        await asyncio.sleep(tracker.check_interval)

async def start_background_tasks(app):
    """Start background tasks when app starts"""
    tracker = app['tracker']
    app['background_task'] = asyncio.create_task(background_task(tracker))

async def cleanup_background_tasks(app):
    """Cleanup background tasks when app stops"""
    app['background_task'].cancel()
    await app['background_task']

async def create_app():
    """Create web application"""
    app = web.Application()
    
    # Create tracker instance
    tracker = JobTracker()
    app['tracker'] = tracker
    
    # Add routes
    app.add_routes([
        web.get('/', tracker.health_check),
        web.get('/health', tracker.health_check),
        web.get('/status', tracker.status_check),
        web.get('/check', tracker.manual_check),
    ])
    
    # Setup background tasks
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    return app

def main():
    """Main entry point"""
    port = int(os.getenv('PORT', 10000))
    
    # Check if we have required environment variables
    if not os.getenv('DISCORD_WEBHOOK_URL'):
        logger.warning("DISCORD_WEBHOOK_URL not set. Notifications will be disabled.")
    
    if not os.getenv('JOB_KEYWORDS'):
        logger.warning("JOB_KEYWORDS not set. Using default keywords.")
    
    logger.info(f"Starting Job Tracker on port {port}")
    logger.info(f"Check interval: {os.getenv('CHECK_INTERVAL', '1800')} seconds")
    
    # Start the web server
    web.run_app(create_app(), port=port, host='0.0.0.0')

if __name__ == "__main__":
    main()
