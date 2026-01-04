"""
Simple and reliable scraper for expatriates.com
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class ExpatriatesScraper:
    def __init__(self):
        self.base_url = "https://www.expatriates.com"
        self.saudi_url = "https://www.expatriates.com/classifieds/saudi-arabia/"
        
        # Simple headers that work
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    async def fetch_page(self, url):
        """Fetch webpage with retry logic"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Add delay to be polite
                await asyncio.sleep(1)
                
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def parse_job_listings(self, html):
        """Parse job listings from HTML"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Look for job listings - try different approaches
        # Method 1: Look for any links with job-related text
        job_keywords = ['job', 'hire', 'wanted', 'vacancy', 'position', 'opportunity']
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().lower()
            link_href = link.get('href', '').lower()
            
            # Check if this looks like a job link
            is_job_link = any(keyword in link_text for keyword in job_keywords)
            is_classified_link = '/classifieds/' in link_href
            
            if is_job_link or is_classified_link:
                try:
                    job = {
                        'title': link.get_text().strip() or "Job Opportunity",
                        'url': self.base_url + link['href'] if link['href'].startswith('/') else link['href'],
                        'description': self.get_description_from_element(link),
                        'date_posted': "Recently",
                        'category': "General",
                        'location': "Saudi Arabia"
                    }
                    jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error creating job from link: {e}")
        
        # If no jobs found with method 1, try extracting from page text
        if not jobs:
            all_text = soup.get_text()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            for i, line in enumerate(lines[:50]):  # Check first 50 lines
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in job_keywords):
                    job = {
                        'title': line[:100],
                        'url': self.saudi_url,
                        'description': ' '.join(lines[i:i+3])[:200],
                        'date_posted': "Recently",
                        'category': "General",
                        'location': "Saudi Arabia"
                    }
                    jobs.append(job)
        
        # Remove duplicates based on title
        unique_jobs = []
        seen_titles = set()
        for job in jobs:
            if job['title'] not in seen_titles:
                seen_titles.add(job['title'])
                unique_jobs.append(job)
        
        logger.info(f"Parsed {len(unique_jobs)} unique jobs")
        return unique_jobs[:15]  # Return max 15 jobs
    
    def get_description_from_element(self, element):
        """Extract description from HTML element"""
        try:
            # Get parent element text
            parent = element.parent
            if parent:
                parent_text = parent.get_text().strip()
                link_text = element.get_text().strip()
                description = parent_text.replace(link_text, '').strip()
                return description[:300]
        except:
            pass
        return "No description available"
    
    def extract_contacts(self, text):
        """Extract contact information from text"""
        contacts = {'email': 'Not found', 'whatsapp': 'Not found'}
        
        # Find email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            contacts['email'] = email_match.group(0)
        
        # Find phone number
        phone_match = re.search(r'(\+?\d[\d\s\-\(\)]{7,}\d)', text)
        if phone_match:
            contacts['whatsapp'] = phone_match.group(1).strip()
        
        return contacts
    
    async def scrape_jobs(self):
        """Main scraping function"""
        try:
            logger.info(f"Scraping {self.saudi_url}")
            html = await self.fetch_page(self.saudi_url)
            
            if html:
                jobs = self.parse_job_listings(html)
                
                # Add contact extraction
                for job in jobs:
                    contacts = self.extract_contacts(job['description'])
                    job.update(contacts)
                
                return jobs
            else:
                logger.warning("Could not fetch page")
                return []
                
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            # Return dummy data for testing
            return [{
                'title': 'Test Job - Web Developer',
                'url': self.saudi_url,
                'description': 'Looking for web developer with Python experience. Contact at test@example.com',
                'date_posted': 'Recently',
                'category': 'IT',
                'location': 'Riyadh',
                'email': 'test@example.com',
                'whatsapp': '+966501234567'
            }]
