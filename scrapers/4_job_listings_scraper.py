# scrapers/4_job_listings_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random
from urllib.parse import urljoin
import re

class JobListingsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.base_url = "https://www.daybook.com"
        self.search_path = "/jobs/in/washington-dc"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.jobs = []
        # Fixed filenames (no timestamps)
        self.csv_filename = "output/job_listings.csv"
        self.json_filename = "output/job_listings.json"
        
    def get_full_url(self, path):
        """Construct full URL from base URL and path"""
        if not path:
            return None
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return f"https:{path}"
        return urljoin(self.base_url, path)
    
    def extract_job_title(self, card):
        """Extract job title"""
        try:
            # Method 1: Look for h3 with job title
            title_elem = card.find('h3', class_=lambda c: c and 'text-base' in c if c else False)
            if title_elem:
                return title_elem.text.strip()
        except:
            pass
            
        try:
            # Method 2: Look for any h3
            title_elem = card.find('h3')
            if title_elem and title_elem.text.strip():
                return title_elem.text.strip()
        except:
            pass
            
        try:
            # Method 3: Look for any heading with job-like text
            for tag in ['h2', 'h3', 'h4']:
                elem = card.find(tag)
                if elem and len(elem.text.strip()) > 5:
                    return elem.text.strip()
        except:
            pass
            
        return "N/A"
    
    def extract_company(self, card):
        """Extract company name"""
        try:
            # Method 1: Look for span with company class
            company_elem = card.find('span', class_=lambda c: c and 'font-medium' in c if c else False)
            if company_elem:
                return company_elem.text.strip()
        except:
            pass
            
        try:
            # Method 2: Look for any span with company-like text
            spans = card.find_all('span')
            for span in spans:
                text = span.text.strip()
                if len(text) > 2 and not any(x in text for x in ['$', 'New', 'Posted']):
                    # Check if it looks like a company name
                    if text[0].isupper() or ' ' in text:
                        return text
        except:
            pass
            
        return "N/A"
    
    def extract_location(self, card):
        """Extract job location"""
        try:
            # Method 1: Look for span with location
            location_elem = card.find('span', string=lambda x: x and ('Washington' in str(x) or 'DC' in str(x)) if x else False)
            if location_elem:
                return location_elem.text.strip()
        except:
            pass
            
        try:
            # Method 2: Look for any span with location pattern
            spans = card.find_all('span')
            for span in spans:
                text = span.text.strip()
                if len(text) > 5 and any(x in text for x in ['Washington', 'DC', 'USA', 'Remote']):
                    return text
        except:
            pass
            
        try:
            # Method 3: Look for location in any text
            card_text = card.text
            location_patterns = [
                r'Washington,?\s*DC',
                r'[A-Z][a-z]+,\s*[A-Z]{2}',
                r'[A-Z][a-z]+,\s*[A-Z][a-z]+\s*,\s*USA'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, card_text)
                if match:
                    return match.group()
        except:
            pass
            
        return "N/A"
    
    def extract_salary(self, card):
        """Extract salary if listed"""
        try:
            # Look for any text with $ sign
            card_text = card.text
            salary_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:-\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?)?'
            match = re.search(salary_pattern, card_text)
            if match:
                return match.group()
        except:
            pass
        return "Not Listed"
    
    def extract_posted_time(self, card):
        """Extract posted time"""
        try:
            # Method 1: Look for time tag
            time_elem = card.find('time')
            if time_elem:
                return time_elem.text.strip()
        except:
            pass
            
        try:
            # Method 2: Look for any text with time pattern
            card_text = card.text
            time_patterns = [
                r'\d+\s+(hours?|days?|minutes?)\s+ago',
                r'Just\s+now',
                r'Today',
                r'Yesterday'
            ]
            for pattern in time_patterns:
                match = re.search(pattern, card_text, re.IGNORECASE)
                if match:
                    return match.group()
        except:
            pass
            
        return "N/A"
    
    def extract_job_url(self, card):
        """Extract job URL"""
        try:
            # Method 1: Look for link in card
            link = card.find('a')
            if link and link.get('href'):
                return self.get_full_url(link.get('href'))
        except:
            pass
            
        try:
            # Method 2: Look for any link with /job/
            links = card.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and '/job/' in href:
                    return self.get_full_url(href)
        except:
            pass
            
        return None
    
    def scrape_page(self, url):
        """Scrape a single page of job listings"""
        try:
            print(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for job cards
            job_cards = []
            
            # Method 1: Look for job links with group class
            cards = soup.find_all('a', class_=lambda c: c and 'group block' in c if c else False)
            if cards:
                job_cards = cards
                print(f"Found {len(job_cards)} jobs with 'group block' class")
            
            # Method 2: Look for any link containing /job/
            if not job_cards:
                cards = soup.find_all('a', href=lambda x: x and '/job/' in x if x else False)
                if cards:
                    job_cards = cards
                    print(f"Found {len(job_cards)} jobs with /job/ in href")
            
            # Method 3: Look for job listings in divs
            if not job_cards:
                cards = soup.find_all('div', class_=lambda c: c and ('job' in c.lower() or 'listing' in c.lower()) if c else False)
                if cards:
                    job_cards = cards
                    print(f"Found {len(job_cards)} jobs with job/listing class")
            
            # Method 4: Look for any link with job-like text
            if not job_cards:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    text = link.text.strip()
                    if href and '/job/' in href and len(text) > 5:
                        job_cards.append(link)
                if job_cards:
                    print(f"Found {len(job_cards)} jobs from links")
            
            if not job_cards:
                print("No job cards found on this page")
                # Debug: show page structure
                print("Page title:", soup.title.string if soup.title else "No title")
                # Show first few links
                links = soup.find_all('a', href=True)[:5]
                for link in links:
                    print(f"  Link: {link.get('href')} - {link.text.strip()[:50]}")
                return None
            
            print(f"Processing {len(job_cards)} jobs...")
            
            for index, card in enumerate(job_cards):
                try:
                    # Extract data from card
                    job_title = self.extract_job_title(card)
                    company = self.extract_company(card)
                    location = self.extract_location(card)
                    salary = self.extract_salary(card)
                    posted_time = self.extract_posted_time(card)
                    job_url = self.extract_job_url(card)
                    
                    # Check if it's a new job
                    is_new = False
                    new_elem = card.find('span', class_=lambda c: c and ('green' in str(c) or 'new' in str(c).lower()) if c else False)
                    if new_elem:
                        is_new = True
                    
                    print(f"Job {index + 1}: {job_title[:40]}... - {company}")
                    
                    self.jobs.append({
                        'job_title': job_title,
                        'company': company,
                        'location': location,
                        'salary': salary,
                        'posted_time': posted_time,
                        'is_new': is_new,
                        'job_url': job_url,
                        'scraped_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing job {index}: {e}")
                    continue
            
            # Check for pagination
            next_url = None
            
            # Method 1: Look for Next button
            next_link = soup.find('a', string=lambda x: x and 'Next' in str(x) if x else False)
            if next_link and next_link.get('href'):
                next_url = self.get_full_url(next_link.get('href'))
            
            # Method 2: Look for recirculation link
            if not next_url:
                next_link = soup.find('a', {'data-event': 'recirculation'})
                if next_link and next_link.get('href'):
                    next_url = self.get_full_url(next_link.get('href'))
            
            # Method 3: Look for any link with page parameter
            if not next_url:
                links = soup.find_all('a', href=lambda x: x and 'page=' in x if x else False)
                for link in links:
                    href = link.get('href')
                    if href and 'page=' in href:
                        # Check if it's the next page
                        page_match = re.search(r'page=(\d+)', href)
                        if page_match:
                            page_num = int(page_match.group(1))
                            if page_num > 1:
                                next_url = self.get_full_url(href)
                                break
            
            if next_url:
                print(f"Next page found: {next_url}")
                return next_url
            else:
                print("No more pages found")
                return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=3):
        """Scrape multiple pages"""
        current_url = self.full_search_url
        page_num = 1
        
        print(f"\n{'='*60}")
        print(f"STARTING JOB LISTINGS SCRAPER")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Search path: {self.search_path}")
        print(f"Full URL: {self.full_search_url}")
        print(f"Max pages: {max_pages}")
        print(f"{'='*60}\n")
        
        while current_url and page_num <= max_pages:
            print(f"{'='*60}")
            print(f"SCRAPING PAGE {page_num}")
            print(f"{'='*60}")
            
            next_url = self.scrape_page(current_url)
            
            if next_url:
                current_url = next_url
            else:
                break
                
            page_num += 1
            print(f"Total jobs scraped so far: {len(self.jobs)}")
            
            delay = random.uniform(2, 4)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total jobs scraped: {len(self.jobs)}")
        print(f"{'='*60}")
        
        return self.jobs
    
    def save_results(self, jobs):
        """Save results to CSV and JSON - OVERWRITES existing files"""
        if not jobs:
            print("No jobs to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        fieldnames = ['job_title', 'company', 'location', 'salary', 'posted_time', 'is_new', 'job_url', 'scraped_at']
        
        # Save as CSV - OVERWRITE
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(jobs)
            print(f"\n✓ CSV saved (overwritten): {self.csv_filename}")
            print(f"  Total records: {len(jobs)}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON - OVERWRITE
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2, ensure_ascii=False)
            print(f"✓ JSON saved (overwritten): {self.json_filename}")
            print(f"  Total records: {len(jobs)}")
        except Exception as e:
            print(f"✗ Error saving JSON: {e}")
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total jobs: {len(jobs)}")
        print(f"CSV file: {self.csv_filename}")
        print(f"JSON file: {self.json_filename}")
        
        # Show first 5 jobs as preview
        print(f"\n{'='*60}")
        print("SAMPLE JOBS (first 5)")
        print(f"{'='*60}")
        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job['job_title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   Salary: {job['salary']}")
            print(f"   Posted: {job['posted_time']}")
            print("-" * 40)

if __name__ == "__main__":
    print("="*60)
    print("JOB LISTINGS SCRAPER")
    print("="*60)
    
    scraper = JobListingsScraper()
    jobs = scraper.scrape(max_pages=2)
    scraper.save_results(jobs)
