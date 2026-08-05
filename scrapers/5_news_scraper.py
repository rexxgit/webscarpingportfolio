# scrapers/5_news_scraper.py
import asyncio
import csv
import json
import os
import time
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

class TechCrunchScraper:
    """
    TechCrunch AI News Scraper using Playwright for JavaScript-rendered content.
    Follows the same pattern as other scrapers in the portfolio.
    """
    
    def __init__(self):
        self.base_url = "https://techcrunch.com"
        self.search_path = "/category/artificial-intelligence/"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.articles = []
        self.playwright = None
        self.browser = None
        self.page = None
        self.max_articles = 15
        self.max_pages = 3
        
        # Fixed filenames (no timestamps - overwrite)
        self.csv_filename = "output/news_articles.csv"
        self.json_filename = "output/news_articles.json"
    
    def get_full_url(self, path: str) -> Optional[str]:
        """Construct full URL from base URL and path"""
        if not path:
            return None
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return f"https:{path}"
        return urljoin(self.base_url, path)
    
    async def _init_browser(self):
        """Initialize Playwright browser with context."""
        try:
            self.playwright = await async_playwright().start()
            
            # Use a simpler launch configuration
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-setuid-sandbox'
                ]
            )
            
            self.page = await self.browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page.set_default_timeout(45000)
            
            print("✅ Playwright browser initialized")
        except Exception as e:
            print(f"❌ Error initializing browser: {e}")
            raise
    
    async def _close_browser(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("🔚 Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")
    
    async def _scroll_to_load(self):
        """Scroll to load lazy-loaded content."""
        try:
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
            await self.page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
            print("   📜 Scrolled to load content")
        except Exception as e:
            print(f"   ⚠️ Scroll error: {e}")
    
    async def _get_next_page_url(self) -> Optional[str]:
        """Extract the next page URL from pagination."""
        try:
            # Try multiple selectors for pagination
            selectors = [
                'a.wp-block-query-pagination-next',
                'a.next.page-numbers',
                'a:has-text("Next")',
                'a:has-text("Older posts")',
                '.next a'
            ]
            
            for selector in selectors:
                try:
                    next_link = await self.page.query_selector(selector)
                    if next_link:
                        href = await next_link.get_attribute('href')
                        if href:
                            print(f"   📌 Next page found: {href}")
                            return self.get_full_url(href)
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Could not find next page: {e}")
            return None
    
    async def _extract_article_urls_from_page(self, url: str) -> List[str]:
        """
        Scrape article URLs from a TechCrunch category page.
        """
        try:
            print(f"📄 Loading category page: {url}")
            
            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except PlaywrightTimeoutError:
                print("   ⏳ Load timeout, retrying...")
                try:
                    await self.page.goto(url, wait_until='commit', timeout=30000)
                except:
                    print("   ❌ Failed to load page")
                    return []
            
            # Wait for content with specific selector
            try:
                await self.page.wait_for_selector('h2', timeout=10000)
            except:
                print("   ⚠️ No h2 elements found")
            
            await asyncio.sleep(2)
            await self._scroll_to_load()
            
            article_urls = []
            
            # STRATEGY 1: h2 elements with links
            try:
                h2_elements = await self.page.query_selector_all('h2')
                for h2 in h2_elements:
                    link = await h2.query_selector('a')
                    if link:
                        href = await link.get_attribute('href')
                        if href and 'techcrunch.com' in href and '/category/' not in href:
                            if href not in article_urls:
                                article_urls.append(href)
            except Exception as e:
                print(f"   ⚠️ Strategy 1 error: {e}")
            
            # STRATEGY 2: article elements
            if len(article_urls) < 5:
                try:
                    articles = await self.page.query_selector_all('article')
                    for article in articles:
                        link = await article.query_selector('a')
                        if link:
                            href = await link.get_attribute('href')
                            if href and 'techcrunch.com' in href and '/category/' not in href:
                                if href not in article_urls:
                                    article_urls.append(href)
                except Exception as e:
                    print(f"   ⚠️ Strategy 2 error: {e}")
            
            # STRATEGY 3: Any link with date pattern
            if len(article_urls) < 5:
                try:
                    all_links = await self.page.query_selector_all('a[href*="techcrunch.com"]')
                    for link in all_links:
                        href = await link.get_attribute('href')
                        if href and '/202' in href and '/category/' not in href:
                            if href not in article_urls:
                                article_urls.append(href)
                except Exception as e:
                    print(f"   ⚠️ Strategy 3 error: {e}")
            
            # Remove duplicates
            article_urls = list(dict.fromkeys(article_urls))
            
            print(f"✅ Found {len(article_urls)} article URLs on this page")
            return article_urls
            
        except Exception as e:
            print(f"❌ Error scraping category page: {e}")
            return []
    
    async def _scrape_article_content(self, url: str) -> Optional[Dict]:
        """
        Scrape a single TechCrunch article page.
        """
        try:
            print(f"   📄 Scraping article: {url}")
            
            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except PlaywrightTimeoutError:
                print("   ⏳ Article load timeout, attempting to proceed...")
                try:
                    await self.page.evaluate("window.stop()")
                    await asyncio.sleep(2)
                except:
                    pass
            
            await asyncio.sleep(1.5)
            
            # EXTRACT TITLE
            title = "No Title"
            title_selectors = ['h1', '.article__title', '.entry-title', '.wp-block-post-title']
            for selector in title_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        title = await elem.text_content()
                        title = title.strip() if title else "No Title"
                        break
                except Exception:
                    continue
            
            # EXTRACT AUTHOR
            author = "Unknown"
            author_selectors = [
                '.byline a',
                '.article__byline a',
                '.author-name',
                '.wp-block-post-author__name'
            ]
            for selector in author_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        author = await elem.text_content()
                        author = author.strip() if author else "Unknown"
                        break
                except Exception:
                    continue
            
            # EXTRACT DATE
            date = datetime.now().strftime('%Y-%m-%d')
            date_selectors = ['time', '.post-date', '.article__date']
            for selector in date_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        datetime_val = await elem.get_attribute('datetime')
                        if datetime_val:
                            date = datetime_val
                        else:
                            text = await elem.text_content()
                            if text:
                                date = text.strip()
                        break
                except Exception:
                    continue
            
            # EXTRACT CONTENT
            content = ""
            content_selectors = ['.entry-content', '.article-content', '.post-content', 'article']
            
            content_elem = None
            for selector in content_selectors:
                try:
                    content_elem = await self.page.query_selector(selector)
                    if content_elem:
                        break
                except Exception:
                    continue
            
            if content_elem:
                try:
                    paragraphs = await content_elem.query_selector_all('p')
                    paragraph_texts = []
                    for p in paragraphs:
                        text = await p.text_content()
                        if text and len(text.strip()) > 20:
                            paragraph_texts.append(text.strip())
                    content = ' '.join(paragraph_texts)
                except Exception:
                    content = ""
            
            # Build result
            if content and len(content) > 100:
                return {
                    'headline': title,
                    'author': author,
                    'date_time': date,
                    'summary': content[:300] + "..." if len(content) > 300 else content,
                    'content': content[:2000],
                    'article_link': url,
                    'scraped_at': datetime.now().isoformat()
                }
            else:
                print(f"      ⚠️ Content too short or missing")
                return None
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return None
    
    async def scrape(self, max_articles: int = 15, max_pages: int = 3) -> List[Dict]:
        """
        Main scraping function.
        """
        print(f"\n{'='*60}")
        print(f"STARTING NEWS SCRAPER")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Search path: {self.search_path}")
        print(f"Full URL: {self.full_search_url}")
        print(f"Max articles: {max_articles}")
        print(f"Max pages: {max_pages}")
        print(f"{'='*60}\n")
        
        self.max_articles = max_articles
        self.max_pages = max_pages
        
        try:
            await self._init_browser()
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            return []
        
        try:
            all_urls = []
            current_url = self.full_search_url
            page_count = 0
            
            print("🔍 Step 1: Collecting article URLs...")
            while current_url and page_count < max_pages:
                page_count += 1
                print(f"\n📑 Scraping page {page_count}: {current_url}")
                
                try:
                    page_urls = await self._extract_article_urls_from_page(current_url)
                    
                    new_urls = [url for url in page_urls if url not in all_urls]
                    all_urls.extend(new_urls)
                    print(f"   📝 Added {len(new_urls)} new articles (total: {len(all_urls)})")
                    
                    if len(all_urls) >= max_articles:
                        print(f"   🎯 Reached target of {max_articles} articles")
                        break
                    
                    current_url = await self._get_next_page_url()
                    if current_url:
                        delay = random.uniform(1.5, 3.5)
                        print(f"   ⏳ Waiting {delay:.1f}s before next page...")
                        await asyncio.sleep(delay)
                    else:
                        print("   📌 No more pages available")
                        break
                        
                except Exception as e:
                    print(f"   ❌ Error on page {page_count}: {e}")
                    break
            
            if len(all_urls) > max_articles:
                all_urls = all_urls[:max_articles]
            
            print(f"\n✅ Collected {len(all_urls)} article URLs from {page_count} pages")
            
            if not all_urls:
                print("❌ No article URLs found")
                return []
            
            print(f"\n📝 Step 2: Scraping {len(all_urls)} articles...")
            articles = []
            for i, url in enumerate(all_urls):
                print(f"\n   📊 Progress: {i+1}/{len(all_urls)}")
                article = await self._scrape_article_content(url)
                if article:
                    articles.append(article)
                    print(f"      ✅ {article['headline'][:60]}...")
                await asyncio.sleep(random.uniform(1, 2.5))
            
            print(f"\n✅ Scraped {len(articles)} articles successfully")
            self.articles = articles
            return articles
            
        except Exception as e:
            print(f"❌ Scraper error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await self._close_browser()
    
    def save_results(self, articles: List[Dict]) -> None:
        """
        Save results to CSV and JSON - OVERWRITES existing files.
        """
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

# ================================================
# MAIN ENTRY POINT
# ================================================

async def main():
    """Async main entry point."""
    print("="*60)
    print("TECHCRUNCH NEWS SCRAPER")
    print("="*60)
    
    scraper = TechCrunchScraper()
    articles = await scraper.scrape(max_articles=10, max_pages=2)
    scraper.save_results(articles)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Scraper interrupted by user")
    except Exception as e:
        print(f"\n❌ Scraper failed: {e}")
        import traceback
        traceback.print_exc()
