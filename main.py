from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
import yt_dlp
import asyncio
from datetime import datetime
import os
import random
import requests

app = FastAPI(
    title="Video Metadata Extraction API",
    description="Extract metadata from YouTube, TikTok, and Instagram videos",
    version="1.0.0"
)

# ScrapeOps Proxy Configuration
SCRAPEOPS_PROXY = "http://scrapeops:04b1ed1c-8ea5-4fdf-8f96-814b91f8bf36@residential-proxy.scrapeops.io:8181"

# Load proxies from file
PROXIES = []
if os.path.exists("proxies.txt"):
    with open("proxies.txt", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                PROXIES.append(line)

def get_proxy(use_scrapeops: bool = False) -> Optional[str]:
    """Get proxy URL"""
    if use_scrapeops:
        return SCRAPEOPS_PROXY
    if PROXIES:
        proxy = random.choice(PROXIES)
        parsed = parse_proxy(proxy)
        if parsed:
            return parsed['http']
    return None

def parse_proxy(proxy_str: str) -> dict:
    """Parse proxy string into components"""
    parts = proxy_str.split(":")
    if len(parts) == 4:
        ip, port, username, password = parts
        return {
            "http": f"http://{username}:{password}@{ip}:{port}",
            "https": f"http://{username}:{password}@{ip}:{port}"
        }
    return None

class VideoRequest(BaseModel):
    url: HttpUrl
    cookies_file: Optional[str] = Field(default=None, description="Path to cookies file for authentication")
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")

class YouTubeRequest(BaseModel):
    url: HttpUrl
    cookies_file: Optional[str] = Field(default="youtube_cookies.txt", description="Path to YouTube cookies file")
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    include_all_formats: Optional[bool] = Field(default=True, description="Include all video formats with direct URLs")

class TwitterRequest(BaseModel):
    url: HttpUrl
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    include_all_formats: Optional[bool] = Field(default=True, description="Include all video formats with direct URLs")

class TwitterCommentsRequest(BaseModel):
    url: HttpUrl
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    max_comments: Optional[int] = Field(default=50, description="Maximum number of comments to fetch (default: 50)")


class InstagramRequest(BaseModel):
    url: HttpUrl
    cookies_file: Optional[str] = Field(default="instagram_cookies.txt", description="Path to Instagram cookies file (required for most content)")
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    include_all_formats: Optional[bool] = Field(default=True, description="Include all video formats with direct URLs")

class InstagramCommentsRequest(BaseModel):
    url: HttpUrl
    cookies_file: Optional[str] = Field(default="instagram_cookies.txt", description="Path to Instagram cookies file")
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    max_comments: Optional[int] = Field(default=50, description="Maximum number of comments to fetch (default: 50)")


class TikTokRequest(BaseModel):
    url: HttpUrl
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    include_all_formats: Optional[bool] = Field(default=True, description="Include all video formats with direct URLs")

class YouTubeCommentsRequest(BaseModel):
    url: HttpUrl
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    max_comments: Optional[int] = Field(default=100, description="Maximum number of comments to fetch (default: 100)")

class TikTokCommentsRequest(BaseModel):
    url: HttpUrl
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")
    max_comments: Optional[int] = Field(default=100, description="Maximum number of comments to fetch (default: 100)")


class Comment(BaseModel):
    author: Optional[str] = None
    author_id: Optional[str] = None
    text: Optional[str] = None
    like_count: Optional[int] = None
    timestamp: Optional[Any] = None  # Can be int or string
    reply_count: Optional[int] = None

class CommentsResponse(BaseModel):
    success: bool
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    total_comments: Optional[int] = None
    comments: List[Comment] = []
    error: Optional[str] = None
    timestamp: str

class VideoMetadata(BaseModel):
    platform: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None  # Can be int or float (Twitter/X uses float)
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    upload_date: Optional[str] = None
    uploader: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    thumbnail: Optional[str] = None
    thumbnails: Optional[List[Dict[str, Any]]] = None
    video_id: Optional[str] = None
    formats: Optional[List[Dict[str, Any]]] = None
    subtitles: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    age_limit: Optional[int] = None
    availability: Optional[str] = None
    live_status: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None

class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[VideoMetadata] = None
    error: Optional[str] = None
    timestamp: str


def extract_twitter_metadata(url: str, use_proxy: bool = False, include_all_formats: bool = True, proxy_url: Optional[str] = None) -> VideoMetadata:
    """Extract metadata from Twitter/X using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Get ALL formats with full details
        formats = []
        for fmt in info.get('formats', []):
            format_data = {
                'format_id': fmt.get('format_id'),
                'format_note': fmt.get('format_note'),
                'ext': fmt.get('ext'),
                'quality': fmt.get('quality_label') or fmt.get('format_note'),
                'width': fmt.get('width'),
                'height': fmt.get('height'),
                'fps': fmt.get('fps'),
                'url': fmt.get('url'),  # Direct download URL (expires!)
                'manifest_url': fmt.get('manifest_url'),
                'filesize': fmt.get('filesize'),
                'filesize_approx': fmt.get('filesize_approx'),
                'vcodec': fmt.get('vcodec'),
                'acodec': fmt.get('acodec'),
                'has_video': fmt.get('vcodec') != 'none',
                'has_audio': fmt.get('acodec') != 'none',
            }
            formats.append(format_data)
        
        # Sort by quality (height) descending
        formats.sort(key=lambda x: (x.get('height') or 0, x.get('width') or 0), reverse=True)
        
        # Twitter/X specific fields
        timestamp = info.get('timestamp')
        upload_date = None
        if timestamp:
            from datetime import datetime
            upload_date = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
        
        return VideoMetadata(
            platform='twitter',
            url=url,
            title=info.get('title') or info.get('description', '').split('\n')[0][:100] if info.get('description') else None,
            description=info.get('description'),
            duration=info.get('duration'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            upload_date=upload_date or info.get('upload_date'),
            uploader=info.get('uploader'),
            channel_id=info.get('uploader_id'),
            channel_url=info.get('uploader_url'),
            thumbnail=info.get('thumbnail'),
            thumbnails=info.get('thumbnails'),
            video_id=info.get('id'),
            formats=formats,
            subtitles=info.get('subtitles'),
            tags=info.get('tags', []),
            categories=None,
            age_limit=info.get('age_limit'),
            availability=info.get('availability'),
            live_status=None,
            raw_metadata={
                'webpage_url': info.get('webpage_url'),
                'original_url': info.get('original_url'),
                'extractor': info.get('extractor'),
                'extractor_key': info.get('extractor_key'),
                'repost_count': info.get('repost_count'),
                'quote_count': info.get('quote_count'),
            }
        )


def extract_twitter_comments(url: str, use_proxy: bool = False, max_comments: int = 50, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from a Twitter/X post using Playwright browser automation
    
    This uses headless browser to navigate to the tweet and extract replies.
    Note: This is fragile and may break if Twitter changes their UI.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    from datetime import datetime
    import time
    import re
    
    comments_list = []
    video_title = None
    tweet_id = None
    
    def log(msg, level="info"):
        try:
            from apify import Actor
            if level == "error":
                Actor.log.error(msg)
            elif level == "warning":
                Actor.log.warning(msg)
            else:
                Actor.log.info(msg)
        except:
            print(f"[{level.upper()}] {msg}")
    
    try:
        log(f"Starting Twitter comments extraction for: {url}")

        with sync_playwright() as p:
            # Launch browser with specific args to avoid detection
            launch_opts = {
                'headless': True,
                'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox']
            }

            if proxy_url:
                from urllib.parse import urlparse
                parsed = urlparse(proxy_url)
                proxy_config = {'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}'}
                if parsed.username:
                    proxy_config['username'] = parsed.username
                if parsed.password:
                    proxy_config['password'] = parsed.password
                launch_opts['proxy'] = proxy_config

            browser = p.chromium.launch(**launch_opts)
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Set extra headers to look more like a real browser
            context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            
            page = context.new_page()
            
            # Extract tweet ID from URL
            tweet_id = url.split('/status/')[-1].split('?')[0]
            log(f"Tweet ID: {tweet_id}")
            
            # Navigate to tweet
            log("Navigating to tweet...")
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for content to load - try multiple selectors
            log("Waiting for tweet to load...")
            loaded = False
            
            # Try different selectors for the main tweet
            selectors = [
                'article[data-testid="tweet"]',
                '[data-testid="tweet"]',
                'article[role="article"]',
                'article'
            ]
            
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    log(f"Found tweet using selector: {selector}")
                    loaded = True
                    break
                except PlaywrightTimeout:
                    continue
            
            if not loaded:
                log("Could not find tweet with standard selectors, waiting for any article...")
                page.wait_for_selector('article', timeout=10000)
            
            # Give extra time for JavaScript to render
            time.sleep(3)

            # Dismiss login modal if it appears
            try:
                close_btn = page.locator('[data-testid="xMigrationBottomBar"] button, [role="button"]:has-text("Not now"), button[aria-label="Close"]').first
                if close_btn.count() > 0:
                    close_btn.click()
                    time.sleep(1)
            except:
                pass

            # Extract tweet text
            try:
                # Try multiple selectors for tweet text
                text_selectors = [
                    'article[data-testid="tweet"] div[data-testid="tweetText"]',
                    '[data-testid="tweetText"]',
                    'article div[lang]'
                ]
                
                for selector in text_selectors:
                    try:
                        elem = page.locator(selector).first
                        if elem.count() > 0:
                            text = elem.text_content()
                            if text:
                                video_title = text[:200]
                                log(f"Found tweet text: {video_title[:50]}...")
                                break
                    except:
                        continue
            except Exception as e:
                log(f"Could not extract tweet text: {e}", "warning")
            
            # Scroll down to load replies
            log("Scrolling to load replies...")
            deadline = time.time() + 30
            prev_count = 0
            stale_rounds = 0

            for _ in range(15):
                if time.time() > deadline:
                    log("Hit scroll timeout")
                    break
                current_articles = page.locator('article').count()
                if current_articles > max_comments + 1:  # +1 for the main tweet
                    break
                if current_articles == prev_count:
                    stale_rounds += 1
                    if stale_rounds >= 3:
                        log("No new replies loading, stopping scroll")
                        break
                else:
                    stale_rounds = 0
                prev_count = current_articles
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)

            time.sleep(1)
            
            # Extract replies
            log("Extracting replies...")
            
            # Find all reply articles (they have a specific structure)
            # Replies are typically in articles after the first one
            articles = page.locator('article').all()
            log(f"Found {len(articles)} articles on page")
            
            # Skip the first article (it's the main tweet)
            reply_articles = articles[1:] if len(articles) > 1 else []
            
            for idx, article in enumerate(reply_articles[:max_comments]):
                try:
                    # Check if this is actually a reply (not a "Show more" or ad)
                    try:
                        # Try to find the user link
                        user_link = article.locator('a[href^="/"]').first
                        if user_link.count() == 0:
                            continue
                        
                        href = user_link.get_attribute('href')
                        if not href or href.startswith('/i/'):
                            # Skip ads, topics, etc.
                            continue
                        
                        author_id = href.strip('/').split('/')[0]
                    except:
                        continue
                    
                    # Extract author display name
                    try:
                        author_elem = article.locator('a[role="link"] span span').first
                        author = author_elem.text_content() if author_elem.count() > 0 else author_id
                    except:
                        author = author_id
                    
                    # Extract text
                    text = ""
                    try:
                        text_elem = article.locator('[data-testid="tweetText"]').first
                        if text_elem.count() > 0:
                            text = text_elem.text_content() or ""
                    except:
                        pass
                    
                    # Skip if no text
                    if not text.strip():
                        continue
                    
                    # Extract likes
                    like_count = 0
                    try:
                        # Look for the like button and its aria-label
                        like_btn = article.locator('button[data-testid="like"]').first
                        if like_btn.count() > 0:
                            aria = like_btn.get_attribute('aria-label') or ""
                            match = re.search(r'(\d+[,.]?\d*)', aria.replace(',', ''))
                            if match:
                                like_count = int(float(match.group(1).replace(',', '')))
                    except:
                        pass
                    
                    # Extract timestamp
                    timestamp = None
                    try:
                        time_elem = article.locator('time').first
                        if time_elem.count() > 0:
                            datetime_str = time_elem.get_attribute('datetime')
                            if datetime_str:
                                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                                timestamp = int(dt.timestamp())
                    except:
                        pass
                    
                    comment = Comment(
                        author=author,
                        author_id=author_id,
                        text=text,
                        like_count=like_count,
                        timestamp=timestamp,
                        reply_count=0
                    )
                    comments_list.append(comment)
                    log(f"Extracted comment {len(comments_list)}: @{author_id}")
                    
                    if len(comments_list) >= max_comments:
                        break
                        
                except Exception as e:
                    log(f"Error extracting reply {idx}: {e}", "warning")
                    continue
            
            browser.close()
            log(f"Successfully extracted {len(comments_list)} comments")
        
        return CommentsResponse(
            success=True,
            video_id=tweet_id,
            video_title=video_title,
            total_comments=len(comments_list),
            comments=comments_list,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        log(f"Twitter extraction failed: {e}", "error")
        return CommentsResponse(
            success=False,
            video_id=tweet_id,
            video_title=video_title,
            total_comments=0,
            comments=[],
            error=f"Twitter extraction failed: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )


def extract_instagram_metadata(url: str, cookies_file: Optional[str] = None, use_proxy: bool = False, include_all_formats: bool = True, proxy_url: Optional[str] = None) -> VideoMetadata:
    """Extract metadata from Instagram using yt-dlp with enhanced error handling"""
    import re
    
    # Chrome User-Agent that matches typical browser cookie exports
    CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'user_agent': CHROME_UA,
        'referer': 'https://www.instagram.com/',
    }
    
    # Instagram REQUIRES cookies for most content
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
    
    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get ALL formats with full details
            formats = []
            for fmt in info.get('formats', []):
                format_data = {
                    'format_id': fmt.get('format_id'),
                    'format_note': fmt.get('format_note'),
                    'ext': fmt.get('ext'),
                    'quality': fmt.get('quality_label') or fmt.get('format_note'),
                    'width': fmt.get('width'),
                    'height': fmt.get('height'),
                    'fps': fmt.get('fps'),
                    'url': fmt.get('url'),  # Direct download URL (expires!)
                    'manifest_url': fmt.get('manifest_url'),
                    'filesize': fmt.get('filesize'),
                    'filesize_approx': fmt.get('filesize_approx'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec'),
                    'has_video': fmt.get('vcodec') != 'none',
                    'has_audio': fmt.get('acodec') != 'none',
                }
                formats.append(format_data)
            
            # Sort by quality (height) descending
            formats.sort(key=lambda x: (x.get('height') or 0, x.get('width') or 0), reverse=True)
            
            # Parse timestamp to upload_date
            timestamp = info.get('timestamp')
            upload_date = None
            if timestamp:
                from datetime import datetime
                upload_date = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
            
            # Instagram-specific fields
            return VideoMetadata(
                platform='instagram',
                url=url,
                title=info.get('title') or info.get('description', '').split('\n')[0][:100] if info.get('description') else None,
                description=info.get('description'),
                duration=info.get('duration'),
                view_count=info.get('view_count'),
                like_count=info.get('like_count'),
                comment_count=info.get('comment_count'),
                upload_date=upload_date or info.get('upload_date'),
                uploader=info.get('uploader') or info.get('creator'),
                channel_id=info.get('uploader_id') or info.get('creator_id'),
                channel_url=info.get('uploader_url') or info.get('creator_url'),
                thumbnail=info.get('thumbnail'),
                thumbnails=info.get('thumbnails'),
                video_id=info.get('id'),
                formats=formats,
                subtitles=info.get('subtitles'),
                tags=info.get('tags', []),
                categories=None,
                age_limit=info.get('age_limit'),
                availability=info.get('availability'),
                live_status='is_live' if info.get('is_live') else None,
                raw_metadata={
                    'webpage_url': info.get('webpage_url'),
                    'original_url': info.get('original_url'),
                    'extractor': info.get('extractor'),
                    'extractor_key': info.get('extractor_key'),
                    'post_type': info.get('post_type'),  # post, reel, story, etc.
                }
            )
    except Exception as e:
        error_msg = str(e)
        
        # Provide detailed error messages for common issues
        if "empty media response" in error_msg.lower():
            raise Exception(
                "Instagram returned empty media response. This usually means:\n"
                "1. The cookies are expired or invalid (most common cause)\n"
                "2. Instagram requires fresh authentication\n"
                "3. The post may be private, deleted, or age-restricted\n\n"
                "HOW TO FIX:\n"
                "1. Log into Instagram in Chrome/Firefox on your local machine\n"
                "2. Install 'Get cookies.txt LOCALLY' browser extension\n"
                "3. Export cookies for instagram.com\n"
                "4. Copy the contents to instagram_cookies.txt in this workspace\n"
                "5. Make sure the cookies include: sessionid, csrftoken, ds_user_id"
            )
        elif "400" in error_msg and "bad request" in error_msg.lower():
            raise Exception(
                "Instagram rejected the cookies (HTTP 400 Bad Request).\n"
                "This indicates the cookies were rejected - they may be:\n"
                "- Expired\n"
                "- From a different IP address\n"
                "- From a different browser/user-agent\n\n"
                "HOW TO FIX:\n"
                "Export fresh cookies immediately after logging into Instagram.\n"
                "Cookies are tied to your session and can become invalid quickly."
            )
        elif "403" in error_msg:
            raise Exception(
                "Instagram denied access (HTTP 403 Forbidden).\n"
                "The session may have been flagged or the cookies are invalid.\n\n"
                "HOW TO FIX:\n"
                "1. Log out and log back into Instagram in your browser\n"
                "2. Export fresh cookies immediately\n"
                "3. If using a proxy, try disabling it (proxies can trigger blocks)"
            )
        elif "login" in error_msg.lower():
            raise Exception(
                "Instagram requires authentication.\n"
                "Please provide valid cookies from a logged-in session.\n\n"
                "HOW TO FIX:\n"
                "Export cookies using 'Get cookies.txt LOCALLY' extension after logging in."
            )
        else:
            raise


def extract_instagram_comments(url: str, cookies_file: Optional[str] = None, use_proxy: bool = False, max_comments: int = 50, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from an Instagram post/reel with enhanced error handling"""
    CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'getcomments': True,
        'max_comments': [max_comments, max_comments, max_comments, max_comments],
        'user_agent': CHROME_UA,
        'referer': 'https://www.instagram.com/',
    }
    
    # Instagram REQUIRES cookies
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
    
    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            comments_list = []
            raw_comments = info.get('comments', []) or []
            
            for comment_data in raw_comments[:max_comments]:
                comment = Comment(
                    author=comment_data.get('author'),
                    author_id=comment_data.get('author_id'),
                    text=comment_data.get('text'),
                    like_count=comment_data.get('like_count'),
                    timestamp=comment_data.get('timestamp'),
                    reply_count=len(comment_data.get('replies', [])) if comment_data.get('replies') else 0
                )
                comments_list.append(comment)
            
            return CommentsResponse(
                success=True,
                video_id=info.get('id'),
                video_title=info.get('title') or (info.get('description', '').split('\n')[0][:100] if info.get('description') else None),
                total_comments=info.get('comment_count'),
                comments=comments_list,
                timestamp=datetime.utcnow().isoformat()
            )
    except Exception as e:
        error_msg = str(e)
        if "empty media response" in error_msg.lower() or "400" in error_msg or "403" in error_msg:
            raise Exception(
                "Failed to fetch Instagram comments. "
                "Please ensure you have valid, fresh cookies from a logged-in Instagram session."
            )
        raise


