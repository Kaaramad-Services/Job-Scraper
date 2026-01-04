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
        """Parse job listings from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Find job listings - adjust selectors based on actual website structure
        listings = soup.find_all('div', class_='listing') or soup.find_all('tr', class_='listing')
        
        for listing in listings[:50]:  # Limit to 50 listings
            try:
                job = {}
                
                # Extract title and URL
                title_elem = listing.find('a', class_='title') or listing.find('a')
                if title_elem:
                    job['title'] = title_elem.text.strip()
                    job['url'] = urljoin(self.base_url, title_elem.get('href', ''))
                else:
                    continue  # Skip if no title
                
                # Extract description/preview
                desc_elem = listing.find('div', class_='description') or listing.find('td', class_='description')
                if desc_elem:
                    job['description'] = desc_elem.text.strip()
                else:
                    job['description'] = ""
                
                # Extract date
                date_elem = listing.find('span', class_='date') or listing.find('td', class_='date')
                if date_elem:
                    job['date_posted'] = date_elem.text.strip()
                else:
                    job['date_posted'] = "Recently"
                
                # Extract category/type
                cat_elem = listing.find('span', class_='category') or listing.find('td', class_='category')
                if cat_elem:
                    job['category'] = cat_elem.text.strip()
                else:
                    job['category'] = "General"
                
                # Extract location
                loc_elem = listing.find('span', class_='location') or listing.find('td', class_='location')
                if loc_elem:
                    job['location'] = loc_elem.text.strip()
                else:
                    job['location'] = "Saudi Arabia"
                
                # Get full description from individual page
                if job['url']:
                    job['full_description'] = self.get_full_description_sync(job['url'])
                else:
                    job['full_description'] = job['description']
                
                jobs.append(job)
                
            except Exception as e:
                logger.warning(f"Error parsing listing: {e}")
                continue
        
        return jobs
    
    def get_full_description_sync(self, url):
        """Get full description from job page (simplified - you might need async version)"""
        # For simplicity, using requests in sync mode
        # In production, make this async too
        import requests
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                desc_div = soup.find('div', class_='description') or soup.find('div', id='description')
                if desc_div:
                    return desc_div.text.strip()
        except:
            pass
        return ""
    
    def extract_contacts(self, text):
        """Extract email and phone numbers from text"""
        contacts = {'email': 'Not found', 'whatsapp': 'Not found'}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contacts['email'] = emails[0]  # Take first email
        
        # Extract phone numbers (including WhatsApp)
        phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        phones = re.findall(phone_pattern, text)
        
        # Look for WhatsApp specifically
        whatsapp_pattern = r'(?:whatsapp|wa\.?)\s*[:]?\s*(\+?\d[\d\s\-\(\)]{8,}\d)'
        whatsapp_match = re.search(whatsapp_pattern, text.lower())
        
        if whatsapp_match:
            contacts['whatsapp'] = whatsapp_match.group(1)
        elif phones:
            contacts['whatsapp'] = phones[0]  # Take first phone as potential WhatsApp
        
        return contacts
    
    async def scrape_jobs(self):
        """Main scraping function"""
        html = await self.fetch_page(self.saudi_url)
        if html:
            jobs = self.parse_job_listings(html)
            return jobs
        return []