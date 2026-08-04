# scrapers/3_business_directory_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random

class BusinessDirectoryScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.yellowpages.com/los-angeles-ca/general-contractors"
        self.businesses = []
        
    def scrape_listing_details(self, listing_url):
        """Scrape detailed information from a business listing page"""
        try:
            response = requests.get(listing_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract business name
            name_elem = soup.find('h1', class_='dockable')
            name = name_elem.text.strip() if name_elem else "N/A"
            
            # Extract phone
            phone_elem = soup.find('a', {'data-analytics': lambda x: x and 'phone-no' in x if x else False})
            phone = phone_elem.text.strip() if phone_elem else "N/A"
            
            # Extract email (if publicly listed)
            email_elem = soup.find('a', {'href': lambda x: x and x.startswith('mailto:') if x else False})
            email = email_elem.get('href', '').replace('mailto:', '') if email_elem else "N/A"
            
            # Extract website
            website_elem = soup.find('a', {'href': lambda x: x and 'website' in str(x) if x else False})
            website = website_elem.get('href') if website_elem else "N/A"
            
            # Extract industry/profession
            industry_elem = soup.find('a', {'href': lambda x: x and 'bathroom-remodeling' in x if x else False})
            industry = industry_elem.text.strip() if industry_elem else "N/A"
            
            return {
                'business_name': name,
                'phone': phone,
                'email': email,
                'website': website,
                'industry': industry,
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            print(f"Error scraping listing details: {e}")
            return None
    
    def scrape_page(self, url):
        """Scrape a single page of business listings"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            listing_cards = soup.find_all('div', class_='srp-listing')
            
            for card in listing_cards:
                try:
                    # Get the listing URL
                    link_elem = card.find('a', {'data-analytics': lambda x: x and 'listing_id' in str(x) if x else False})
                    if link_elem and link_elem.get('href'):
                        listing_url = link_elem['href']
                        if not listing_url.startswith('http'):
                            listing_url = f"https://www.yellowpages.com{listing_url}"
                        
                        # Scrape detailed information
                        details = self.scrape_listing_details(listing_url)
                        if details:
                            self.businesses.append(details)
                        
                        time.sleep(random.uniform(2, 4))  # Be respectful
                    
                except Exception as e:
                    print(f"Error parsing business card: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('a', {'data-page': lambda x: x and int(x) > 1 if x else False})
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
                    current_url = f"https://www.yellowpages.com{next_url}"
                else:
                    current_url = next_url
            else:
                break
                
            page_num += 1
            time.sleep(random.uniform(3, 5))
        
        return self.businesses
    
    def save_results(self, businesses):
        """Save results to CSV and JSON"""
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/business_directory_{timestamp}.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['business_name', 'phone', 'email', 'website', 'industry', 'timestamp'])
            writer.writeheader()
            writer.writerows(businesses)
        
        # Save as JSON
        json_file = f'output/business_directory_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(businesses)} businesses to {csv_file} and {json_file}")

if __name__ == "__main__":
    scraper = BusinessDirectoryScraper()
    businesses = scraper.scrape(max_pages=3)
    scraper.save_results(businesses)
