# scrapers/2_real_estate_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random

class RealEstateScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.realestate.com.au/international/us/mn/"
        self.listings = []
        
    def scrape_page(self, url):
        """Scrape a single page of real estate listings"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            listing_cards = soup.find_all('div', {'data-testid': 'standard-listing-card'})
            
            for card in listing_cards:
                try:
                    # Extract price in AUD
                    price_aud_elem = card.find('div', class_='displayConsumerPrice')
                    price_aud = price_aud_elem.text.strip() if price_aud_elem else "N/A"
                    
                    # Extract price in USD
                    price_usd_elem = card.find('div', class_='displayConsumerPrice')
                    price_usd = price_usd_elem.text.strip() if price_usd_elem else "N/A"
                    
                    # Extract address
                    address_elem = card.find('div', class_='address')
                    address = address_elem.text.strip() if address_elem else "N/A"
                    
                    # Extract bedrooms
                    bedroom_elem = card.find('img', {'alt': 'bedrooms'})
                    bedroom = bedroom_elem.parent.text.strip() if bedroom_elem and bedroom_elem.parent else "N/A"
                    
                    # Extract bathrooms
                    bathroom_elem = card.find('img', {'alt': 'bathroom'})
                    bathroom = bathroom_elem.parent.text.strip() if bathroom_elem and bathroom_elem.parent else "N/A"
                    
                    self.listings.append({
                        'address': address,
                        'price_aud': price_aud,
                        'price_usd': price_usd,
                        'bedrooms': bedroom,
                        'bathrooms': bathroom,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing listing card: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('li', class_='ant-pagination-next')
            if next_button and 'aria-disabled' not in next_button.attrs:
                next_link = next_button.find('a')
                return next_link.get('href') if next_link else None
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
                    current_url = f"https://www.realestate.com.au{next_url}"
                else:
                    current_url = next_url
            else:
                break
                
            page_num += 1
            time.sleep(random.uniform(3, 5))
        
        return self.listings
    
    def save_results(self, listings):
        """Save results to CSV and JSON"""
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/real_estate_listings_{timestamp}.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'price_aud', 'price_usd', 'bedrooms', 'bathrooms', 'timestamp'])
            writer.writeheader()
            writer.writerows(listings)
        
        # Save as JSON
        json_file = f'output/real_estate_listings_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(listings)} listings to {csv_file} and {json_file}")

if __name__ == "__main__":
    scraper = RealEstateScraper()
    listings = scraper.scrape(max_pages=3)
    scraper.save_results(listings)
