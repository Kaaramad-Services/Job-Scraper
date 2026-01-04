"""
Web scraper for expatriates.com
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin
from datetime import datetime

logger = logging.getLogger(__name__)

class ExpatriatesScraper:
    def __init__(self):
        self.base_url = "https://www.expatriates.com"
        self.saudi_url = "https://www.expatriates.com/classifieds/saudi-arabia/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def fetch_page(self, url):
        """Fetch a webpage asynchronously"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"Failed to fetch {url}: Status {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                return None
    
    def parse_job_listings(self, html):
        """Parse job listings from HTML - using html.parser instead of lxml"""
        soup = BeautifulSoup(html, 'html.parser')  # Changed from 'lxml' to 'html.parser'
        jobs = []
        
        # Find all job listings - try different selectors
        # First try: look for listing items
        listings = []
        
        # Try multiple possible selectors
        possible_selectors = [
            'div.listing',
            'tr.listing',
            '.listing-row',
            '.classified-item',
            '.ad-item',
            'div[class*="listing"]',
            'tr[class*="listing"]'
        ]
        
        for selector in possible_selectors:
            found = soup.select(selector)
            if found:
                listings = found
                logger.info(f"Found {len(listings)} listings with selector: {selector}")
                break
        
        # If no specific selectors found, try to find any job-like containers
        if not listings:
            # Look for common patterns
            all_links = soup.find_all('a')
            for link in all_links:
                if '/classifieds/' in link.get('href', '') and 'saudi-arabia' in link.get('href', ''):
                    parent = link.parent
                    if parent not in listings:
                        listings.append(parent)
            
            logger.info(f"Found {len(listings)} listings via link search")
        
        for listing in listings[:50]:  # Limit to 50 listings
            try:
                job = {}
                
                # Extract title and URL
                title_elem = listing.find('a')
                if title_elem:
                    job['title'] = title_elem.text.strip()
                    href = title_elem.get('href', '')
                    if href and not href.startswith('http'):
                        job['url'] = urljoin(self.base_url, href)
                    else:
                        job['url'] = href
                else:
                    continue  # Skip if no title
                
                # Extract description/preview
                desc_text = listing.get_text()
                # Remove title from description
                if 'title' in job:
                    desc_text = desc_text.replace(job['title'], '')
                job['description'] = desc_text.strip()[:500]  # Limit to 500 chars
                
                # Try to find date
                date_patterns = ['Posted', 'Date:', 'Added']
                job['date_posted'] = "Recently"
                for pattern in date_patterns:
                    if pattern in desc_text:
                        # Extract date-like text after pattern
                        idx = desc_text.find(pattern)
                        if idx != -1:
                            date_text = desc_text[idx:idx+50]
                            job['date_posted'] = date_text.strip()
                            break
                
                job['category'] = "General"
                job['location'] = "Saudi Arabia"
                job['full_description'] = job['description']
                
                jobs.append(job)
                
            except Exception as e:
                logger.warning(f"Error parsing listing: {e}")
                continue
        
        return jobs
    
    def extract_contacts(self, text):
        """Extract email and phone numbers from text"""
        contacts = {'email': 'Not found', 'whatsapp': 'Not found'}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text, re.IGNORECASE)
        if emails:
            contacts['email'] = emails[0]  # Take first email
        
        # Extract phone numbers (including WhatsApp)
        phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        
        # Look for WhatsApp specifically
        whatsapp_pattern = r'(?:whatsapp|wa\.?)[:\s]*(\+?\d[\d\s\-\(\)]{8,}\d)'
        whatsapp_match = re.search(whatsapp_pattern, text.lower())
        
        if whatsapp_match:
            contacts['whatsapp'] = whatsapp_match.group(1).strip()
        elif phones:
            contacts['whatsapp'] = phones[0].strip()
        
        return contacts
    
    async def scrape_jobs(self):
        """Main scraping function"""
        html = await self.fetch_page(self.saudi_url)
        if html:
            jobs = self.parse_job_listings(html)
            return jobs
        return []
