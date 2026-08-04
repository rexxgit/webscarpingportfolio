# scrapers/1_ecommerce_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random

class EcommerceScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.redbubble.com/shop/iphone-17-cases"
        self.products = []
        
    def scrape_page(self, url):
        """Scrape a single page of products"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            product_cards = soup.find_all('div', {'data-testid': 'search-result-card'})
            
            for card in product_cards:
                try:
                    # Extract product name
                    title_elem = card.find('span', {'data-testid': 'ds-box'})
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    # Extract price
                    price_elem = card.find('span', {'data-testid': 'line-item-price-price'})
                    price = price_elem.text.strip() if price_elem else "N/A"
                    
                    # Extract rating (if available)
                    rating_elem = card.find('span', {'data-testid': 'rating-stars'})
                    rating = rating_elem.get('aria-label', 'N/A') if rating_elem else "N/A"
                    
                    # Extract stock status (if available)
                    stock_elem = card.find('span', {'data-testid': 'stock-status'})
                    stock = stock_elem.text.strip() if stock_elem else "In Stock"
                    
                    self.products.append({
                        'product_name': title,
                        'price': price,
                        'rating': rating,
                        'stock_status': stock,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing product card: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('a', {'data-testid': 'pagination-next'})
            return next_button.get('href') if next_button else None
            
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
                current_url = next_url
            else:
                break
                
            page_num += 1
            time.sleep(random.uniform(2, 4))  # Be respectful to the server
        
        return self.products
    
    def save_results(self, products):
        """Save results to CSV and JSON"""
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/ecommerce_products_{timestamp}.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['product_name', 'price', 'rating', 'stock_status', 'timestamp'])
            writer.writeheader()
            writer.writerows(products)
        
        # Save as JSON
        json_file = f'output/ecommerce_products_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(products)} products to {csv_file} and {json_file}")

if __name__ == "__main__":
    scraper = EcommerceScraper()
    products = scraper.scrape(max_pages=3)
    scraper.save_results(products)
