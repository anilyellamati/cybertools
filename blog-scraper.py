#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import concurrent.futures
import re
import sys
import time
from urllib.parse import urlparse, urljoin
import pandas as pd
from dateutil import parser
import random
import os

# Set up User-Agent rotation to avoid being blocked
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
]

# Cybersecurity blog URLs
BLOG_URLS = {
    'Cisco Talos': 'https://blog.talosintelligence.com/',
    'Microsoft Security': 'https://www.microsoft.com/en-us/security/blog/',
    'Google Security Blog': 'https://security.googleblog.com/',
    'Cloudflare': 'https://blog.cloudflare.com/',
    'Palo Alto Networks Unit 42': 'https://unit42.paloaltonetworks.com/',
    'Mandiant': 'https://www.mandiant.com/resources/blog',
    'CrowdStrike': 'https://www.crowdstrike.com/blog/',
    'Symantec': 'https://symantec-enterprise-blogs.security.com/',
    'Trend Micro': 'https://www.trendmicro.com/en_us/research.html',
    'Kaspersky': 'https://securelist.com/',
    'Flashpoint': 'https://www.flashpoint.io/blog/',
    'Recorded Future': 'https://www.recordedfuture.com/blog',
    'Intel 471': 'https://intel471.com/blog',
    'Digital Shadows': 'https://www.digitalshadows.com/blog-and-research/',
    'Group-IB': 'https://www.group-ib.com/blog/',
    'RiskIQ': 'https://www.riskiq.com/blog/',
    'DomainTools': 'https://www.domaintools.com/resources/blog/',
    'BitSight': 'https://www.bitsight.com/blog',
    'Anomali': 'https://www.anomali.com/blog',
    'ThreatConnect': 'https://threatconnect.com/blog/',
    'IntSights': 'https://intsights.com/blog',
    'ESET': 'https://www.welivesecurity.com/',
    'McAfee': 'https://www.mcafee.com/blogs/',
    'Fortinet': 'https://www.fortinet.com/blog',
    'SentinelOne': 'https://www.sentinelone.com/blog/',
    'CheckPoint Research': 'https://research.checkpoint.com/',
    'F-Secure': 'https://blog.f-secure.com/',
    'Sophos': 'https://news.sophos.com/',
    'Proofpoint': 'https://www.proofpoint.com/us/blog',
    'Rapid7': 'https://www.rapid7.com/blog/',
    'Tenable': 'https://www.tenable.com/blog',
    'IBM Security': 'https://securityintelligence.com/',
    'VMware Carbon Black': 'https://blogs.vmware.com/security/',
    'Akamai': 'https://blogs.akamai.com/',
    'Cybereason': 'https://www.cybereason.com/blog'
}

