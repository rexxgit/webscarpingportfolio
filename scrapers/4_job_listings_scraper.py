# scrapers/4_job_listings_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random

class JobListingsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.daybook.com/jobs/in/washington-dc"
        self.jobs = []
        
    def scrape_page(self, url):
        """Scrape a single page of job listings"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_links = soup.find_all('a', class_='group block')
            
            for link in job_links:
                try:
                    # Get job URL
                    job_url = link.get('href')
                    if job_url and not job_url.startswith('http'):
                        job_url = f"https://www.daybook.com{job_url}"
                    
                    # Extract job title
                    title_elem = link.find('h3', class_='text-base')
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    # Extract company name
                    company_elem = link.find('span', class_='font-medium')
                    company = company_elem.text.strip() if company_elem else "N/A"
                    
                    # Extract location
                    location_elem = link.find('span', string=lambda x: x and 'Washington' in x if x else False)
                    location = location_elem.text.strip() if location_elem else "N/A"
                    
                    # Extract posted time
                    time_elem = link.find('time')
                    posted_time = time_elem.text.strip() if time_elem else "N/A"
                    
                    # Extract salary if listed
                    salary_elem = link.find('span', string=lambda x: x and '$' in x if x else False)
                    salary = salary_elem.text.strip() if salary_elem else "Not Listed"
                    
                    # Check if new
                    new_elem = link.find('span', class_='bg-gradient-to-r')
                    is_new = bool(new_elem)
                    
                    self.jobs.append({
                        'job_title': title,
                        'company': company,
                        'location': location,
                        'salary': salary,
                        'posted_time': posted_time,
                        'is_new': is_new,
                        'job_url': job_url,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing job listing: {e}")
                    continue
            
            # Check for pagination
            next_button = soup.find('a', {'data-event': 'recirculation'})
            if next_button and next_button.get('href'):
                return next_button['href']
            return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=5):
        """Scrape multiple pages"""
        current_url = self.base_url
        page_num = 1
        
        while current_url and page_num <= max_pages:
            print(f"Scraping page {page_num}...")
            next_url = self.scrape_page(current_url)
            
            if next_url:
                if not next_url.startswith('http'):
                    current_url = f"https://www.daybook.com{next_url}"
                else:
                    current_url = next_url
            else:
                break
                
            page_num += 1
            time.sleep(random.uniform(2, 4))
        
        return self.jobs
    
    def save_results(self, jobs):
        """Save results to CSV and JSON"""
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/job_listings_{timestamp}.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['job_title', 'company', 'location', 'salary', 'posted_time', 'is_new', 'job_url', 'timestamp'])
            writer.writeheader()
            writer.writerows(jobs)
        
        # Save as JSON
        json_file = f'output/job_listings_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(jobs)} jobs to {csv_file} and {json_file}")

if __name__ == "__main__":
    scraper = JobListingsScraper()
    jobs = scraper.scrape(max_pages=3)
    scraper.save_results(jobs)
