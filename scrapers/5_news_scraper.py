# scrapers/5_news_scraper.py
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

class TechCrunchScraper:
    """
    TechCrunch AI News Scraper using Requests and BeautifulSoup.
    More reliable than Playwright for CI/CD environments.
    """
    
    def __init__(self):
        self.base_url = "https://techcrunch.com"
        self.search_path = "/category/artificial-intelligence/"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.articles = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://techcrunch.com/'
        }
        
        # Fixed filenames (no timestamps - overwrite)
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
    
    def extract_headline(self, card):
        """Extract headline from article card"""
        try:
            # Method 1: Look for h2 with link
            h2 = card.find('h2')
            if h2:
                link = h2.find('a')
                if link:
                    return link.text.strip()
                return h2.text.strip()
        except:
            pass
        
        try:
            # Method 2: Look for any link with longer text
            links = card.find_all('a')
            for link in links:
                text = link.text.strip()
                if len(text) > 20 and not any(x in text.lower() for x in ['read more', 'comment', 'share']):
                    return text
        except:
            pass
        
        return "N/A"
    
    def extract_author(self, card):
        """Extract author from article card"""
        try:
            # Look for author/byline elements
            author_selectors = [
                '.wp-block-tc23-author-card-name__link',
                '.byline a',
                '.article__byline a',
                '[class*="author"]',
                '[class*="byline"]'
            ]
            
            for selector in author_selectors:
                elem = card.select_one(selector)
                if elem:
                    return elem.text.strip()
        except:
            pass
        
        return "N/A"
    
    def extract_date(self, card):
        """Extract date from article card"""
        try:
            # Look for time element
            time_elem = card.find('time')
            if time_elem:
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    return datetime_attr
                text = time_elem.text.strip()
                if text:
                    return text
        except:
            pass
        
        try:
            # Look for date patterns in text
            card_text = card.text
            date_patterns = [
                r'\d{1,2}:\d{2} [AP]M',
                r'[A-Z][a-z]+ \d{1,2}, \d{4}',
                r'\d{4}-\d{2}-\d{2}'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, card_text)
                if match:
                    return match.group()
        except:
            pass
        
        return "N/A"
    
    def extract_summary(self, card):
        """Extract summary from article card"""
        try:
            # Look for summary/excerpt
            summary_selectors = [
                '#speakable-summary',
                '[class*="excerpt"]',
                '[class*="summary"]',
                '[class*="description"]'
            ]
            
            for selector in summary_selectors:
                elem = card.select_one(selector)
                if elem:
                    text = elem.text.strip()
                    if len(text) > 20:
                        return text
        except:
            pass
        
        try:
            # Look for paragraphs that might be summary
            paragraphs = card.find_all('p')
            for p in paragraphs:
                text = p.text.strip()
                if len(text) > 50 and len(text) < 300:
                    if not any(x in text.lower() for x in ['read more', 'subscribe']):
                        return text
        except:
            pass
        
        return "N/A"
    
    def extract_article_url(self, card):
        """Extract article URL from card"""
        try:
            # Look for link in h2 first
            h2 = card.find('h2')
            if h2:
                link = h2.find('a')
                if link and link.get('href'):
                    return self.get_full_url(link.get('href'))
            
            # Look for any link with article-like text
            links = card.find_all('a')
            for link in links:
                href = link.get('href')
                if href and 'techcrunch.com' in href and '/category/' not in href:
                    if '/202' in href or link.text.strip() and len(link.text.strip()) > 15:
                        return self.get_full_url(href)
        except:
            pass
        
        return None
    
    def scrape_article_content(self, url):
        """Scrape full article content from article page"""
        if not url:
            return "N/A"
        
        try:
            print(f"  Fetching article: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article content
            content_parts = []
            
            # Try multiple content selectors
            content_selectors = [
                '.entry-content.wp-block-post-content',
                '.entry-content',
                '.article-content',
                '.post-content',
                'article'
            ]
            
            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break
            
            if content_elem:
                paragraphs = content_elem.find_all('p')
                for p in paragraphs[:10]:
                    text = p.text.strip()
                    if text and len(text) > 30:
                        content_parts.append(text)
            
            # Fallback: get all paragraphs
            if not content_parts:
                paragraphs = soup.find_all('p', class_='wp-block-paragraph')
                for p in paragraphs[:10]:
                    text = p.text.strip()
                    if text and len(text) > 30:
                        content_parts.append(text)
            
            if content_parts:
                content = ' '.join(content_parts)
                return content[:2000]
            
            return "N/A"
            
        except Exception as e:
            print(f"  Error scraping article content: {e}")
            return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of news articles"""
        try:
            print(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article cards using multiple methods
            article_cards = []
            
            # Method 1: TechCrunch card class
            cards = soup.find_all('div', class_=lambda c: c and 'wp-block-techcrunch-card' in c if c else False)
            if cards:
                article_cards = cards
                print(f"Found {len(article_cards)} cards with wp-block-techcrunch-card")
            
            # Method 2: Article elements
            if not article_cards:
                cards = soup.find_all('article')
                if cards:
                    article_cards = cards
                    print(f"Found {len(article_cards)} cards with article tag")
            
            # Method 3: Post containers
            if not article_cards:
                cards = soup.find_all('div', class_=lambda c: c and ('post' in c.lower() or 'article' in c.lower()) if c else False)
                if cards:
                    article_cards = cards
                    print(f"Found {len(article_cards)} cards with post/article class")
            
            # Method 4: H2 with links
            if not article_cards:
                h2_elements = soup.find_all('h2')
                for h2 in h2_elements:
                    link = h2.find('a')
                    if link and link.get('href') and 'techcrunch.com' in link.get('href'):
                        # Use the parent as card
                        parent = h2.parent
                        if parent:
                            article_cards.append(parent)
                if article_cards:
                    print(f"Found {len(article_cards)} cards from h2 elements")
            
            if not article_cards:
                print("No article cards found on this page")
                return None
            
            print(f"Processing {len(article_cards)} articles...")
            
            for index, card in enumerate(article_cards):
                try:
                    # Extract data
                    headline = self.extract_headline(card)
                    author = self.extract_author(card)
                    date_time = self.extract_date(card)
                    summary = self.extract_summary(card)
                    article_link = self.extract_article_url(card)
                    
                    # Scrape full content for first 3 articles
                    content = "N/A"
                    if article_link and index < 3:
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
                    print(f"Error parsing article {index}: {e}")
                    continue
            
            # Check for next page
            next_url = None
            
            # Try multiple pagination selectors
            pagination_selectors = [
                'a.wp-block-query-pagination-next',
                'a.next.page-numbers',
                'a:contains("Next")',
                'a:contains("Older posts")'
            ]
            
            for selector in pagination_selectors:
                try:
                    next_elem = soup.select_one(selector)
                    if next_elem and next_elem.get('href'):
                        next_url = self.get_full_url(next_elem.get('href'))
                        break
                except:
                    continue
            
            if next_url:
                print(f"Next page found: {next_url}")
                return next_url
            
            print("No more pages found")
            return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=3, max_articles=15):
        """Scrape multiple pages"""
        current_url = self.full_search_url
        page_num = 1
        total_articles = 0
        
        print(f"\n{'='*60}")
        print(f"STARTING NEWS SCRAPER (Requests + BeautifulSoup)")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Search path: {self.search_path}")
        print(f"Full URL: {self.full_search_url}")
        print(f"Max articles: {max_articles}")
        print(f"Max pages: {max_pages}")
        print(f"{'='*60}\n")
        
        while current_url and page_num <= max_pages and total_articles < max_articles:
            print(f"{'='*60}")
            print(f"SCRAPING PAGE {page_num}")
            print(f"{'='*60}")
            
            next_url = self.scrape_page(current_url)
            
            if next_url:
                current_url = next_url
            else:
                break
                
            page_num += 1
            total_articles = len(self.articles)
            print(f"Total articles scraped so far: {total_articles}")
            
            delay = random.uniform(2, 4)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
        
        # Trim to max articles
        if len(self.articles) > max_articles:
            self.articles = self.articles[:max_articles]
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total articles scraped: {len(self.articles)}")
        print(f"{'='*60}")
        
        return self.articles
    
    def save_results(self, articles):
        """Save results to CSV and JSON - OVERWRITES existing files"""
        if not articles:
            print("No articles to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        fieldnames = ['headline', 'author', 'date_time', 'summary', 'content', 'article_link', 'scraped_at']
        
        # Save as CSV - OVERWRITE
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
            print(f"\n✓ CSV saved (overwritten): {self.csv_filename}")
            print(f"  Total records: {len(articles)}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON - OVERWRITE
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            print(f"✓ JSON saved (overwritten): {self.json_filename}")
            print(f"  Total records: {len(articles)}")
        except Exception as e:
            print(f"✗ Error saving JSON: {e}")
        
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
    print("TECHCRUNCH NEWS SCRAPER")
    print("="*60)
    
    scraper = TechCrunchScraper()
    articles = scraper.scrape(max_pages=2, max_articles=10)
    scraper.save_results(articles)
