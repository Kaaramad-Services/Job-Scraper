"""
Discord notification module
"""

import aiohttp
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    async def send_webhook(self, embed_data):
        """Send data to Discord webhook"""
        payload = {
            "embeds": [embed_data],
            "username": "Job Tracker Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/3082/3082383.png"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        logger.info("Discord notification sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Discord webhook error: {response.status} - {error_text}")
                        return False
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")
                return False
    
    async def send_job_alert(self, job):
        """Send job alert to Discord"""
        embed = {
            "title": f"🚨 NEW JOB MATCH: {job.get('title', 'Untitled')}",
            "description": job.get('description', '')[:200] + "...",
            "color": 0x00ff00,
            "fields": [
                {
                    "name": "📍 Location",
                    "value": job.get('location', 'Saudi Arabia'),
                    "inline": True
                },
                {
                    "name": "📅 Posted",
                    "value": job.get('date_posted', 'Recently'),
                    "inline": True
                },
                {
                    "name": "📧 Email",
                    "value": f"`{job.get('email', 'Not found')}`",
                    "inline": True
                },
                {
                    "name": "📱 WhatsApp",
                    "value": f"`{job.get('whatsapp', 'Not found')}`",
                    "inline": True
                },
                {
                    "name": "🔑 Matched Keywords",
                    "value": ", ".join(job.get('matched_keywords', [])),
                    "inline": True
                },
                {
                    "name": "🏢 Category",
                    "value": job.get('category', 'General'),
                    "inline": True
                }
            ],
            "url": job.get('url', ''),
            "footer": {
                "text": f"Job Tracker • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        await self.send_webhook(embed)
    
    async def send_startup_notification(self, keywords):
        """Send startup notification"""
        embed = {
            "title": "✅ Job Tracker Started",
            "description": "I'm now monitoring expatriates.com for new job postings!",
            "color": 0x3498db,
            "fields": [
                {
                    "name": "📌 Tracking Keywords",
                    "value": ", ".join(keywords)
                },
                {
                    "name": "⏰ Check Interval",
                    "value": "Every 10 minutes"
                },
                {
                    "name": "🌐 Target Website",
                    "value": "expatriates.com/classifieds/saudi-arabia/"
                }
            ],
            "footer": {
                "text": f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        await self.send_webhook(embed)
    
    async def send_error_notification(self, error_message):
        """Send error notification"""
        embed = {
            "title": "❌ Job Tracker Error",
            "description": "An error occurred while checking for jobs:",
            "color": 0xff0000,
            "fields": [
                {
                    "name": "Error Details",
                    "value": f"```{error_message[:500]}```"
                }
            ],
            "footer": {
                "text": f"Error at {datetime.now().strftime('%H:%M:%S')}"
            }
        }
        
        await self.send_webhook(embed)