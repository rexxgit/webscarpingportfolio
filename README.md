# Web Scraping Portfolio 🌐

A professional collection of 5 industry-specific web scrapers demonstrating diverse techniques across retail, real estate, business, recruitment, and media sectors. Built with Python, BeautifulSoup, Playwright, and automated via GitHub Actions.

## 📊 Scraper Portfolio

| # | Scraper | Industry | Target | Method | Key Data |
|---|---------|----------|--------|--------|----------|
| 1 | E-commerce | Retail | Redbubble | Playwright | Products, prices, ratings |
| 2 | Real Estate | Property | realestate.com.au | Requests + BS4 | Listings, prices, bedrooms |
| 3 | Business Directory | Local Business | Yellow Pages | Requests + BS4 | Companies, contacts, industry |
| 4 | Job Listings | Recruitment | Daybook | Requests + BS4 | Jobs, salaries, locations |
| 5 | News | Media | TechCrunch | Requests + BS4 | Headlines, authors, content |

## 🛠️ Technology Stack

- **Python 3.10+** with BeautifulSoup4, Requests, Playwright
- **LXML** for fast HTML parsing
- **GitHub Actions** for automated scheduling
- **Chromium** for JavaScript rendering

## 📁 Project Structure
webscrapingportfolio/
├── .github/workflows/ # 5 automated workflows
├── scrapers/ # 5 scraper scripts
├── output/ # CSV & JSON results (overwritten)
├── requirements.txt
└── README.md

text

## 🚀 Quick Start

```bash
# Clone and install
git clone https://github.com/rexxgit/webscarpingportfolio.git
cd webscarpingportfolio
pip install -r requirements.txt

# Install Playwright for E-commerce scraper
python -m playwright install chromium

# Run any scraper
python scrapers/1_ecommerce_scraper.py
python scrapers/5_news_scraper.py
🔧 Key Features
Consistent Output: All scrapers save to output/ as both CSV and JSON with automatic file overwrite (no duplicates).

Production-Ready: Each scraper includes error handling, rate limiting (2-5 second delays), pagination support, and user-agent rotation.

Automated Scheduling: GitHub Actions runs each scraper on schedule - E-commerce (weekly Sunday), Real Estate (weekly Monday), Business Directory (weekly Tuesday), Job Listings (weekly Wednesday), and News (every 6 hours).

Dual Approach: Uses Playwright for JavaScript-heavy sites and Requests/BeautifulSoup for static content.

📊 Data Extracted
E-commerce: Product names, prices ($37.01), ratings, stock status
Real Estate: Addresses, AUD/USD prices, bedrooms/bathrooms
Business Directory: Company names, phone numbers, emails, websites, industries
Job Listings: Job titles, companies, locations, salaries, posting times
News: Headlines, authors, publication dates, summaries, full content

🎯 Portfolio Value
This portfolio demonstrates:

5 distinct industries with different data structures

2 scraping methods (dynamic vs static)

Pagination handling across all scrapers

Deep scraping (following links to detail pages)

Regex patterns for extracting prices, phone numbers, and dates

Respectful scraping with proper rate limiting

🤖 Automated Workflows
Each scraper runs independently via GitHub Actions, committing fresh data to the repository. Manual triggers allow on-demand execution.

🔒 Ethical Practices
All scrapers implement responsible practices: user-agent masking, request delays (2-5 seconds), limited page scraping (2-3 pages), and data usage for educational purposes only.

Built with ❤️ for portfolio showcasing

text
