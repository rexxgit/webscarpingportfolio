# scrapers/3_business_directory_scraper.py
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

class BusinessDirectoryScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.base_url = "https://www.yellowpages.com"
        self.search_path = "/los-angeles-ca/general-contractors"
        self.full_search_url = urljoin(self.base_url, self.search_path)
        self.businesses = []
        # Fixed filenames (no timestamps)
        self.csv_filename = "output/business_directory.csv"
        self.json_filename = "output/business_directory.json"
        
    def get_full_url(self, path):
        """Construct full URL from base URL and path"""
        if not path:
            return None
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return f"https:{path}"
        return urljoin(self.base_url, path)
    
    def scrape_listing_details(self, listing_url):
        """Scrape detailed information from a business listing page"""
        try:
            print(f"  Fetching details: {listing_url}")
            response = requests.get(listing_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # EXTRACT BUSINESS NAME - Using your selector
            name = "N/A"
            name_elem = soup.find('h1', class_='dockable business-name')
            if name_elem:
                name = name_elem.text.strip()
            
            # EXTRACT PHONE
            phone = "N/A"
            phone_elem = soup.find('a', {'data-analytics': lambda x: x and 'phone-no' in str(x) if x else False})
            if phone_elem:
                phone = phone_elem.text.strip()
            else:
                # Fallback: look for phone pattern
                phone_pattern = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', soup.text)
                if phone_pattern:
                    phone = phone_pattern.group()
            
            # EXTRACT EMAIL
            email = "N/A"
            email_elem = soup.find('a', {'href': lambda x: x and x.startswith('mailto:') if x else False})
            if email_elem:
                email = email_elem.get('href', '').replace('mailto:', '')
            
            # EXTRACT WEBSITE
            website = "N/A"
            website_elem = soup.find('a', {'href': lambda x: x and 'website' in str(x) if x else False})
            if website_elem and website_elem.get('href'):
                website = website_elem.get('href')
            else:
                # Look for any external link
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if href and 'http' in href and 'yellowpages' not in href:
                        website = href
                        break
            
            # EXTRACT INDUSTRY - Using your selector
            industry = "N/A"
            industry_elem = soup.find('a', {'href': lambda x: x and 'bathroom-remodeling' in str(x) if x else False})
            if industry_elem:
                industry = industry_elem.text.strip()
            else:
                # Look for any category link
                category_links = soup.find_all('a', href=lambda x: x and '/los-angeles-ca/' in str(x) if x else False)
                for link in category_links:
                    text = link.text.strip()
                    if text and len(text) > 3:
                        industry = text
                        break
            
            return {
                'business_name': name,
                'phone': phone,
                'email': email,
                'website': website,
                'industry': industry,
                'scraped_at': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            print(f"  Error scraping listing details: {e}")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            return None
    
    def scrape_page(self, url):
        """Scrape a single page of business listings"""
        try:
            print(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # FIND LISTING CARDS - Using your exact selector
            # The class is "srp-listing clickable-area paid-listing astro-tmc"
            listing_cards = soup.find_all('div', class_=lambda c: c and 'srp-listing' in c if c else False)
            
            if not listing_cards:
                # Fallback: look for any div with srp-listing
                listing_cards = soup.find_all('div', class_='srp-listing')
            
            print(f"Found {len(listing_cards)} listing cards on this page")
            
            for index, card in enumerate(listing_cards):
                try:
                    # EXTRACT BUSINESS NAME from the card (before clicking)
                    # Using your selector: <h1 class="dockable business-name">
                    business_name = "N/A"
                    name_elem = card.find('h1', class_='dockable business-name')
                    if name_elem:
                        business_name = name_elem.text.strip()
                    
                    # EXTRACT INDUSTRY from the card
                    # Using your selector: <a href="/van-nuys-ca/bathroom-remodeling">
                    industry = "N/A"
                    industry_elem = card.find('a', {'href': lambda x: x and 'bathroom-remodeling' in str(x) if x else False})
                    if industry_elem:
                        industry = industry_elem.text.strip()
                    
                    # EXTRACT TIME INFO if available
                    time_info = "N/A"
                    time_elem = card.find('div', class_='time-info')
                    if time_elem:
                        time_info = time_elem.text.strip()
                    
                    # GET LISTING URL for detailed scraping
                    # Look for the link that goes to the listing page
                    listing_url = None
                    
                    # Try to find the link with addest or mip in the URL
                    links = card.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if href and ('mip/' in href or 'listing/' in href):
                            listing_url = self.get_full_url(href)
                            break
                    
                    # If no URL found, try to find any link with /mip/
                    if not listing_url:
                        for link in links:
                            href = link.get('href', '')
                            if href and '/mip/' in href:
                                listing_url = self.get_full_url(href)
                                break
                    
                    # If still no URL, try to construct from data attributes
                    if not listing_url:
                        # Check for addest in data-analytics
                        analytics = card.get('data-analytics', '')
                        if analytics:
                            try:
                                # Parse the JSON in data-analytics
                                import json
                                data = json.loads(analytics)
                                if 'addest' in data:
                                    listing_url = self.get_full_url(data['addest'])
                            except:
                                pass
                    
                    print(f"  Processing business {index + 1}: {business_name}")
                    print(f"    Industry: {industry}")
                    print(f"    Listing URL: {listing_url}")
                    
                    # Scrape detailed information if we have a URL
                    details = None
                    if listing_url:
                        details = self.scrape_listing_details(listing_url)
                        time.sleep(random.uniform(1, 2))
                    
                    # Use card data if details scraping failed
                    if details and details['business_name'] != "N/A":
                        self.businesses.append(details)
                        print(f"    ✅ Added: {details['business_name']}")
                    elif business_name != "N/A":
                        # Use the data from the card
                        self.businesses.append({
                            'business_name': business_name,
                            'phone': 'N/A',
                            'email': 'N/A',
                            'website': 'N/A',
                            'industry': industry,
                            'scraped_at': datetime.now().isoformat()
                        })
                        print(f"    ✅ Added (from card): {business_name}")
                    else:
                        print(f"    ⚠️ No business name found")
                    
                except Exception as e:
                    print(f"Error parsing business card {index}: {e}")
                    continue
            
            # FIND PAGINATION - Using your selector
            # <a href="/los-angeles-ca/general-contractors?page=2" data-page="2">
            next_url = None
            
            # Look for next page link with data-page attribute
            next_links = soup.find_all('a', {'data-page': True})
            for link in next_links:
                page_num = link.get('data-page')
                if page_num and int(page_num) > 1:
                    href = link.get('href')
                    if href:
                        # Find the highest page number (should be the last page)
                        # But we want the next page, so we need to find the current page + 1
                        pass
            
            # Look for pagination links
            pagination_links = soup.find_all('a', href=lambda x: x and 'page=' in str(x) if x else False)
            for link in pagination_links:
                href = link.get('href')
                if href and 'page=' in href:
                    # Check if it's a numbered page
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        if page_num > 1:
                            # Check if this is the next page or a later page
                            # We'll just take the first one we find (page 2)
                            if page_num == 2:
                                next_url = self.get_full_url(href)
                                break
            
            # Fallback: look for "Next" link
            if not next_url:
                next_link = soup.find('a', string=lambda x: x and ('Next' in str(x) or '»' in str(x)) if x else False)
                if next_link and next_link.get('href'):
                    next_url = self.get_full_url(next_link.get('href'))
            
            if next_url:
                print(f"Next page found: {next_url}")
                return next_url
            else:
                print("No more pages found")
                return None
            
        except requests.RequestException as e:
            print(f"Error scraping page: {e}")
            return None
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None
    
    def scrape(self, max_pages=3):
        """Scrape multiple pages"""
        current_url = self.full_search_url
        page_num = 1
        
        print(f"\n{'='*60}")
        print(f"STARTING BUSINESS DIRECTORY SCRAPER")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Search path: {self.search_path}")
        print(f"Full URL: {self.full_search_url}")
        print(f"Max pages: {max_pages}")
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
            print(f"Total businesses scraped so far: {len(self.businesses)}")
            
            delay = random.uniform(2, 4)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total businesses scraped: {len(self.businesses)}")
        print(f"{'='*60}")
        
        return self.businesses
    
    def save_results(self, businesses):
        """Save results to CSV and JSON - OVERWRITES existing files"""
        if not businesses:
            print("No businesses to save!")
            return
            
        if not os.path.exists('output'):
            os.makedirs('output')
        
        fieldnames = ['business_name', 'phone', 'email', 'website', 'industry', 'scraped_at']
        
        # Save as CSV - OVERWRITE
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(businesses)
            print(f"\n✓ CSV saved (overwritten): {self.csv_filename}")
            print(f"  Total records: {len(businesses)}")
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
        
        # Save as JSON - OVERWRITE
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(businesses, f, indent=2, ensure_ascii=False)
            print(f"✓ JSON saved (overwritten): {self.json_filename}")
            print(f"  Total records: {len(businesses)}")
        except Exception as e:
            print(f"✗ Error saving JSON: {e}")
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total businesses: {len(businesses)}")
        print(f"CSV file: {self.csv_filename}")
        print(f"JSON file: {self.json_filename}")
        
        # Show first 5 businesses as preview
        print(f"\n{'='*60}")
        print("SAMPLE BUSINESSES (first 5)")
        print(f"{'='*60}")
        for i, business in enumerate(businesses[:5], 1):
            print(f"{i}. {business['business_name']}")
            print(f"   Phone: {business['phone']}")
            print(f"   Website: {business['website']}")
            print(f"   Industry: {business['industry']}")
            print("-" * 40)

if __name__ == "__main__":
    print("="*60)
    print("BUSINESS DIRECTORY SCRAPER")
    print("="*60)
    
    scraper = BusinessDirectoryScraper()
    businesses = scraper.scrape(max_pages=2)
    scraper.save_results(businesses)