def extract_tiktok_metadata(url: str, use_proxy: bool = False, include_all_formats: bool = True, proxy_url: Optional[str] = None) -> VideoMetadata:
    """Extract metadata from TikTok using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Get ALL formats with full details
        formats = []
        for fmt in info.get('formats', []):
            format_data = {
                'format_id': fmt.get('format_id'),
                'format_note': fmt.get('format_note'),
                'ext': fmt.get('ext'),
                'quality': fmt.get('quality_label') or fmt.get('format_note'),
                'width': fmt.get('width'),
                'height': fmt.get('height'),
                'fps': fmt.get('fps'),
                'url': fmt.get('url'),  # Direct download URL (expires!)
                'manifest_url': fmt.get('manifest_url'),
                'filesize': fmt.get('filesize'),
                'filesize_approx': fmt.get('filesize_approx'),
                'vcodec': fmt.get('vcodec'),
                'acodec': fmt.get('acodec'),
                'has_video': fmt.get('vcodec') != 'none',
                'has_audio': fmt.get('acodec') != 'none',
            }
            formats.append(format_data)
        
        # Sort by quality (height) descending
        formats.sort(key=lambda x: (x.get('height') or 0, x.get('width') or 0), reverse=True)
        
        # TikTok specific fields
        timestamp = info.get('timestamp')
        upload_date = None
        if timestamp:
            # Convert Unix timestamp to YYYYMMDD format
            from datetime import datetime
            upload_date = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
        
        return VideoMetadata(
            platform='tiktok',
            url=url,
            title=info.get('title') or info.get('description', '').split('\n')[0][:100],
            description=info.get('description'),
            duration=info.get('duration'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            upload_date=upload_date or info.get('upload_date'),
            uploader=info.get('uploader') or info.get('creator'),
            channel_id=info.get('uploader_id') or info.get('creator_id'),
            channel_url=info.get('uploader_url') or info.get('creator_url'),
            thumbnail=info.get('thumbnail'),
            thumbnails=info.get('thumbnails'),
            video_id=info.get('id'),
            formats=formats,
            subtitles=info.get('subtitles'),
            tags=info.get('tags', []),
            categories=None,  # TikTok doesn't have categories
            age_limit=info.get('age_limit'),
            availability=info.get('availability'),
            live_status='is_live' if info.get('is_live') else None,
            raw_metadata={
                'webpage_url': info.get('webpage_url'),
                'original_url': info.get('original_url'),
                'extractor': info.get('extractor'),
                'extractor_key': info.get('extractor_key'),
                'track': info.get('track'),
                'artist': info.get('artist'),
                'album': info.get('album'),
            }
        )


def extract_tiktok_comments(url: str, use_proxy: bool = False, max_comments: int = 100, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from a TikTok video using TikTokApi
    
    Note: yt-dlp's _get_comments is not implemented for TikTok (raises NotImplementedError),
    so we use TikTokApi which uses browser automation to fetch comments.
    """
    import asyncio
    from TikTokApi import TikTokApi
    
    async def _fetch_comments():
        comments_list = []
        video_title = None
        video_id = None
        total_comments = None
        
        async with TikTokApi() as api:
            # Create session with headless browser
            await api.create_sessions(headless=True, ms_tokens=[''], num_sessions=1)
            
            video = api.video(url=url)
            
            # Get video info for title
            try:
                info = await video.info()
                video_title = info.get('desc', '')[:100] if info else None
                video_id = info.get('id') if info else None
                total_comments = info.get('commentCount') if info else None
            except Exception as e:
                print(f"Warning: Could not get video info: {e}")
            
            # Fetch comments
            count = 0
            async for comment in video.comments(count=max_comments):
                comment_dict = comment.as_dict
                
                # Extract author info from nested structure
                author = comment_dict.get('user', {}).get('nickname') or comment_dict.get('user', {}).get('uniqueId')
                author_id = comment_dict.get('user', {}).get('uniqueId') or comment_dict.get('user', {}).get('secUid')
                
                # Extract other fields
                text = comment_dict.get('text', '')
                like_count = comment_dict.get('diggCount', 0)
                timestamp = comment_dict.get('createTime')
                reply_count = comment_dict.get('replyCommentTotal', 0)
                
                comment_obj = Comment(
                    author=author,
                    author_id=author_id,
                    text=text,
                    like_count=like_count,
                    timestamp=timestamp,
                    reply_count=reply_count
                )
                comments_list.append(comment_obj)
                count += 1
                
                if count >= max_comments:
                    break
        
        return comments_list, video_title, video_id, total_comments
    
    # Run the async function
    try:
        comments_list, video_title, video_id, total_comments = asyncio.run(_fetch_comments())
        
        return CommentsResponse(
            success=True,
            video_id=video_id,
            video_title=video_title,
            total_comments=total_comments or len(comments_list),
            comments=comments_list,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        # Return error response
        return CommentsResponse(
            success=False,
            video_id=None,
            video_title=None,
            total_comments=0,
            comments=[],
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


def extract_youtube_metadata(url: str, cookies_file: Optional[str] = None, use_proxy: bool = False, include_all_formats: bool = True, proxy_url: Optional[str] = None) -> VideoMetadata:
    """Extract metadata from YouTube using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'writesubtitles': True,
        'writeautomaticsub': True,
    }
    
    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    
    # Add cookies only if NOT using proxy (Android client doesn't support cookies)
    if cookies_file and os.path.exists(cookies_file) and not proxy_url and not use_proxy:
        ydl_opts['cookiefile'] = cookies_file
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Get ALL formats with full details
        formats = []
        for fmt in info.get('formats', []):
            format_data = {
                'format_id': fmt.get('format_id'),
                'format_note': fmt.get('format_note'),
                'ext': fmt.get('ext'),
                'quality': fmt.get('quality_label') or fmt.get('format_note'),
                'width': fmt.get('width'),
                'height': fmt.get('height'),
                'fps': fmt.get('fps'),
                'url': fmt.get('url'),  # Direct download URL (expires!)
                'manifest_url': fmt.get('manifest_url'),
                'filesize': fmt.get('filesize'),
                'filesize_approx': fmt.get('filesize_approx'),
                'vcodec': fmt.get('vcodec'),
                'acodec': fmt.get('acodec'),
                'abr': fmt.get('abr'),  # Audio bitrate
                'vbr': fmt.get('vbr'),  # Video bitrate
                'asr': fmt.get('asr'),  # Audio sample rate
                'audio_channels': fmt.get('audio_channels'),
                'has_video': fmt.get('vcodec') != 'none',
                'has_audio': fmt.get('acodec') != 'none',
            }
            formats.append(format_data)
        
        # Sort by quality (height) descending
        formats.sort(key=lambda x: (x.get('height') or 0, x.get('width') or 0), reverse=True)
        
        # Limit formats if not including all
        if not include_all_formats:
            # Keep top 5 video+audio, top 5 video-only, top 5 audio-only
            video_audio = [f for f in formats if f['has_video'] and f['has_audio']][:5]
            video_only = [f for f in formats if f['has_video'] and not f['has_audio']][:5]
            audio_only = [f for f in formats if not f['has_video'] and f['has_audio']][:5]
            formats = video_audio + video_only + audio_only
        
        return VideoMetadata(
            platform='youtube',
            url=url,
            title=info.get('title'),
            description=info.get('description'),
            duration=info.get('duration'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            upload_date=info.get('upload_date'),
            uploader=info.get('uploader'),
            channel_id=info.get('channel_id'),
            channel_url=info.get('channel_url'),
            thumbnail=info.get('thumbnail'),
            thumbnails=info.get('thumbnails'),
            video_id=info.get('id'),
            formats=formats,
            subtitles=info.get('subtitles'),
            tags=info.get('tags'),
            categories=info.get('categories'),
            age_limit=info.get('age_limit'),
            availability=info.get('availability'),
            live_status=info.get('live_status'),
            raw_metadata={
                'webpage_url': info.get('webpage_url'),
                'original_url': info.get('original_url'),
                'webpage_url_basename': info.get('webpage_url_basename'),
                'webpage_url_domain': info.get('webpage_url_domain'),
                'extractor': info.get('extractor'),
                'extractor_key': info.get('extractor_key'),
            }
        )


def extract_youtube_comments(url: str, use_proxy: bool = False, max_comments: int = 100, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from a YouTube video"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'getcomments': True,
        'max_comments': [max_comments, max_comments, max_comments, max_comments],  # [top, newest, replies, all]
    }

    # Add proxy if provided or requested
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    elif use_proxy:
        proxy = get_proxy(use_scrapeops=True)
        if proxy:
            ydl_opts['proxy'] = proxy
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        comments_list = []
        raw_comments = info.get('comments', []) or []

        for comment_data in raw_comments[:max_comments]:
            comment = Comment(
                author=comment_data.get('author'),
                author_id=comment_data.get('author_id'),
                text=comment_data.get('text'),
                like_count=comment_data.get('like_count'),
                timestamp=comment_data.get('timestamp'),
                reply_count=len(comment_data.get('replies', [])) if comment_data.get('replies') else 0
            )
            comments_list.append(comment)

        return CommentsResponse(
            success=True,
            video_id=info.get('id'),
            video_title=info.get('title'),
            total_comments=info.get('comment_count'),
            comments=comments_list,
            timestamp=datetime.utcnow().isoformat()
        )


@app.get("/")
def root():
    cookies_status = "✅ Found" if os.path.exists("youtube_cookies.txt") else "❌ Not found"
    ig_cookies_status = "✅ Found" if os.path.exists("instagram_cookies.txt") else "❌ Not found"
    proxy_status = f"✅ {len(PROXIES)} proxies loaded" if PROXIES else "❌ No proxies"
    return {
        "message": "Video Metadata Extraction API",
        "version": "1.0.0",
        "cookies": {
            "youtube": cookies_status,
            "instagram": ig_cookies_status,
            "help": "Export from browser and save as youtube_cookies.txt / instagram_cookies.txt"
        },
        "proxies": {
            "status": proxy_status,
            "count": len(PROXIES)
        },
        "endpoints": {
            "youtube": "/extract/youtube",
            "youtube_comments": "/extract/youtube/comments",
            "tiktok": "/extract/tiktok",
            "tiktok_comments": "/extract/tiktok/comments",
            "instagram": "/extract/instagram",
            "instagram_comments": "/extract/instagram/comments",
            "twitter": "/extract/twitter",
            "twitter_comments": "/extract/twitter/comments",
            "stream": "/stream (NEW - proxy videos through API)",
            "auto": "/extract/auto"
        }
    }


@app.post("/extract/youtube", response_model=ExtractionResponse)
def extract_youtube(request: YouTubeRequest):
    """Extract metadata from a YouTube video URL
    
    Set `include_all_formats: true` to get all video formats with direct URLs.
    Direct URLs expire after a few hours!
    """
    try:
        metadata = extract_youtube_metadata(
            str(request.url), 
            request.cookies_file,
            request.use_proxy,
            request.include_all_formats
        )
        return ExtractionResponse(
            success=True,
            data=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return ExtractionResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/tiktok", response_model=ExtractionResponse)
def extract_tiktok(request: TikTokRequest):
    """Extract metadata from a TikTok video URL
    
    Set `include_all_formats: true` to get all video formats with direct URLs.
    Direct URLs expire after a few hours!
    
    Note: TikTok REQUIRES a residential proxy for reliable extraction.
    """
    try:
        metadata = extract_tiktok_metadata(
            str(request.url),
            request.use_proxy,
            request.include_all_formats
        )
        return ExtractionResponse(
            success=True,
            data=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return ExtractionResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/tiktok/comments", response_model=CommentsResponse)
def extract_tiktok_comments_endpoint(request: TikTokCommentsRequest):
    """Extract comments from a TikTok video
    
    Fetches actual comment text, author, likes, replies, etc.
    Set `max_comments` to limit results (default: 100)
    
    Note: Uses TikTokApi with browser automation since yt-dlp doesn't implement
    TikTok comment extraction (_get_comments raises NotImplementedError).
    """
    try:
        return extract_tiktok_comments(
            str(request.url),
            request.use_proxy,
            request.max_comments
        )
    except Exception as e:
        return CommentsResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/instagram", response_model=ExtractionResponse)
def extract_instagram(request: InstagramRequest):
    """Extract metadata from an Instagram post/reel
    
    Set `include_all_formats: true` to get all video formats with direct URLs.
    Direct URLs expire after a few hours!
    
    Note: Instagram REQUIRES authentication cookies for most content.
    Export cookies from your browser after logging into Instagram.
    """
    try:
        # Check if Instagram cookies exist
        if not os.path.exists(request.cookies_file):
            return ExtractionResponse(
                success=False,
                error=f"Instagram cookies required. Please export cookies from your browser after logging into Instagram and save as '{request.cookies_file}'. Use 'Get cookies.txt LOCALLY' Chrome extension.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        metadata = extract_instagram_metadata(
            str(request.url),
            request.cookies_file,
            request.use_proxy,
            request.include_all_formats
        )
        return ExtractionResponse(
            success=True,
            data=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "cookie" in error_msg.lower():
            error_msg = "Instagram requires valid login cookies. Please export fresh cookies from your browser after logging into Instagram."
        return ExtractionResponse(
            success=False,
            error=error_msg,
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/instagram/comments", response_model=CommentsResponse)
def extract_instagram_comments_endpoint(request: InstagramCommentsRequest):
    """Extract comments from an Instagram post/reel
    
    Fetches actual comment text, author, likes, etc.
    Set `max_comments` to limit results (default: 50)
    
    Note: Instagram REQUIRES authentication cookies.
    """
    try:
        # Check if Instagram cookies exist
        if not os.path.exists(request.cookies_file):
            return CommentsResponse(
                success=False,
                error=f"Instagram cookies required. Please export cookies from your browser after logging into Instagram and save as '{request.cookies_file}'.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        return extract_instagram_comments(
            str(request.url),
            request.cookies_file,
            request.use_proxy,
            request.max_comments
        )
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "cookie" in error_msg.lower():
            error_msg = "Instagram requires valid login cookies. Please export fresh cookies from your browser after logging into Instagram."
        return CommentsResponse(
            success=False,
            error=error_msg,
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/twitter", response_model=ExtractionResponse)
def extract_twitter(request: TwitterRequest):
    """Extract metadata from a Twitter/X video post
    
    Set `include_all_formats: true` to get all video formats with direct URLs.
    Direct URLs expire after a few hours!
    
    Supports twitter.com and x.com URLs.
    """
    try:
        metadata = extract_twitter_metadata(
            str(request.url),
            request.use_proxy,
            request.include_all_formats
        )
        return ExtractionResponse(
            success=True,
            data=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        error_msg = str(e)
        if "No video could be found" in error_msg:
            error_msg = "No video found in this tweet. The tweet may not contain a video, or the video may be restricted."
        return ExtractionResponse(
            success=False,
            error=error_msg,
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/twitter/comments", response_model=CommentsResponse)
def extract_twitter_comments_endpoint(request: TwitterCommentsRequest):
    """Extract comments from a Twitter/X post
    
    Fetches actual comment/reply text, author, likes, etc.
    Set `max_comments` to limit results (default: 50)
    
    Note: Twitter/X API limits may apply.
    """
    try:
        return extract_twitter_comments(
            str(request.url),
            request.use_proxy,
            request.max_comments
        )
    except Exception as e:
        return CommentsResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/extract/youtube/comments", response_model=CommentsResponse)
class StreamRequest(BaseModel):
    url: HttpUrl
    platform: str = Field(default="youtube", description="Platform: youtube, tiktok, twitter")
    quality: Optional[str] = Field(default="best", description="Video quality: best, worst, or format_id")
    use_proxy: Optional[bool] = Field(default=False, description="Use proxy for extraction")


def stream_video_generator(url: str, platform: str, quality: str, use_proxy: bool):
    """Generator function to stream video content"""
    ydl_opts = {
        'quiet': True,
        'format': quality if quality in ['best', 'worst'] else quality,
    }
    
    # Add proxy if requested
    if use_proxy:
        proxy_url = get_proxy(use_scrapeops=True)
        if proxy_url:
            ydl_opts['proxy'] = proxy_url
            if platform == 'youtube':
                ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    
    # Platform-specific options
    if platform == 'instagram':
        if os.path.exists('instagram_cookies.txt'):
            ydl_opts['cookiefile'] = 'instagram_cookies.txt'
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = info['url'] if 'url' in info else info['formats'][0]['url']
        
        # Stream the content with browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'Range': 'bytes=0-',
            'Referer': 'https://www.tiktok.com/' if platform == 'tiktok' else 'https://www.youtube.com/' if platform == 'youtube' else 'https://twitter.com/' if platform == 'twitter' else 'https://www.instagram.com/',
            'Origin': 'https://www.tiktok.com' if platform == 'tiktok' else 'https://www.youtube.com' if platform == 'youtube' else 'https://twitter.com' if platform == 'twitter' else 'https://www.instagram.com',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        
        # Add cookies if available
        cookies = None
        if platform == 'instagram' and os.path.exists('instagram_cookies.txt'):
            # Load cookies from file
            import http.cookiejar
            cookies = http.cookiejar.MozillaCookieJar('instagram_cookies.txt')
            cookies.load()
        
        session = requests.Session()
        if cookies:
            session.cookies = cookies
            
        with session.get(video_url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk


@app.post("/stream")
def stream_video(request: StreamRequest):
    """Stream video directly through the API
    
    This solves the YouTube IP-lock issue by proxying the video through the server.
    The video is streamed from the source through this API to the client.
    
    Usage:
    - POST /stream with {"url": "https://youtube.com/watch?v=...", "platform": "youtube"}
    - Returns video stream that can be played directly
    
    Supported platforms: youtube, tiktok, twitter, instagram
    """
    try:
        # Get video info first to determine content type
        ydl_opts = {'quiet': True}
        if request.use_proxy:
            proxy_url = get_proxy(use_scrapeops=True)
            if proxy_url:
                ydl_opts['proxy'] = proxy_url
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(str(request.url), download=False)
            ext = info.get('ext', 'mp4')
            
        return StreamingResponse(
            stream_video_generator(
                str(request.url),
                request.platform,
                request.quality,
                request.use_proxy
            ),
            media_type=f"video/{ext}",
            headers={
                "Content-Disposition": f"inline; filename=video.{ext}",
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Apify Actor Entry Point
async def apify_main():
    """Main entry point for Apify Actor
    
    Uses Apify's built-in proxy for reliable extraction.
    Can download videos to Apify's key-value store.
    """
    try:
        from apify import Actor
    except ImportError:
        print("Apify not installed. Install with: pip install apify")
        return
    
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get("url")
        extract_comments = actor_input.get("extractComments", False)
        use_proxy = actor_input.get("useProxy", True)
        max_comments = actor_input.get("maxComments", 50)
        download_video = actor_input.get("downloadVideo", False)
        
        if not url:
            Actor.log.error("No URL provided. Please provide a video URL.")
            return
            return
        
        Actor.log.info(f"Processing URL: {url}")
        
        try:
            # Determine platform
            platform = "youtube"
            url_lower = url.lower()
            if "tiktok" in url_lower:
                platform = "tiktok"
            elif "twitter" in url_lower or "x.com" in url_lower:
                platform = "twitter"
            elif "instagram" in url_lower:
                platform = "instagram"
            
            Actor.log.info(f"Detected platform: {platform}")
            
            # Build proxy configuration for yt-dlp
            proxy_url = None
            if use_proxy:
                # Use Apify's built-in proxy
                proxy_configuration = await Actor.create_proxy_configuration(
                    groups=['RESIDENTIAL'],  # Use residential proxy
                    country_code='US'  # Optional: specify country
                )
                if proxy_configuration:
                    # Get a new proxy URL from the configuration
                    proxy_url = await proxy_configuration.new_url()
                    Actor.log.info("Using Apify residential proxy")
            
            # Extract video metadata
            if platform == "youtube":
                metadata = await asyncio.to_thread(
                    extract_youtube_metadata, 
                    url, 
                    None, 
                    proxy_url is not None,  # use_proxy flag
                    True,  # include_all_formats
                    proxy_url  # actual proxy URL
                )
                result = metadata.dict()
                if extract_comments:
                    Actor.log.info("Extracting comments...")
                    comments_resp = await asyncio.to_thread(
                        extract_youtube_comments,
                        url,
                        use_proxy,
                        max_comments
                    )
                    result["comments"] = comments_resp.comments
                    result["comments_extracted"] = len(comments_resp.comments)
                    
            elif platform == "tiktok":
                metadata = await asyncio.to_thread(
                    extract_tiktok_metadata, 
                    url, 
                    proxy_url is not None, 
                    True,
                    proxy_url
                )
                result = metadata.dict()
                if extract_comments:
                    Actor.log.info("Extracting comments...")
                    comments_resp = await asyncio.to_thread(
                        extract_tiktok_comments, 
                        url, 
                        proxy_url is not None,
                        max_comments,
                        proxy_url
                    )
                    result["comments"] = comments_resp.comments
                    result["comments_extracted"] = len(comments_resp.comments)
                    
            elif platform == "twitter":
                metadata = await asyncio.to_thread(
                    extract_twitter_metadata, 
                    url, 
                    proxy_url is not None, 
                    True,
                    proxy_url
                )
                result = metadata.dict()
                if extract_comments:
                    Actor.log.info("Extracting comments...")
                    comments_resp = await asyncio.to_thread(
                        extract_twitter_comments,
                        url,
                        proxy_url is not None,
                        max_comments,
                        proxy_url
                    )
                    result["comments"] = comments_resp.comments
                    result["comments_extracted"] = len(comments_resp.comments)
                    
            else:  # instagram
                metadata = await asyncio.to_thread(
                    extract_instagram_metadata, 
                    url, 
                    "instagram_cookies.txt", 
                    proxy_url is not None, 
                    True,
                    proxy_url
                )
                result = metadata.dict()
                if extract_comments:
                    Actor.log.info("Extracting comments...")
                    comments_resp = await asyncio.to_thread(
                        extract_instagram_comments, 
                        url, 
                        "instagram_cookies.txt",
                        proxy_url is not None,
                        max_comments,
                        proxy_url
                    )
                    result["comments"] = comments_resp.comments
                    result["comments_extracted"] = len(comments_resp.comments)
            
            # Download video if requested
            if download_video:
                Actor.log.info("Downloading video...")
                try:
                    video_url, video_error = await download_video_to_store(
                        url, 
                        platform, 
                        proxy_url,
                        Actor
                    )
                    if video_url:
                        result["video_download_url"] = video_url
                        result["video_stored"] = True
                        result["video_error"] = None
                    else:
                        result["video_stored"] = False
                        result["video_error"] = video_error or "Unknown error during download"
                except Exception as e:
                    Actor.log.error(f"Video download failed: {e}")
                    result["video_stored"] = False
                    result["video_error"] = str(e)
            
            # Add metadata
            result["platform"] = platform
            result["extracted_at"] = datetime.utcnow().isoformat()
            
            Actor.log.info(f"Successfully extracted data from {platform}")
            
            # Push to dataset
            await Actor.push_data(result)
            
        except Exception as e:
            Actor.log.error(f"Extraction failed: {str(e)}")
            Actor.log.error(f"Extraction failed: {str(e)}")
            raise  # Re-raise the exception to fail the actor


async def download_video_to_store(url: str, platform: str, proxy_url: Optional[str], Actor) -> tuple[Optional[str], Optional[str]]:
    """Download video to Apify's key-value store
    
    Returns:
        (public_url, error_message) - public_url is None if failed, error_message explains why
    """
    import tempfile
    import os
    
    try:
        ydl_opts = {
            'quiet': True,
            'format': 'best',
            'outtmpl': tempfile.gettempdir() + '/%(id)s.%(ext)s',
        }
        
        if proxy_url:
            ydl_opts['proxy'] = proxy_url

        if platform == 'youtube':
            if os.path.exists('youtube_cookies.txt'):
                # Use web client with cookies (android client doesn't support cookies)
                ydl_opts['cookiefile'] = 'youtube_cookies.txt'
                ydl_opts['extractor_args'] = {'youtube': {'player_client': ['web']}}
            else:
                ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

        if platform == 'instagram' and os.path.exists('instagram_cookies.txt'):
            ydl_opts['cookiefile'] = 'instagram_cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'video')
            ext = info.get('ext', 'mp4')
            
            # Find the downloaded file
            temp_path = os.path.join(tempfile.gettempdir(), f"{video_id}.{ext}")
            
            if not os.path.exists(temp_path):
                return None, f"Download failed: file not found at {temp_path}"
            
            # Check file size
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                os.remove(temp_path)
                return None, "Download failed: file is empty"
            
            Actor.log.info(f"Downloaded {file_size} bytes, uploading to storage...")
            
            # Upload to Apify's key-value store
            key = f"{platform}_{video_id}.{ext}"
            
            # Read file
            with open(temp_path, 'rb') as f:
                file_data = f.read()
            
            # Use Actor's set_value method (simpler API)
            await Actor.set_value(key, file_data, content_type=f'video/{ext}')
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Build the public URL manually
            # Format: https://api.apify.com/v2/key-value-stores/{storeId}/records/{key}
            store_id = os.environ.get('APIFY_DEFAULT_KEY_VALUE_STORE_ID', '')
            public_url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{key}"
            
            Actor.log.info(f"Video stored successfully: {public_url}")
            
            return public_url, None
            
    except Exception as e:
        error_msg = str(e)
        Actor.log.error(f"Video download failed: {error_msg}")
        return None, error_msg
    
    return None, "Unknown error"


if __name__ == "__main__":
    import sys
    # Check if running as Apify actor
    if os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_ACTOR_RUN_ID"):
        import asyncio
        asyncio.run(apify_main())
    else:
        # Run as standalone server
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
