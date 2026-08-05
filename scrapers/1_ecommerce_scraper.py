# scrapers/1_ecommerce_scraper.py
import time
import csv
import json
import os
from datetime import datetime
import random
from urllib.parse import urljoin
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class EcommerceScraper:
    def __init__(self):
        self.base_url = "https://www.redbubble.com"
        self.search_path = "/shop/iphone-17-cases"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.products = []
        self.playwright = None
        self.browser = None
        self.page = None
        
    def get_full_url(self, path):
        """Construct full URL from base URL and path"""
        return urljoin(self.base_url, path)
    
    def setup_browser(self):
        """Setup Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,  # Run in headless mode for GitHub Actions
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        )
        self.page = self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page.set_default_timeout(30000)  # 30 second timeout
        
    def close_browser(self):
        """Close browser and playwright"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_title(self, card):
        """Extract product title using multiple methods"""
        try:
            # Method 1: Using data-testid
            title_elem = card.query_selector('span[data-testid="ds-box"]')
            if title_elem:
                title = title_elem.inner_text().strip()
                if title:
                    return title
        except:
            pass
            
        try:
            # Method 2: Using class containing 'SearchResultCard_title'
            title_elem = card.query_selector('span[class*="SearchResultCard_title"]')
            if title_elem:
                title = title_elem.inner_text().strip()
                if title:
                    return title
        except:
            pass
            
        try:
            # Method 3: Find all spans and look for the one with longest text
            spans = card.query_selector_all('span')
            for span in spans:
                text = span.inner_text().strip()
                if len(text) > 15 and '$' not in text and '★' not in text:
                    # Check if it's in a link
                    parent_link = span.query_selector('xpath=./ancestor::a')
                    if parent_link:
                        return text
        except:
            pass
            
        try:
            # Method 4: Get image alt text
            img = card.query_selector('img')
            if img:
                alt_text = img.get_attribute('alt')
                if alt_text and len(alt_text.strip()) > 10:
                    return alt_text.strip()
        except:
            pass
            
        try:
            # Method 5: Get link text
            link = card.query_selector('a')
            if link:
                text = link.inner_text().strip()
                if len(text) > 10:
                    return text
        except:
            pass
            
        return "N/A"
    
    def extract_price(self, card):
        """Extract product price"""
        try:
            # Method 1: Using data-testid
            price_elem = card.query_selector('span[data-testid="line-item-price-price"]')
            if price_elem:
                price = price_elem.inner_text().strip()
                if price:
                    return price
        except:
            pass
            
        try:
            # Method 2: Using class containing 'Price'
            price_elem = card.query_selector('span[class*="Price"]')
            if price_elem:
                price = price_elem.inner_text().strip()
                if price:
                    return price
        except:
            pass
            
        try:
            # Method 3: Look for price pattern in card text
            card_text = card.inner_text()
            price_pattern = re.search(r'\$\d+\.?\d*', card_text)
            if price_pattern:
                return price_pattern.group()
        except:
            pass
            
        return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of products"""
        try:
            print(f"Fetching URL: {url}")
            
            # Navigate to the page
            self.page.goto(url, wait_until='networkidle')
            
            # Wait for products to load - try multiple selectors
            try:
                self.page.wait_for_selector('div[data-testid="search-result-card"]', timeout=15000)
            except PlaywrightTimeoutError:
                print("Timeout waiting for product cards. Checking for alternative selectors...")
                # Try alternative selector
                try:
                    self.page.wait_for_selector('div[class*="SearchResultCard"]', timeout=10000)
                except PlaywrightTimeoutError:
                    print("No products found on this page")
                    return None
            
            # Scroll down to load more products
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Scroll back up slightly to ensure all elements are loaded
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            time.sleep(1)
            
            # Find all product cards - try multiple selectors
            product_cards = self.page.query_selector_all('div[data-testid="search-result-card"]')
            
            if not product_cards:
                # Try alternative selector
                product_cards = self.page.query_selector_all('div[class*="SearchResultCard"]')
            
            print(f"Found {len(product_cards)} product cards on this page")
            
            for index, card in enumerate(product_cards):
                try:
                    # Extract data
                    title = self.extract_title(card)
                    price = self.extract_price(card)
                    
                    # Extract rating
                    rating = "N/A"
                    try:
                        rating_elem = card.query_selector('span[data-testid="rating-stars"]')
                        if rating_elem:
                            rating = rating_elem.get_attribute('aria-label') or "N/A"
                    except:
                        pass
                    
                    # Extract stock status
                    stock = "In Stock"
                    try:
                        stock_elem = card.query_selector('span[data-testid="stock-status"]')
                        if stock_elem:
                            stock = stock_elem.inner_text().strip()
                        else:
                            # Check for out of stock indicators in card text
                            card_text = card.inner_text().lower()
                            if 'out of stock' in card_text or 'sold out' in card_text:
                                stock = "Out of Stock"
                    except:
                        pass
                    
                    # Extract product URL
                    product_url = "N/A"
                    try:
                        link = card.query_selector('a')
                        if link:
                            href = link.get_attribute('href')
                            if href:
                                product_url = self.get_full_url(href)
                    except:
                        pass
                    
                    print(f"Product {index + 1}: {title[:50]}... - {price}")
                    
                    if title != "N/A":
                        self.products.append({
                            'product_name': title,
                            'price': price,
                            'rating': rating,
                            'stock_status': stock,
                            'product_url': product_url,
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        print(f"  ⚠️ Skipping product {index + 1} - no title found")
                    
                except Exception as e:
                    print(f"Error parsing product card {index}: {e}")
                    continue
            
            # Check for next page
            try:
                next_button = self.page.query_selector('a[data-testid="pagination-next"]')
                if next_button:
                    next_url = next_button.get_attribute('href')
                    if next_url:
                        full_next_url = self.get_full_url(next_url)
                        print(f"Next page found: {full_next_url}")
                        return full_next_url
            except:
                pass
                
            # Try alternative pagination selector
            try:
                next_links = self.page.query_selector_all('a:has-text("Next")')
                for link in next_links:
                    if link.get_attribute('href'):
                        full_next_url = self.get_full_url(link.get_attribute('href'))
                        print(f"Next page found (alternative): {full_next_url}")
                        return full_next_url
            except:
                pass
                
            print("No more pages found")
            return None
            
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=3):
        """Scrape multiple pages"""
        self.setup_browser()
        
        try:
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
            
        finally:
            self.close_browser()
        
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
    print("E-COMMERCE PRODUCT SCRAPER (Playwright)")
    print("="*60)
    
    scraper = EcommerceScraper()
    products = scraper.scrape(max_pages=2)
    scraper.save_results(products)