class BlogScraper:
    def __init__(self):
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.yesterday = self.today - timedelta(days=1)
        self.results = []
        self.processed_blogs = 0
        self.total_blogs = len(BLOG_URLS)
        self.debug_info = {}
        
    def get_random_user_agent(self):
        return random.choice(USER_AGENTS)
    
    def clean_url(self, url):
        """Ensures URL has proper scheme"""
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url
    
    def make_request(self, url):
        """Make a request with error handling and retries"""
        headers = {'User-Agent': self.get_random_user_agent()}
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_date_from_text(self, text):
        """Try to extract date from a text string using regex patterns"""
        # Common date formats
        date_patterns = [
            # Apr 21, 2025
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})',
            # April 21, 2025
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            # 21 Apr 2025
            r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',
            # 21 April 2025
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            # 2025-04-21
            r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})',
            # 04/21/2025
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})'
        ]
        
        if not text:
            return None
        
        # Clean the text
        text = text.strip()
        
        # Try each pattern
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return parser.parse(match.group(0))
                except:
                    continue
        
        return None
    
    def extract_date(self, article, blog_name, url):
        """Try various methods to extract the date from an article"""
        date = None
        
        # Custom handling for Microsoft Security Blog
        if blog_name == 'Microsoft Security':
            try:
                # Look for the time element, which usually contains the date
                time_element = article.select_one('time')
                if time_element:
                    if time_element.has_attr('datetime'):
                        try:
                            date = parser.parse(time_element['datetime'])
                            return date
                        except:
                            pass
                    
                    try:
                        date = parser.parse(time_element.get_text().strip())
                        return date
                    except:
                        pass
                
                # Microsoft often has a specific class for the date
                date_element = article.select_one('.blog-post-meta-date, .c-paragraph-4, .posted-date')
                if date_element:
                    try:
                        date = parser.parse(date_element.get_text().strip())
                        return date
                    except:
                        pass
                
                # Look for date patterns in text content
                for element in article.select('p, span, div'):
                    text = element.get_text().strip()
                    if 'published' in text.lower() or 'posted' in text.lower() or 'date' in text.lower():
                        extracted_date = self.extract_date_from_text(text)
                        if extracted_date:
                            return extracted_date
                
                # Check for a structured data script tag
                for script in article.find_all('script', type='application/ld+json'):
                    try:
                        import json
                        data = json.loads(script.string)
                        if 'datePublished' in data:
                            return parser.parse(data['datePublished'])
                    except:
                        pass
            except Exception as e:
                print(f"Error extracting date from Microsoft blog: {e}")
        
        # Common date patterns to check for all blogs
        date_patterns = [
            # Look for HTML5 time elements
            lambda a: a.select_one('time'),
            lambda a: a.select_one('[datetime]'),
            
            # Look for common date class/id patterns
            lambda a: a.select_one('.date'),
            lambda a: a.select_one('.post-date'),
            lambda a: a.select_one('.entry-date'),
            lambda a: a.select_one('#date'),
            lambda a: a.select_one('.publish-date'),
            lambda a: a.select_one('.meta-date'),
            lambda a: a.select_one('.timestamp'),
            lambda a: a.select_one('.c-blog-date'),
            lambda a: a.select_one('.blog-date'),
            
            # Look for date text in common metadata elements
            lambda a: a.select_one('.meta'),
            lambda a: a.select_one('.entry-meta'),
            lambda a: a.select_one('.post-meta'),
            lambda a: a.select_one('.blog-meta'),
            lambda a: a.select_one('header'),
            lambda a: a.select_one('.article-info'),
            lambda a: a.select_one('.published'),
            lambda a: a.select_one('.posted-on'),
            lambda a: a.select_one('.byline')
        ]
        
        # Try each pattern
        for pattern in date_patterns:
            try:
                date_element = pattern(article)
                if date_element:
                    # First try to get datetime attribute
                    if date_element.has_attr('datetime'):
                        try:
                            date = parser.parse(date_element['datetime'])
                            return date
                        except:
                            pass
                    
                    # Try to parse the text content
                    try:
                        date = parser.parse(date_element.get_text().strip())
                        return date
                    except:
                        date_text = date_element.get_text().strip()
                        extracted_date = self.extract_date_from_text(date_text)
                        if extracted_date:
                            return extracted_date
            except:
                continue
        
        # If we still don't have a date, look for text patterns in the article
        if not date:
            # Look for any element with text that might contain a date
            for element in article.select('p, span, div, h1, h2, h3, h4, h5, h6'):
                try:
                    text = element.get_text().strip()
                    if len(text) < 100:  # Avoid processing long paragraphs
                        extracted_date = self.extract_date_from_text(text)
                        if extracted_date:
                            return extracted_date
                except:
                    continue
        
        # If we can't find a date, return None
        return None
    
    def is_current_or_previous_day(self, date):
        """Check if the date is from today or yesterday"""
        if not date:
            return False
        
        # Convert to date only for comparison
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # For debugging
        today_str = self.today.strftime('%Y-%m-%d')
        yesterday_str = self.yesterday.strftime('%Y-%m-%d')
        date_str = date_only.strftime('%Y-%m-%d')
        
        is_today = date_only == self.today
        is_yesterday = date_only == self.yesterday
        
        return is_today or is_yesterday
    
    def extract_title(self, article):
        """Extract the title of an article"""
        # Try different selectors for the title
        for selector in ['h1', 'h2', 'h3', '.title', '.post-title', '.entry-title']:
            title_element = article.select_one(selector)
            if title_element:
                return title_element.get_text().strip()
        return "Unknown Title"
    
    def extract_link(self, article, base_url):
        """Extract the full URL of an article"""
        # Try to find a link in the article or its title
        link_selectors = [
            # Look for a link in the title
            lambda a: a.select_one('h1 a, h2 a, h3 a, .title a, .post-title a, .entry-title a'),
            # Look for a "read more" link
            lambda a: a.select_one('a.read-more, a.more-link, a.continue-reading'),
            # Look for any link
            lambda a: a.select_one('a')
        ]
        
        for selector in link_selectors:
            try:
                link_element = selector(article)
                if link_element and link_element.has_attr('href'):
                    link = link_element['href']
                    # Make sure it's an absolute URL
                    if not link.startswith(('http://', 'https://')):
                        link = urljoin(base_url, link)
                    return link
            except:
                continue
        
        # If the article itself is an <a> tag
        if article.name == 'a' and article.has_attr('href'):
            link = article['href']
            if not link.startswith(('http://', 'https://')):
                link = urljoin(base_url, link)
            return link
        
        return None
    
    def custom_process_microsoft(self, url):
        """Custom processing for Microsoft Security Blog"""
        blog_results = []
        
        try:
            response = self.make_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Microsoft's blog posts are usually in article elements or divs with specific classes
            articles = soup.select('article, .blog-post, .m-post-card, .c-card')
            
            if not articles:
                # Try another approach for Microsoft's blog
                articles = soup.select('.blog-list-card, .card, .post')
            
            for article in articles:
                # Try to extract date
                date = None
                
                # Look for date elements
                date_elements = article.select('.blog-post-meta-date, time, .c-paragraph-4, .date, .posted-date')
                for date_element in date_elements:
                    try:
                        # Try to parse datetime attribute first
                        if date_element.has_attr('datetime'):
                            date = parser.parse(date_element['datetime'])
                            break
                        
                        # Try to parse text content
                        date_text = date_element.get_text().strip()
                        date = parser.parse(date_text)
                        break
                    except:
                        # Try regex pattern matching
                        date = self.extract_date_from_text(date_element.get_text().strip())
                        if date:
                            break
                
                # If we still don't have a date, look for dates in other elements
                if not date:
                    for element in article.select('p, span, div'):
                        text = element.get_text().strip()
                        date = self.extract_date_from_text(text)
                        if date:
                            break
                
                # Check if date is today or yesterday
                if self.is_current_or_previous_day(date):
                    # Extract title
                    title = None
                    title_elements = article.select('h1, h2, h3, .title, .post-title')
                    for title_element in title_elements:
                        title_text = title_element.get_text().strip()
                        if title_text:
                            title = title_text
                            break
                    
                    # Extract link
                    link = None
                    link_elements = article.select('a')
                    for link_element in link_elements:
                        if link_element.has_attr('href'):
                            href = link_element['href']
                            if href and not href.startswith('#') and not href.startswith('javascript:'):
                                if not href.startswith(('http://', 'https://')):
                                    link = urljoin(url, href)
                                else:
                                    link = href
                                break
                    
                    if title and link:
                        date_str = date.strftime('%Y-%m-%d') if date else "Unknown Date"
                        blog_results.append({
                            'Blog': 'Microsoft Security',
                            'Title': title,
                            'Date': date_str,
                            'URL': link
                        })
            
            return blog_results
            
        except Exception as e:
            print(f"Error processing Microsoft Security Blog: {str(e)}")
            return []
    
    def process_blog(self, blog_name, url):
        """Process a single blog URL"""
        blog_results = []
        
        try:
            # Special case for Microsoft Security Blog
            if blog_name == 'Microsoft Security':
                return self.custom_process_microsoft(url)
            
            url = self.clean_url(url)
            response = self.make_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Common article containers
            article_selectors = [
                'article', '.post', '.entry', '.blog-post', '.blog-entry',
                '.article', '.news-item', '.card', '.content-item',
                '.list-item', 'li.item', '.resource-item', '.col-md-4',
                '.post-item', '.blog-item', '.m-post-card'
            ]
            
            articles = []
            for selector in article_selectors:
                found = soup.select(selector)
                if found:
                    articles.extend(found)
                    
            # If we didn't find any articles with the selectors, try getting links and headers
            if not articles:
                # Get all potential heading elements that might be article titles
                headers = soup.select('h1, h2, h3')
                for header in headers:
                    # If the header is wrapped in a link or has a link inside
                    link = header.find('a') or header.parent.find('a')
                    if link:
                        articles.append(header.parent)
            
            # Process each article
            for article in articles:
                date = self.extract_date(article, blog_name, url)
                
                # For debugging
                if blog_name not in self.debug_info:
                    self.debug_info[blog_name] = {"parsed_dates": []}
                
                if date:
                    self.debug_info[blog_name]["parsed_dates"].append(
                        f"{date.strftime('%Y-%m-%d')} - is_recent: {self.is_current_or_previous_day(date)}"
                    )
                
                if self.is_current_or_previous_day(date):
                    title = self.extract_title(article)
                    link = self.extract_link(article, url)
                    if link and title and title != "Unknown Title":
                        # Format date string
                        date_str = date.strftime('%Y-%m-%d') if date else "Unknown Date"
                        blog_results.append({
                            'Blog': blog_name,
                            'Title': title,
                            'Date': date_str,
                            'URL': link
                        })
            
            # Update progress counter
            self.processed_blogs += 1
            print(f"Progress: [{self.processed_blogs}/{self.total_blogs}] - {blog_name} - Found {len(blog_results)} recent posts")
            
            return blog_results
            
        except Exception as e:
            # Update progress counter even on error
            self.processed_blogs += 1
            print(f"Progress: [{self.processed_blogs}/{self.total_blogs}] - Error processing {blog_name}: {str(e)}")
            return []
    
    def scrape_all_blogs(self):
        """Scrape all blogs using a thread pool"""
        print(f"Starting scan of {self.total_blogs} security blogs for posts on {self.today.strftime('%Y-%m-%d')} and {self.yesterday.strftime('%Y-%m-%d')}...")
        print("-" * 80)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_blog = {
                executor.submit(self.process_blog, blog_name, url): (blog_name, url)
                for blog_name, url in BLOG_URLS.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_blog):
                blog_name, url = future_to_blog[future]
                try:
                    blog_results = future.result()
                    if blog_results:
                        self.results.extend(blog_results)
                except Exception as e:
                    print(f"Error processing {blog_name}: {str(e)}")
        
        return self.results
    
    def save_results(self, output_format='csv'):
        """Save the results to a file"""
        if not self.results:
            print("No results to save.")
            return None
            
        df = pd.DataFrame(self.results)
        
        # Sort by date (newest first) and then by blog name
        df = df.sort_values(['Date', 'Blog'], ascending=[False, True])
        
        # Create timestamp and date strings for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        today_str = self.today.strftime('%Y-%m-%d')
        yesterday_str = self.yesterday.strftime('%Y-%m-%d')
        
        if output_format == 'csv':
            filename = f"security_blog_posts_{today_str}_and_{yesterday_str}_{timestamp}.csv"
            df.to_csv(filename, index=False)
        elif output_format == 'html':
            filename = f"security_blog_posts_{today_str}_and_{yesterday_str}_{timestamp}.html"
            df.to_html(filename, index=False)
        elif output_format == 'markdown':
            filename = f"security_blog_posts_{today_str}_and_{yesterday_str}_{timestamp}.md"
            with open(filename, 'w') as f:
                f.write("# Recent Cybersecurity Blog Posts\n\n")
                f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Posts from: {yesterday_str} to {today_str}\n\n")
                
                # Group by date
                for date in sorted(df['Date'].unique(), reverse=True):
                    f.write(f"## Posts from {date}\n\n")
                    date_posts = df[df['Date'] == date]
                    
                    # Group by blog
                    for blog in sorted(date_posts['Blog'].unique()):
                        f.write(f"### {blog}\n\n")
                        blog_posts = date_posts[date_posts['Blog'] == blog]
                        
                        for _, row in blog_posts.iterrows():
                            f.write(f"**{row['Title']}**\n\n")
                            f.write(f"[Read more]({row['URL']})\n\n")
                        
                        f.write("\n")
                    
                    f.write("---\n\n")
        
        print(f"Results saved to {filename}")
        return filename
    
    def display_results(self):
        """Display the results in the terminal"""
        if not self.results:
            print("\nNo blog posts found from today or yesterday.")
            return False
            
        df = pd.DataFrame(self.results)
        
        # Sort by date (newest first) and then by blog name
        df = df.sort_values(['Date', 'Blog'], ascending=[False, True])
        
        print("\n" + "="*80)
        print(f"FOUND {len(df)} BLOG POSTS PUBLISHED ON {self.today.strftime('%Y-%m-%d')} OR {self.yesterday.strftime('%Y-%m-%d')}")
        print("="*80)
        
        # Count posts by date
        date_counts = df['Date'].value_counts().to_dict()
        today_str = self.today.strftime('%Y-%m-%d')
        yesterday_str = self.yesterday.strftime('%Y-%m-%d')
        
        today_count = date_counts.get(today_str, 0)
        yesterday_count = date_counts.get(yesterday_str, 0)
        unknown_count = len(df) - today_count - yesterday_count
        
        print(f"Posts from today ({today_str}): {today_count}")
        print(f"Posts from yesterday ({yesterday_str}): {yesterday_count}")
        if unknown_count > 0:
            print(f"Posts with unknown/other date: {unknown_count}")
        print("-"*80)
        
        # Count posts by source
        blog_counts = df['Blog'].value_counts()
        print("\nPosts by source:")
        for blog, count in blog_counts.items():
            print(f"- {blog}: {count}")
        
        print("\nDETAILED RESULTS:")
        print("-"*80)
        
        for idx, row in df.iterrows():
            print(f"\n{idx+1}. {row['Title']}")
            print(f"   Blog: {row['Blog']}")
            print(f"   Date: {row['Date']}")
            print(f"   URL:  {row['URL']}")
            print("-"*80)
        
        return True

def main():
    print("\nCybersecurity Blog Post Scanner")
    print("=" * 40)
    
    scraper = BlogScraper()
    scraper.scrape_all_blogs()
    
    # Display only positive hits
    has_results = scraper.display_results()
    
    # Ask user if they want to save results
    if has_results:
        save = input("\nDo you want to save these results? (y/n): ").lower()
        if save == 'y':
            format_choice = input("Choose format (csv, html, markdown): ").lower()
            if format_choice in ['csv', 'html', 'markdown']:
                filename = scraper.save_results(format_choice)
                if filename:
                    print(f"\nResults saved to {os.path.abspath(filename)}")
            else:
                print("Invalid format choice. Saving as CSV by default.")
                filename = scraper.save_results('csv')
                if filename:
                    print(f"\nResults saved to {os.path.abspath(filename)}")
    else:
        print("\nNo results to save.")

if __name__ == "__main__":
    main()
