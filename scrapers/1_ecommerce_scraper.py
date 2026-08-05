# scrapers/1_ecommerce_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random
from urllib.parse import urljoin

class EcommerceScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.base_url = "https://www.redbubble.com"
        self.search_path = "/shop/iphone-17-cases"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.products = []
        
    def get_full_url(self, path):
        """Construct full URL from base URL and path"""
        return urljoin(self.base_url, path)
    
    def extract_title(self, card):
        """Extract product title using multiple methods"""
        # Method 1: Using data-testid (most reliable)
        title_elem = card.find('span', {'data-testid': 'ds-box'})
        if title_elem:
            return title_elem.text.strip()
        
        # Method 2: Using class that contains 'SearchResultCard_title'
        title_elem = card.find('span', class_=lambda c: c and 'SearchResultCard_title' in c if c else False)
        if title_elem:
            return title_elem.text.strip()
        
        # Method 3: Looking for any span with class containing 'title'
        title_elem = card.find('span', class_=lambda c: c and 'title' in c.lower() if c else False)
        if title_elem:
            return title_elem.text.strip()
        
        # Method 4: Looking for any heading element
        title_elem = card.find(['h1', 'h2', 'h3', 'h4'])
        if title_elem:
            return title_elem.text.strip()
        
        # Method 5: Get text from link (fallback)
        link = card.find('a')
        if link and link.text.strip():
            return link.text.strip()
        
        return "N/A"
    
    def extract_price(self, card):
        """Extract product price using multiple methods"""
        # Method 1: Using data-testid
        price_elem = card.find('span', {'data-testid': 'line-item-price-price'})
        if price_elem:
            return price_elem.text.strip()
        
        # Method 2: Looking for price in class containing 'Price'
        price_elem = card.find('span', class_=lambda c: c and 'Price' in c if c else False)
        if price_elem:
            return price_elem.text.strip()
        
        # Method 3: Looking for any element with $ sign
        elements_with_dollar = card.find_all(string=lambda t: t and '$' in t if t else False)
        for elem in elements_with_dollar:
            if elem.strip():
                return elem.strip()
        
        return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of products"""
        try:
            print(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple ways to find product cards
            product_cards = []
            
            # Method 1: Using data-testid
            product_cards = soup.find_all('div', {'data-testid': 'search-result-card'})
            
            # Method 2: If no cards found, try looking for product containers
            if not product_cards:
                product_cards = soup.find_all('div', class_=lambda c: c and 'SearchResultCard' in c if c else False)
            
            print(f"Found {len(product_cards)} product cards on this page")
            
            for index, card in enumerate(product_cards):
                try:
                    # Extract title using the specialized method
                    title = self.extract_title(card)
                    
                    # Extract price using the specialized method
                    price = self.extract_price(card)
                    
                    # Extract rating (if available)
                    rating = "N/A"
                    rating_elem = card.find('span', {'data-testid': 'rating-stars'})
                    if rating_elem:
                        rating = rating_elem.get('aria-label', 'N/A')
                    else:
                        # Try to find rating via other selectors
                        rating_spans = card.find_all('span', class_=lambda c: c and ('rating' in c.lower() or 'star' in c.lower()) if c else False)
                        if rating_spans:
                            rating = rating_spans[0].text.strip()
                    
                    # Extract stock status
                    stock = "In Stock"
                    stock_elem = card.find('span', {'data-testid': 'stock-status'})
                    if stock_elem:
                        stock = stock_elem.text.strip()
                    else:
                        # Check for out of stock indicators
                        out_of_stock = card.find(text=lambda t: t and ('out of stock' in t.lower() or 'sold out' in t.lower()) if t else False)
                        if out_of_stock:
                            stock = "Out of Stock"
                    
                    # Extract product URL for reference
                    product_url = "N/A"
                    link = card.find('a')
                    if link and link.get('href'):
                        product_url = self.get_full_url(link.get('href'))
                    
                    # Debug output - show what we found
                    print(f"Product {index + 1}: {title[:50]}... - {price}")
                    
                    self.products.append({
                        'product_name': title,
                        'price': price,
                        'rating': rating,
                        'stock_status': stock,
                        'product_url': product_url,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing product card {index}: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('a', {'data-testid': 'pagination-next'})
            if next_button and next_button.get('href'):
                next_url = next_button.get('href')
                # Use get_full_url to construct absolute URL
                full_next_url = self.get_full_url(next_url)
                print(f"Next page found: {full_next_url}")
                return full_next_url
            else:
                # Try alternative pagination selector
                next_links = soup.find_all('a', string=lambda t: t and ('next' in t.lower() or 'Next' in t) if t else False)
                for link in next_links:
                    if link.get('href'):
                        full_next_url = self.get_full_url(link.get('href'))
                        print(f"Next page found (alternative): {full_next_url}")
                        return full_next_url
                
                print("No more pages found")
                return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def scrape(self, max_pages=3):
        """Scrape multiple pages"""
        current_url = self.full_search_url
        page_num = 1
        
        print(f"\n{'='*60}")
        print(f"STARTING SCRAPER")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Search path: {self.search_path}")
        print(f"Full URL: {self.full_search_url}")
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
            print(f"Total products scraped so far: {len(self.products)}")
            
            # Random delay to be respectful
            delay = random.uniform(2, 4)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total products scraped: {len(self.products)}")
        print(f"{'='*60}")
        
        return self.products
    
    def save_results(self, products):
        """Save results to CSV and JSON"""
        if not products:
            print("No products to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Define field names for CSV
        fieldnames = ['product_name', 'price', 'rating', 'stock_status', 'product_url', 'timestamp']
        
        # Save as CSV
        csv_file = f'output/ecommerce_products_{timestamp}.csv'
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(products)
            print(f"\n✓ CSV saved: {csv_file}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON
        json_file = f'output/ecommerce_products_{timestamp}.json'
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            print(f"✓ JSON saved: {json_file}")
        except Exception as e:
            print(f"✗ Error saving JSON: {e}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total products: {len(products)}")
        print(f"CSV file: {csv_file}")
        print(f"JSON file: {json_file}")
        
        # Show first 5 products as preview
        print(f"\n{'='*60}")
        print("SAMPLE PRODUCTS (first 5)")
        print(f"{'='*60}")
        for i, product in enumerate(products[:5], 1):
            print(f"{i}. {product['product_name']}")
            print(f"   Price: {product['price']}")
            print(f"   Rating: {product['rating']}")
            print(f"   Stock: {product['stock_status']}")
            if product.get('product_url'):
                print(f"   URL: {product['product_url'][:60]}...")
            print("-" * 40)

if __name__ == "__main__":
    print("="*60)
    print("E-COMMERCE PRODUCT SCRAPER")
    print("="*60)
    
    scraper = EcommerceScraper()
    products = scraper.scrape(max_pages=2)
    scraper.save_results(products)
