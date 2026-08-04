# scrapers/5_news_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import os
from datetime import datetime
import random

class NewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://techcrunch.com/category/artificial-intelligence/"
        self.articles = []
        
    def scrape_article_content(self, article_url):
        """Scrape full article content"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article body paragraphs
            body_paragraphs = soup.find_all('p', class_='wp-block-paragraph')
            content = ' '.join([p.text.strip() for p in body_paragraphs])
            
            return content
            
        except requests.RequestException as e:
            print(f"Error scraping article content: {e}")
            return "N/A"
    
    def scrape_page(self, url):
        """Scrape a single page of news articles"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            article_cards = soup.find_all('div', class_='wp-block-techcrunch-card')
            
            for card in article_cards:
                try:
                    # Extract headline
                    headline_elem = card.find('h2')
                    headline = headline_elem.text.strip() if headline_elem else "N/A"
                    
                    # Extract author
                    author_elem = card.find('a', class_='wp-block-tc23-author-card-name__link')
                    author = author_elem.text.strip() if author_elem else "N/A"
                    
                    # Extract date and time
                    time_elem = card.find('time')
                    date_time = time_elem.get('datetime') if time_elem else "N/A"
                    
                    # Extract summary
                    summary_elem = card.find('p', id='speakable-summary')
                    summary = summary_elem.text.strip() if summary_elem else "N/A"
                    
                    # Get article link
                    link_elem = card.find('a', class_='wp-block-tc23-post-card__link')
                    article_link = link_elem.get('href') if link_elem else None
                    
                    # Scrape full article content if link available
                    content = "N/A"
                    if article_link:
                        content = self.scrape_article_content(article_link)
                        time.sleep(random.uniform(1, 2))  # Be respectful
                    
                    self.articles.append({
                        'headline': headline,
                        'author': author,
                        'date_time': date_time,
                        'summary': summary,
                        'content': content[:500] + "..." if len(content) > 500 else content,  # Truncate for display
                        'article_link': article_link,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error parsing article card: {e}")
                    continue
            
            # Check for next page
            next_button = soup.find('a', class_='wp-block-query-pagination-next')
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
                    current_url = f"https://techcrunch.com{next_url}"
                else:
                    current_url = next_url
            else:
                break
                
            page_num += 1
            time.sleep(random.uniform(3, 5))
        
        return self.articles
    
    def save_results(self, articles):
        """Save results to CSV and JSON"""
        if not os.path.exists('output'):
            os.makedirs('output')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = f'output/news_articles_{timestamp}.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['headline', 'author', 'date_time', 'summary', 'content', 'article_link', 'timestamp'])
            writer.writeheader()
            writer.writerows(articles)
        
        # Save as JSON
        json_file = f'output/news_articles_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(articles)} articles to {csv_file} and {json_file}")

if __name__ == "__main__":
    scraper = NewsScraper()
    articles = scraper.scrape(max_pages=3)
    scraper.save_results(articles)
