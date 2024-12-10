import asyncio
from collections import deque
from typing import Dict, List, Set
from crawl4ai.models import CrawlResult
from crawl4ai import AsyncWebCrawler
from urllib.parse import urljoin, urlparse, urlunparse

class SimpleWebsiteScraper:
    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler
        self.base_url = None

    def is_valid_internal_link(self, link: str) -> bool:
        if not link or link.startswith('#'):
            return False
        
        parsed_base = urlparse(self.base_url)
        parsed_link = urlparse(link)
        
        return (parsed_base.netloc == parsed_link.netloc and
                parsed_link.path not in ['', '/'] and
                parsed_link.path.startswith(parsed_base.path))

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        # Remove any fragments
        parsed = parsed._replace(fragment='')
        # Ensure the path doesn't end with a slash unless it's the root
        if parsed.path.endswith('/') and len(parsed.path) > 1:
            parsed = parsed._replace(path=parsed.path.rstrip('/'))
        return urlunparse(parsed)

    def join_url(self, base: str, url: str) -> str:
        joined = urljoin(base, url)
        parsed_base = urlparse(self.base_url)
        parsed_joined = urlparse(joined)
        
        # Ensure the joined URL starts with the base path
        if not parsed_joined.path.startswith(parsed_base.path):
            # If it doesn't, prepend the base path
            new_path = parsed_base.path.rstrip('/') + '/' + parsed_joined.path.lstrip('/')
            parsed_joined = parsed_joined._replace(path=new_path)
        
        return urlunparse(parsed_joined)

    async def scrape(self, start_url: str, max_depth: int) -> Dict[str, CrawlResult]:
        self.base_url = self.normalize_url(start_url)
        results: Dict[str, CrawlResult] = {}
        queue: deque = deque([(self.base_url, 0)])
        visited: Set[str] = set()

        while queue:
            current_url, current_depth = queue.popleft()
            
            if current_url in visited or current_depth > max_depth:
                continue
            
            visited.add(current_url)
            
            result = await self.crawler.arun(current_url)
            
            if result.success:
                results[current_url] = result
                
                if current_depth < max_depth:
                    internal_links = result.links.get('internal', [])
                    for link in internal_links:
                        full_url = self.join_url(current_url, link['href'])
                        normalized_url = self.normalize_url(full_url)
                        if self.is_valid_internal_link(normalized_url) and normalized_url not in visited:
                            queue.append((normalized_url, current_depth + 1))

        return results


async def main(start_url: str, depth: int):
    async with AsyncWebCrawler() as crawler:
        scraper = SimpleWebsiteScraper(crawler)
        results = await scraper.scrape(start_url, depth)
    
    print(f"Crawled {len(results)} pages:")
    for url, result in results.items():
        print(f"- {url}: {len(result.links.get('internal', []))} internal links, {len(result.links.get('external', []))} external links")

if __name__ == "__main__":
    start_url = "https://crawl4ai.com/mkdocs"
    depth = 2
    asyncio.run(main(start_url, depth))    