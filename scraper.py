"""
Web scraper for expatriates.com with anti-blocking measures
"""

import aiohttp
import asyncio
import random
import time
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin
from datetime import datetime
import cloudscraper  # ADD THIS IMPORT - handles Cloudflare

logger = logging.getLogger(__name__)

class ExpatriatesScraper:
    def __init__(self):
        self.base_url = "https://www.expatriates.com"
        self.saudi_url = "https://www.expatriates.com/classifieds/saudi-arabia/"
        
        # More realistic headers to avoid detection
        self.headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
            },
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            }
        ]
        
        # Initialize cloudscraper for Cloudflare bypass
        try:
            self.scraper = cloudscraper.create_scraper()
            logger.info("Cloudscraper initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize cloudscraper: {e}")
            self.scraper = None
    
    def get_random_headers(self):
        """Get random headers to avoid detection"""
        return random.choice(self.headers_list)
    
    async def fetch_page_async(self, url):
        """Fetch webpage using aiohttp with better headers"""
        headers = self.get_random_headers()
        
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Add random delay to seem more human
                await asyncio.sleep(random.uniform(1, 3))
                
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        logger.info(f"Successfully fetched {url}")
                        return html
                    elif response.status == 403:
                        logger.warning(f"403 Forbidden for {url} - trying alternative method")
                        # Try sync method with cloudscraper
                        return await self.fetch_page_sync(url)
                    else:
                        logger.error(f"Failed to fetch {url}: Status {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching {url} with aiohttp: {e}")
                # Fall back to sync method
                return await self.fetch_page_sync(url)
    
    async def fetch_page_sync(self, url):
        """Fetch webpage using cloudscraper (sync but wrapped in async)"""
        try:
            # Run sync cloudscraper in thread pool
            loop = asyncio.get_event_loop()
            
            if self.scraper:
                html = await loop.run_in_executor(
                    None, 
                    lambda: self.scraper.get(url, timeout=10).text
                )
                logger.info(f"Successfully fetched {url} with cloudscraper")
                return html
            else:
                # Fallback to requests with good headers
                import requests
                headers = self.get_random_headers()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, headers=headers, timeout=10)
                )
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Requests fallback failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error in sync fetch for {url}: {e}")
            return None
    
    async def fetch_page(self, url):
        """Main fetch method - tries async first, then sync fallback"""
        return await self.fetch_page_async(url)
    
    def parse_job_listings(self, html):
        """Parse job listings from HTML"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Try different selectors for expatriates.com
        # Based on common patterns for classified sites
        
        # Pattern 1: Look for listing containers
        listings = soup.find_all(['div', 'tr'], class_=lambda x: x and 'listing' in str(x).lower())
        
        # Pattern 2: Look for items with links to classifieds
        if not listings:
            all_links = soup.find_all('a', href=lambda x: x and '/classifieds/' in x)
            for link in all_links:
                if 'saudi-arabia' in link.get('href', ''):
                    # Get the parent container
                    parent = link.find_parent(['div', 'tr', 'li'])
                    if parent and parent not in listings:
                        listings.append(parent)
        
        # Pattern 3: Look for any job-like content
        if not listings:
            # Try to find any containers with job-like text
            for element in soup.find_all(['div', 'td', 'tr']):
                text = element.get_text().lower()
                if any(keyword in text for keyword in ['job', 'hire', 'wanted', 'position', 'vacancy']):
                    listings.append(element)
        
        logger.info(f"Found {len(listings)} potential job listings")
        
        for listing in listings[:30]:  # Limit to 30 to avoid too many requests
            try:
                job = {}
                
                # Find title link
                title_link = listing.find('a')
                if not title_link:
                    # Try to find any link in the listing
                    links = listing.find_all('a')
                    title_link = links[0] if links else None
                
                if title_link:
                    job['title'] = title_link.text.strip()
                    href = title_link.get('href', '')
                    if href:
                        if href.startswith('/'):
                            job['url'] = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            job['url'] = href
                        else:
                            job['url'] = urljoin(self.base_url, '/' + href.lstrip('/'))
                else:
                    # Try to extract title from text
                    text = listing.get_text().strip()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        job['title'] = lines[0][:100]
                    else:
                        job['title'] = "Untitled Job"
                    job['url'] = self.saudi_url
                
                # Extract description
                full_text = listing.get_text().strip()
                # Remove title from description
                if 'title' in job:
                    desc = full_text.replace(job['title'], '').strip()
                else:
                    desc = full_text
                
                # Clean up description
                desc_lines = [line.strip() for line in desc.split('\n') if line.strip()]
                job['description'] = ' '.join(desc_lines[:5])[:300]
                job['full_description'] = desc[:500]
                
                # Try to extract date (look for date patterns)
                date_patterns = [
                    r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}',
                    r'\d+ (day|week|month)s? ago',
                    r'Posted:? (.+?)(?:\n|$)'
                ]
                
                job['date_posted'] = "Recently"
                for pattern in date_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        job['date_posted'] = match.group(0).strip()
                        break
                
                job['category'] = "General"
                job['location'] = "Saudi Arabia"
                
                jobs.append(job)
                
            except Exception as e:
                logger.warning(f"Error parsing individual listing: {e}")
                continue
        
        return jobs
    
    def extract_contacts(self, text):
        """Extract email and phone numbers from text"""
        contacts = {'email': 'Not found', 'whatsapp': 'Not found'}
        
        # Extract email - more robust pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            contacts['email'] = emails[0]
        
        # Extract phone numbers - international format support
        phone_patterns = [
            r'\+?\d[\d\s\-\(\)]{8,}\d',  # General international
            r'05\d[\d\s\-]{7,}\d',  # Saudi mobile numbers (05XXXXXXXX)
            r'01\d[\d\s\-]{7,}\d',  # Saudi landline
        ]
        
        all_phones = []
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            all_phones.extend(phones)
        
        # Look for WhatsApp specifically
        whatsapp_keywords = ['whatsapp', 'wa.', 'wa ', 'whats app']
        for keyword in whatsapp_keywords:
            if keyword.lower() in text.lower():
                # Find phone near the keyword
                keyword_idx = text.lower().find(keyword)
                if keyword_idx != -1:
                    # Look for phone in next 50 characters
                    search_text = text[keyword_idx:keyword_idx + 100]
                    for pattern in phone_patterns:
                        match = re.search(pattern, search_text)
                        if match:
                            contacts['whatsapp'] = match.group(0).strip()
                            break
                break
        
        # If no WhatsApp found but phones exist, use first phone
        if contacts['whatsapp'] == 'Not found' and all_phones:
            contacts['whatsapp'] = all_phones[0].strip()
        
        return contacts
    
    async def scrape_jobs(self):
        """Main scraping function with error handling"""
        try:
            logger.info(f"Starting scrape of {self.saudi_url}")
            html = await self.fetch_page(self.saudi_url)
            
            if html:
                jobs = self.parse_job_listings(html)
                logger.info(f"Successfully parsed {len(jobs)} jobs")
                return jobs
            else:
                logger.error("Failed to get HTML content")
                return []
                
        except Exception as e:
            logger.error(f"Error in scrape_jobs: {e}")
            return []
