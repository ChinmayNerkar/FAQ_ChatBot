from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import List
import tempfile
import os

class WebScraper:
    def __init__(self, max_internal_links: int = 5, headless: bool = True):
        self.max_internal_links = max_internal_links
        self.headless = headless
        self.driver = self._init_driver()
    
    def _init_driver(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.netloc != base_domain:
            return False
        if parsed.path.endswith(('.pdf', '.jpg', '.png', '.gif')):
            return False
        return True
    
    def get_internal_links(self, url: str) -> List[str]:
        self.driver.get(url)
        time.sleep(2)  # Allow page to load
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        base_domain = urlparse(url).netloc
        internal_links = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(url, href)
            if self._is_valid_url(absolute_url, base_domain):
                internal_links.add(absolute_url)
        
        return list(internal_links)[:self.max_internal_links]
    
    def scrape_page(self, url: str, include_internal: bool = False) -> str:
        try:
            # Scrape main page
            self.driver.get(url)
            time.sleep(2)  # Allow page to load
            main_content = self.driver.page_source
            
            if not include_internal:
                return main_content
            
            # Scrape internal links
            internal_links = self.get_internal_links(url)
            all_content = [main_content]
            
            for link in internal_links:
                try:
                    self.driver.get(link)
                    time.sleep(1)
                    all_content.append(self.driver.page_source)
                except Exception as e:
                    print(f"Error scraping {link}: {str(e)}")
                    continue
            
            return "\n".join(all_content)
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            raise
    
    def scrape_multiple_urls(self, urls: List[str], include_internal: bool = False) -> str:
        all_content = []
        for url in urls:
            try:
                content = self.scrape_page(url, include_internal)
                all_content.append(content)
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                continue
        return "\n".join(all_content)