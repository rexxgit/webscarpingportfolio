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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
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
            
            print(f"Found {len(product_cards)} product cards on this page")
            
            for index, card in enumerate(product_cards):
                try:
                    # Method 1: Try to find title using multiple possible selectors
                    title = "N/A"
                    
                    # Try data-testid first (most reliable)
                    title_elem = card.find('span', {'data-testid': 'ds-box'})
                    if title_elem:
                        title = title_elem.text.strip()
                    else:
                        # Fallback: try to find any span with product title
                        # Look for span that might contain the title
                        title_spans = card.find_all('span', class_=lambda c: c and 'SearchResultCard_title' in c if c else False)
                        if title_spans:
                            title = title_spans[0].text.strip()
                        else:
                            # Another fallback: look for any heading or span with text
                            potential_titles = card.find_all(['h3', 'span', 'div'], 
                                                           class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower()) if c else False)
                            if potential_titles:
                                title = potential_titles[0].text.strip()
                            else:
                                # Last resort: get text from the card's link or container
                                link = card.find('a')
                                if link and link.text.strip():
                                    title = link.text.strip()
                    
                    # Extract price - try multiple selectors
                    price = "N/A"
                    price_elem = card.find('span', {'data-testid': 'line-item-price-price'})
                    if price_elem:
                        price = price_elem.text.strip()
                    else:
                        # Fallback: look for any price-like element
                        price_spans = card.find_all('span', class_=lambda c: c and 'Price' in c if c else False)
                        if price_spans:
                            price = price_spans[0].text.strip()
                    
                    # Extract rating if available
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
                    
                    # Debug output
                    print(f"Product {index + 1}: {title[:50]}... - {price}")
                    
                    self.products.append({
                        'product_name': title,
                        'price': price,
                        'rating': rating,
                        'stock_status': stock,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing product card {index}: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('a', {'data-testid': 'pagination-next'})
            if next_button and next_button.get('href'):
                print(f"Next page found: {next_button.get('href')}")
                return next_button.get('href')
            else:
                print("No more pages found")
                return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=3):
        """Scrape multiple pages"""
        current_url = self.base_url
        page_num = 1
        total_products = 0
        
        while current_url and page_num <= max_pages:
            print(f"\n{'='*50}")
            print(f"Scraping page {page_num}...")
            print(f"URL: {current_url}")
            print(f"{'='*50}")
            
            next_url = self.scrape_page(current_url)
            
            if next_url:
                # Ensure URL is absolute
                if next_url.startswith('/'):
                    current_url = f"https://www.redbubble.com{next_url}"
                else:
                    current_url = next_url
            else:
                break
                
            page_num += 1
            total_products = len(self.products)
            print(f"Total products scraped so far: {total_products}")
            
            # Random delay to be respectful
            delay = random.uniform(2, 5)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
        
        print(f"\n{'='*50}")
        print(f"Scraping complete! Total products: {len(self.products)}")
        print(f"{'='*50}")
        
        return self.products
    
    def save_results(self, products):
        """Save results to CSV and JSON"""
        if not products:
            print("No products to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/ecommerce_products_{timestamp}.csv'
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['product_name', 'price', 'rating', 'stock_status', 'timestamp'])
                writer.writeheader()
                writer.writerows(products)
            print(f"✓ CSV saved: {csv_file}")
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
        print(f"\n{'='*50}")
        print(f"SUMMARY")
        print(f"{'='*50}")
        print(f"Total products: {len(products)}")
        print(f"CSV file: {csv_file}")
        print(f"JSON file: {json_file}")
        print(f"{'='*50}")
        
        # Show first 5 products as preview
        print("\nSample products:")
        for i, product in enumerate(products[:5], 1):
            print(f"{i}. {product['product_name'][:60]}... - {product['price']}")

if __name__ == "__main__":
    print("Starting E-commerce Product Scraper")
    print(f"Target: {EcommerceScraper.base_url}")
    print("="*50)
    
    scraper = EcommerceScraper()
    products = scraper.scrape(max_pages=2)  # Reduced to 2 pages for testing
    scraper.save_results(products)
