"""Content fetcher for extracting full page content from URLs."""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse


@dataclass
class FetchedContent:
    """Fetched and extracted web page content."""

    # Source
    url: str
    final_url: str  # After redirects
    status_code: int

    # Content
    title: str
    text_content: str
    html_content: Optional[str] = None

    # Metadata
    meta_description: Optional[str] = None
    meta_keywords: List[str] = field(default_factory=list)
    author: Optional[str] = None
    publish_date: Optional[str] = None

    # Structure
    headings: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

    # Statistics
    word_count: int = 0
    read_time_minutes: int = 0

    # Temporal
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "title": self.title,
            "text_content": self.text_content,
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
            "author": self.author,
            "publish_date": self.publish_date,
            "headings": self.headings,
            "word_count": self.word_count,
            "read_time_minutes": self.read_time_minutes,
            "fetched_at": self.fetched_at.isoformat(),
        }


class ContentFetcher:
    """Fetch and extract content from web pages."""

    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 1_000_000,  # 1MB
        user_agent: Optional[str] = None,
        follow_redirects: bool = True,
        extract_images: bool = False,
        extract_links: bool = False,
    ):
        """Initialize content fetcher.

        Args:
            timeout: Request timeout in seconds
            max_content_length: Max content size in bytes
            user_agent: Custom user agent string
            follow_redirects: Follow HTTP redirects
            extract_images: Extract image URLs
            extract_links: Extract link URLs
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.follow_redirects = follow_redirects
        self.extract_images = extract_images
        self.extract_links = extract_links

        # Default user agent
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        # Statistics
        self.stats = {
            "total_fetches": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "bytes_downloaded": 0,
        }

    async def fetch(self, url: str) -> FetchedContent:
        """Fetch and extract content from URL.

        Args:
            url: URL to fetch

        Returns:
            FetchedContent object

        Raises:
            httpx.HTTPError: If fetch fails
        """
        self.stats["total_fetches"] += 1

        # Validate URL
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        # Fetch content
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
            headers={"User-Agent": self.user_agent},
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                # Check content length
                content_length = len(response.content)
                if content_length > self.max_content_length:
                    raise ValueError(f"Content too large: {content_length} bytes")

                self.stats["bytes_downloaded"] += content_length
                self.stats["successful_fetches"] += 1

                # Parse content
                return self._parse_content(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    html=response.text,
                )

            except Exception as e:
                self.stats["failed_fetches"] += 1
                raise

    def _parse_content(
        self,
        url: str,
        final_url: str,
        status_code: int,
        html: str,
    ) -> FetchedContent:
        """Parse HTML content.

        Args:
            url: Original URL
            final_url: Final URL after redirects
            status_code: HTTP status code
            html: HTML content

        Returns:
            FetchedContent object
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Extract metadata
        meta_description = self._extract_meta_description(soup)
        meta_keywords = self._extract_meta_keywords(soup)
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)

        # Extract main content
        text_content = self._extract_text_content(soup)

        # Extract headings
        headings = self._extract_headings(soup)

        # Extract images and links if enabled
        images = []
        links = []

        if self.extract_images:
            images = self._extract_images(soup, final_url)

        if self.extract_links:
            links = self._extract_links(soup, final_url)

        # Calculate statistics
        word_count = len(text_content.split())
        read_time_minutes = max(1, word_count // 250)  # 250 WPM

        return FetchedContent(
            url=url,
            final_url=final_url,
            status_code=status_code,
            title=title,
            text_content=text_content,
            html_content=html if len(html) < 100_000 else None,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            author=author,
            publish_date=publish_date,
            headings=headings,
            links=links,
            images=images,
            word_count=word_count,
            read_time_minutes=read_time_minutes,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try <title> tag
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try Open Graph title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try first h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        return "Untitled"

    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description."""
        # Standard meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Open Graph description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        return None

    def _extract_meta_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract meta keywords."""
        meta = soup.find("meta", attrs={"name": "keywords"})
        if meta and meta.get("content"):
            keywords = meta["content"].split(",")
            return [k.strip() for k in keywords if k.strip()]

        return []

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author."""
        # Meta author tag
        meta = soup.find("meta", attrs={"name": "author"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Schema.org author
        author = soup.find("span", itemprop="author")
        if author:
            return author.get_text().strip()

        return None

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publish date."""
        # Meta tags
        for prop in ["article:published_time", "datePublished", "publishDate"]:
            meta = soup.find("meta", property=prop)
            if meta and meta.get("content"):
                return meta["content"].strip()

        # Time tag
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return time_tag["datetime"]

        return None

    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Try to find main content area
        main_content = None

        # Common content containers
        for selector in ["main", "article", "#content", ".content", ".post-content"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # Fall back to body
        if not main_content:
            main_content = soup.body

        if not main_content:
            return ""

        # Extract text
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extract all headings."""
        headings = []

        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = tag.get_text().strip()
            if text:
                headings.append(text)

        return headings

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs."""
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                # Make absolute URL
                absolute_url = urljoin(base_url, src)
                images.append(absolute_url)

        return images[:50]  # Limit to 50 images

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract link URLs."""
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Make absolute URL
            absolute_url = urljoin(base_url, href)

            # Filter out anchors and javascript
            if not absolute_url.startswith(("javascript:", "#", "mailto:")):
                links.append(absolute_url)

        return list(set(links))[:100]  # Limit to 100 unique links

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        return self.stats.copy()

    # Synchronous wrapper
    def fetch_sync(self, url: str) -> FetchedContent:
        """Synchronous fetch wrapper."""
        import asyncio

        return asyncio.run(self.fetch(url))
