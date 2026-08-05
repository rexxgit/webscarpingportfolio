# scrapers/5_news_scraper.py
import time
import csv
import json
import os
from datetime import datetime
import random
from urllib.parse import urljoin
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class NewsScraper:
    def __init__(self):
        self.base_url = "https://techcrunch.com"
        self.search_path = "/category/artificial-intelligence/"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.articles = []
        self.playwright = None
        self.browser = None
        self.page = None
        # Fixed filenames (no timestamps)
        self.csv_filename = "output/news_articles.csv"
        self.json_filename = "output/news_articles.json"
        
    def get_full_url(self, path):
        """Construct full URL from base URL and path"""
        if not path:
            return None
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return f"https:{path}"
        return urljoin(self.base_url, path)
    
    def find_chromium_path(self):
        """Find system Chromium installation"""
        possible_paths = [
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/snap/bin/chromium',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found Chromium at: {path}")
                return path
        
        try:
            import subprocess
            result = subprocess.run(['which', 'chromium-browser'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                print(f"Found Chromium via which: {path}")
                return path
        except:
            pass
        
        print("No Chromium found, will use Playwright's bundled version")
        return None
    
    def setup_browser(self):
        """Setup Playwright with system Chromium if available"""
        self.playwright = sync_playwright().start()
        
        chromium_path = self.find_chromium_path()
        
        launch_options = {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-setuid-sandbox',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-extensions',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests'
            ]
        }
        
        if chromium_path:
            launch_options['executable_path'] = chromium_path
            print(f"Using system Chromium: {chromium_path}")
        else:
            print("Using Playwright's bundled Chromium")
        
        self.browser = self.playwright.chromium.launch(**launch_options)
        self.page = self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page.set_default_timeout(60000)
        
    def close_browser(self):
        """Close browser and playwright"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_article_data(self, card):
        """Extract all article data from a card element without navigating"""
        data = {
            'headline': 'N/A',
            'author': 'N/A',
            'date_time': 'N/A',
            'summary': 'N/A',
            'article_link': None
        }
        
        try:
            # Extract headline
            for tag in ['h2', 'h3', 'h1']:
                elem = card.query_selector(tag)
                if elem:
                    link = elem.query_selector('a')
                    if link:
                        text = link.inner_text().strip()
                        if text:
                            data['headline'] = text
                            # Get link from the same element
                            href = link.get_attribute('href')
                            if href:
                                data['article_link'] = self.get_full_url(href)
                            break
                    text = elem.inner_text().strip()
                    if text:
                        data['headline'] = text
                        break
        except:
            pass
        
        # If no headline found, try looking for any link
        if data['headline'] == 'N/A':
            try:
                links = card.query_selector_all('a')
                for link in links:
                    text = link.inner_text().strip()
                    if len(text) > 20 and not any(x in text.lower() for x in ['read more', 'comment', 'share']):
                        data['headline'] = text
                        href = link.get_attribute('href')
                        if href:
                            data['article_link'] = self.get_full_url(href)
                        break
            except:
                pass
        
        try:
            # Extract author
            author_elem = card.query_selector('[class*="author"], [class*="byline"]')
            if author_elem:
                link = author_elem.query_selector('a')
                if link:
                    data['author'] = link.inner_text().strip()
                else:
                    data['author'] = author_elem.inner_text().strip()
        except:
            pass
        
        try:
            # Extract date
            time_elem = card.query_selector('time')
            if time_elem:
                datetime_attr = time_elem.get_attribute('datetime')
                if datetime_attr:
                    data['date_time'] = datetime_attr
                else:
                    text = time_elem.inner_text().strip()
                    if text:
                        data['date_time'] = text
        except:
            pass
        
        try:
            # Extract summary
            summary_elem = card.query_selector('#speakable-summary')
            if summary_elem:
                text = summary_elem.inner_text().strip()
                if text:
                    data['summary'] = text
        except:
            pass
        
        return data
    
    def scrape_article_content(self, article_url):
        """Scrape full article content from a separate page"""
        if not article_url:
            return "N/A"
            
        try:
            print(f"  Fetching article: {article_url}")
            
            # Open a new page for content to keep main page intact
            content_page = self.browser.new_page()
            content_page.set_default_timeout(30000)
            
            try:
                content_page.goto(article_url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(2)
                
                # Wait for content to load
                try:
                    content_page.wait_for_selector('p.wp-block-paragraph', timeout=5000)
                except:
                    pass
                
                # Extract content
                content_parts = []
                
                # Try to find article body
                article_body = content_page.query_selector('[class*="article-content"], [class*="post-content"], [class*="entry-content"]')
                
                if article_body:
                    paragraphs = article_body.query_selector_all('p')
                else:
                    paragraphs = content_page.query_selector_all('p.wp-block-paragraph')
                    if not paragraphs:
                        paragraphs = content_page.query_selector_all('article p')
                    if not paragraphs:
                        paragraphs = content_page.query_selector_all('p')
                
                for p in paragraphs[:10]:
                    text = p.inner_text().strip()
                    if text and len(text) > 30:
                        content_parts.append(text)
                
                if content_parts:
                    content = ' '.join(content_parts)
                    if len(content) > 500:
                        content = content[:500] + "..."
                    return content
                
                return "N/A"
                
            finally:
                content_page.close()
            
        except Exception as e:
            print(f"  Error scraping article content: {e}")
            return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of news articles"""
        try:
            print(f"Fetching URL: {url}")
            
            # Navigate to the page
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for content to load
            try:
                self.page.wait_for_selector('h2 a, article, div.wp-block-techcrunch-card', timeout=10000)
            except PlaywrightTimeoutError:
                print("No articles found on this page")
                return None
            
            # Scroll to load more content
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Find article cards
            article_cards = []
            
            # Try multiple selectors
            selectors = [
                'div.wp-block-techcrunch-card',
                'article',
                '[class*="post"]',
                '[class*="article"]'
            ]
            
            for selector in selectors:
                cards = self.page.query_selector_all(selector)
                if cards:
                    article_cards = cards
                    print(f"Found {len(article_cards)} articles using selector: {selector}")
                    break
            
            # If still no cards, look for h2 with links
            if not article_cards:
                h2_elements = self.page.query_selector_all('h2')
                for h2 in h2_elements:
                    link = h2.query_selector('a')
                    if link:
                        parent = h2.query_selector('xpath=../..')
                        if parent:
                            article_cards.append(parent)
                if article_cards:
                    print(f"Found {len(article_cards)} articles from h2 elements")
            
            if not article_cards:
                print("No article cards found on this page")
                return None
            
            print(f"Processing {len(article_cards)} articles...")
            
            # Process each card
            for index, card in enumerate(article_cards):
                try:
                    # Extract data from card (no navigation)
                    article_data = self.extract_article_data(card)
                    
                    # Scrape full content only for first 2 articles
                    if article_data['article_link'] and index < 2:
                        article_data['content'] = self.scrape_article_content(article_data['article_link'])
                        time.sleep(random.uniform(1, 2))
                    else:
                        article_data['content'] = "N/A"
                    
                    article_data['scraped_at'] = datetime.now().isoformat()
                    self.articles.append(article_data)
                    
                    print(f"Article {index + 1}: {article_data['headline'][:40]}... - {article_data['author']}")
                    
                except Exception as e:
                    print(f"Error processing article {index}: {e}")
                    continue
            
            # Check for next page
            next_url = None
            try:
                next_button = self.page.query_selector('a.wp-block-query-pagination-next')
                if next_button:
                    next_url = next_button.get_attribute('href')
            except:
                pass
            
            if not next_url:
                try:
                    next_links = self.page.query_selector_all('a:has-text("Next")')
                    for link in next_links:
                        href = link.get_attribute('href')
                        if href:
                            next_url = href
                            break
                except:
                    pass
            
            if not next_url:
                try:
                    older_link = self.page.query_selector('a:has-text("Older posts")')
                    if older_link:
                        next_url = older_link.get_attribute('href')
                except:
                    pass
            
            if next_url:
                return self.get_full_url(next_url)
            
            print("No more pages found")
            return None
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
            return None
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=2):
        """Scrape multiple pages"""
        self.setup_browser()
        
        try:
            current_url = self.full_search_url
            page_num = 1
            
            print(f"\n{'='*60}")
            print(f"STARTING NEWS SCRAPER")
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
                print(f"Total articles scraped so far: {len(self.articles)}")
                
                delay = random.uniform(2, 4)
                print(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
            
            print(f"\n{'='*60}")
            print(f"SCRAPING COMPLETE!")
            print(f"Total articles scraped: {len(self.articles)}")
            print(f"{'='*60}")
            
        finally:
            self.close_browser()
        
        return self.articles
    
    def save_results(self, articles):
        """Save results to CSV and JSON - OVERWRITES existing files"""
        if not articles:
            print("No articles to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        fieldnames = ['headline', 'author', 'date_time', 'summary', 'content', 'article_link', 'scraped_at']
        
        # Save as CSV
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
            print(f"\n✓ CSV saved (overwritten): {self.csv_filename}")
            print(f"  Total records: {len(articles)}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            print(f"✓ JSON saved (overwritten): {self.json_filename}")
            print(f"  Total records: {len(articles)}")
        except Exception as e:
            print(f"✗ Error saving JSON: {e}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total articles: {len(articles)}")
        print(f"CSV file: {self.csv_filename}")
        print(f"JSON file: {self.json_filename}")
        
        # Show first 5 articles as preview
        print(f"\n{'='*60}")
        print("SAMPLE ARTICLES (first 5)")
        print(f"{'='*60}")
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article['headline']}")
            print(f"   Author: {article['author']}")
            print(f"   Date: {article['date_time']}")
            if article.get('summary') and article['summary'] != 'N/A':
                print(f"   Summary: {article['summary'][:100]}...")
            if article.get('content') and article['content'] != 'N/A':
                print(f"   Content preview: {article['content'][:100]}...")
            print("-" * 40)

if __name__ == "__main__":
    print("="*60)
    print("NEWS SCRAPER (Playwright with Chromium)")
    print("="*60)
    
    scraper = NewsScraper()
    articles = scraper.scrape(max_pages=2)
    scraper.save_results(articles)
