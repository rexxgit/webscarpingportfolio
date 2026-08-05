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
                '--disable-blink-features=AutomationControlled'
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
        self.page.set_default_timeout(30000)
        
    def close_browser(self):
        """Close browser and playwright"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_headline(self, card):
        """Extract headline using multiple methods"""
        try:
            # Method 1: Look for h2 or h3 with link
            for tag in ['h2', 'h3', 'h1']:
                elem = card.query_selector(tag)
                if elem:
                    link = elem.query_selector('a')
                    if link:
                        text = link.inner_text().strip()
                        if text:
                            return text
                    text = elem.inner_text().strip()
                    if text:
                        return text
        except:
            pass
            
        try:
            # Method 2: Look for any link with article title
            links = card.query_selector_all('a')
            for link in links:
                text = link.inner_text().strip()
                if len(text) > 20 and not any(x in text.lower() for x in ['read more', 'comment', 'share']):
                    return text
        except:
            pass
            
        try:
            # Method 3: Look for div with title class
            title_elem = card.query_selector('[class*="title"], [class*="headline"]')
            if title_elem:
                text = title_elem.inner_text().strip()
                if text:
                    return text
        except:
            pass
            
        return "N/A"
    
    def extract_author(self, card):
        """Extract author using multiple methods"""
        try:
            # Method 1: Look for author link
            author_elem = card.query_selector('[class*="author"], [class*="byline"]')
            if author_elem:
                link = author_elem.query_selector('a')
                if link:
                    return link.inner_text().strip()
                return author_elem.inner_text().strip()
        except:
            pass
            
        try:
            # Method 2: Look for any link with author name pattern
            links = card.query_selector_all('a')
            for link in links:
                text = link.inner_text().strip()
                if len(text) > 3 and len(text) < 30 and ' ' in text:
                    common_words = ['the', 'and', 'for', 'with', 'from', 'more', 'read', 'comment']
                    if not any(word in text.lower() for word in common_words):
                        # Check if it's in a byline context
                        parent = link.query_selector('xpath=..')
                        if parent:
                            parent_text = parent.inner_text().lower()
                            if 'by' in parent_text or 'author' in parent_text:
                                return text
        except:
            pass
            
        return "N/A"
    
    def extract_date(self, card):
        """Extract date using multiple methods"""
        try:
            # Method 1: Look for time tag
            time_elem = card.query_selector('time')
            if time_elem:
                datetime_attr = time_elem.get_attribute('datetime')
                if datetime_attr:
                    return datetime_attr
                text = time_elem.inner_text().strip()
                if text:
                    return text
        except:
            pass
            
        try:
            # Method 2: Look for date class
            date_elem = card.query_selector('[class*="date"], [class*="time"]')
            if date_elem:
                text = date_elem.inner_text().strip()
                if text:
                    return text
        except:
            pass
            
        try:
            # Method 3: Look for date pattern in text
            card_text = card.inner_text()
            date_patterns = [
                r'\d{1,2}:\d{2} [AP]M',  # 6:00 AM
                r'\d{1,2}:\d{2}:\d{2}',   # 06:00:00
                r'[A-Z][a-z]+ \d{1,2}, \d{4}',  # August 4, 2026
                r'\d{4}-\d{2}-\d{2}',     # 2026-08-04
            ]
            for pattern in date_patterns:
                match = re.search(pattern, card_text)
                if match:
                    return match.group()
        except:
            pass
            
        return "N/A"
    
    def extract_summary(self, card):
        """Extract summary using multiple methods"""
        try:
            # Method 1: Look for specific summary element
            summary_elem = card.query_selector('#speakable-summary')
            if summary_elem:
                text = summary_elem.inner_text().strip()
                if text:
                    return text
        except:
            pass
            
        try:
            # Method 2: Look for any paragraph that might be a summary
            paragraphs = card.query_selector_all('p')
            for p in paragraphs:
                text = p.inner_text().strip()
                if len(text) > 50 and len(text) < 300:
                    if not any(x in text.lower() for x in ['read more', 'subscribe', 'newsletter']):
                        return text
        except:
            pass
            
        try:
            # Method 3: Look for div with excerpt class
            excerpt = card.query_selector('[class*="excerpt"], [class*="summary"], [class*="description"]')
            if excerpt:
                text = excerpt.inner_text().strip()
                if text:
                    return text
        except:
            pass
            
        return "N/A"
    
    def scrape_article_content(self, article_url):
        """Scrape full article content"""
        if not article_url:
            return "N/A"
            
        try:
            print(f"  Fetching article: {article_url}")
            
            # Navigate to article page
            self.page.goto(article_url, wait_until='networkidle')
            time.sleep(2)
            
            # Wait for content to load
            try:
                self.page.wait_for_selector('p.wp-block-paragraph', timeout=10000)
            except:
                pass
            
            # Extract content
            content_parts = []
            
            # Method 1: Look for article content
            article_body = self.page.query_selector('[class*="article-content"], [class*="post-content"], [class*="entry-content"]')
            
            if article_body:
                paragraphs = article_body.query_selector_all('p')
            else:
                # Fallback: find all paragraphs
                paragraphs = self.page.query_selector_all('p.wp-block-paragraph')
                if not paragraphs:
                    paragraphs = self.page.query_selector_all('p')
            
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
            
        except Exception as e:
            print(f"  Error scraping article content: {e}")
            return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of news articles"""
        try:
            print(f"Fetching URL: {url}")
            
            # Navigate to the page
            self.page.goto(url, wait_until='networkidle')
            time.sleep(3)
            
            # Wait for content to load
            try:
                self.page.wait_for_selector('div.wp-block-techcrunch-card', timeout=15000)
            except PlaywrightTimeoutError:
                print("Timeout waiting for article cards. Trying alternative selectors...")
                try:
                    self.page.wait_for_selector('article', timeout=10000)
                except:
                    print("No articles found on this page")
                    return None
            
            # Scroll to load more content
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Try multiple selectors for article cards
            article_cards = []
            
            # Method 1: Primary selector
            article_cards = self.page.query_selector_all('div.wp-block-techcrunch-card')
            
            # Method 2: Look for article containers
            if not article_cards:
                article_cards = self.page.query_selector_all('article')
            
            # Method 3: Look for post containers
            if not article_cards:
                article_cards = self.page.query_selector_all('[class*="post"], [class*="article"]')
            
            print(f"Found {len(article_cards)} article cards on this page")
            
            for index, card in enumerate(article_cards):
                try:
                    headline = self.extract_headline(card)
                    author = self.extract_author(card)
                    date_time = self.extract_date(card)
                    summary = self.extract_summary(card)
                    
                    # Get article link
                    article_link = None
                    link = card.query_selector('a')
                    if link:
                        href = link.get_attribute('href')
                        if href:
                            article_link = self.get_full_url(href)
                    
                    # Scrape full article content if link available
                    content = "N/A"
                    if article_link:
                        content = self.scrape_article_content(article_link)
                        time.sleep(random.uniform(1, 2))
                    
                    print(f"Article {index + 1}: {headline[:40]}... - {author}")
                    
                    self.articles.append({
                        'headline': headline,
                        'author': author,
                        'date_time': date_time,
                        'summary': summary,
                        'content': content,
                        'article_link': article_link,
                        'scraped_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing article card {index}: {e}")
                    continue
            
            # Check for next page
            try:
                next_button = self.page.query_selector('a.wp-block-query-pagination-next')
                if next_button:
                    next_url = next_button.get_attribute('href')
                    if next_url:
                        return self.get_full_url(next_url)
            except:
                pass
                
            # Try alternative pagination
            try:
                next_links = self.page.query_selector_all('a:has-text("Next")')
                for link in next_links:
                    href = link.get_attribute('href')
                    if href:
                        return self.get_full_url(href)
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
        
        # Save as CSV - OVERWRITE if exists
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
            print(f"\n✓ CSV saved (overwritten): {self.csv_filename}")
            print(f"  Total records: {len(articles)}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON - OVERWRITE if exists
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
            if article.get('summary'):
                print(f"   Summary: {article['summary'][:100]}...")
            print("-" * 40)

if __name__ == "__main__":
    print("="*60)
    print("NEWS SCRAPER (Playwright with Chromium)")
    print("="*60)
    
    scraper = NewsScraper()
    articles = scraper.scrape(max_pages=2)
    scraper.save_results(articles)
