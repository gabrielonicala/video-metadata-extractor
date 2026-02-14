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

def _get_follower_count(info: dict) -> Optional[int]:
    """Extract follower/subscriber count from yt-dlp info dict.

    Tries multiple field names since different platforms use different keys.
    Uses explicit None checks so a valid 0 value isn't skipped.
    """
    for key in ('channel_follower_count', 'uploader_follower_count', 'follower_count'):
        val = info.get(key)
        if val is not None:
            return val
    return None


def resolve_proxy(use_proxy: bool = False, proxy_url: Optional[str] = None) -> Optional[str]:
    """Resolve proxy URL - direct URL takes priority over use_proxy flag"""
    if proxy_url:
        return proxy_url
    if use_proxy:
        return get_proxy(use_scrapeops=True)
    return None

def apply_proxy(ydl_opts: dict, use_proxy: bool = False, proxy_url: Optional[str] = None) -> bool:
    """Apply proxy + timeout + retry settings to yt-dlp options. Returns True if proxy was applied."""
    resolved = resolve_proxy(use_proxy, proxy_url)
    if resolved:
        ydl_opts['proxy'] = resolved
        ydl_opts['socket_timeout'] = 60
        ydl_opts['retries'] = 3
        return True
    return False

def _playwright_proxy_config(proxy_url: str) -> dict:
    """Parse a proxy URL into Playwright's proxy config format."""
    from urllib.parse import urlparse
    parsed = urlparse(proxy_url)
    config = {'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}'}
    if parsed.username:
        config['username'] = parsed.username
    if parsed.password:
        config['password'] = parsed.password
    return config

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
    followers: Optional[int] = None
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

    apply_proxy(ydl_opts, use_proxy, proxy_url)
    
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
            followers=_get_follower_count(info),
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


def _twitter_comments_ydl(url: str, use_proxy: bool = False, max_comments: int = 50, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract Twitter comments via yt-dlp (may fail due to upstream bugs)."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'getcomments': True,
        'max_comments': [max_comments, max_comments, max_comments, max_comments],
    }

    apply_proxy(ydl_opts, use_proxy, proxy_url)

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

        if not comments_list:
            raise ValueError("yt-dlp returned no Twitter comments")

        return CommentsResponse(
            success=True,
            video_id=info.get('id'),
            video_title=info.get('title') or (info.get('description', '').split('\n')[0][:100] if info.get('description') else None),
            total_comments=info.get('comment_count'),
            comments=comments_list,
            timestamp=datetime.utcnow().isoformat()
        )


def _extract_tweets_from_graphql(data: Any, original_tweet_id: str, seen_ids: set) -> List[Comment]:
    """Walk a Twitter GraphQL response and pull out reply tweets."""
    comments: List[Comment] = []
    stack = [data]

    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            # Detect a Tweet node that is NOT the original tweet
            if (obj.get('__typename') in ('Tweet', 'TweetWithVisibilityResults')
                    and obj.get('rest_id')
                    and str(obj.get('rest_id')) != str(original_tweet_id)
                    and obj.get('rest_id') not in seen_ids):

                seen_ids.add(obj['rest_id'])
                legacy = obj.get('legacy', {})
                user_legacy = (obj.get('core', {})
                               .get('user_results', {})
                               .get('result', {})
                               .get('legacy', {}))
                text = legacy.get('full_text', '')
                if text:
                    comments.append(Comment(
                        author=user_legacy.get('name'),
                        author_id=user_legacy.get('screen_name'),
                        text=text,
                        like_count=legacy.get('favorite_count'),
                        timestamp=legacy.get('created_at'),
                        reply_count=legacy.get('reply_count', 0),
                    ))

            # Also handle TweetWithVisibilityResults wrapper
            if obj.get('__typename') == 'TweetWithVisibilityResults' and 'tweet' in obj:
                stack.append(obj['tweet'])
            else:
                stack.extend(obj.values())
        elif isinstance(obj, list):
            stack.extend(obj)

    return comments


def _twitter_comments_playwright(tweet_url: str, tweet_id: Optional[str], max_comments: int,
                                  proxy_url: Optional[str] = None) -> CommentsResponse:
    """Load a tweet page in Playwright and intercept GraphQL TweetDetail responses."""
    from playwright.sync_api import sync_playwright

    all_comments: List[Comment] = []
    seen_ids: set = set()

    with sync_playwright() as p:
        launch_kwargs: Dict[str, Any] = {'headless': True}
        if proxy_url:
            launch_kwargs['proxy'] = _playwright_proxy_config(proxy_url)

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        page = context.new_page()

        def on_response(response):
            try:
                if 'TweetDetail' in response.url and response.status == 200:
                    data = response.json()
                    new = _extract_tweets_from_graphql(data, tweet_id or '', seen_ids)
                    all_comments.extend(new)
            except Exception:
                pass

        page.on('response', on_response)

        try:
            page.goto(tweet_url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)

            # Scroll to load more replies
            scroll_attempts = min(10, max(1, max_comments // 10))
            for _ in range(scroll_attempts):
                if len(all_comments) >= max_comments:
                    break
                page.evaluate('window.scrollBy(0, 800)')
                page.wait_for_timeout(2000)
        except Exception:
            pass
        finally:
            browser.close()

    if not all_comments:
        raise ValueError("Playwright could not extract Twitter comments")

    return CommentsResponse(
        success=True, video_id=tweet_id, video_title=None,
        total_comments=len(all_comments),
        comments=all_comments[:max_comments],
        timestamp=datetime.utcnow().isoformat()
    )


def extract_twitter_comments(url: str, use_proxy: bool = False, max_comments: int = 50,
                              proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from a Twitter/X post.

    Strategy:
      1. Try yt-dlp (fast, may fail due to upstream bugs)
      2. Fall back to Playwright browser (intercept GraphQL responses)
    """
    import re

    errors = []
    tweet_id = None
    match = re.search(r'/status/(\d+)', url)
    if match:
        tweet_id = match.group(1)

    # Try yt-dlp first
    try:
        return _twitter_comments_ydl(url, use_proxy, max_comments, proxy_url)
    except Exception as e:
        errors.append(f"yt-dlp: {e}")

    # Fall back to Playwright
    try:
        return _twitter_comments_playwright(url, tweet_id, max_comments, proxy_url)
    except Exception as e:
        errors.append(f"Playwright: {e}")

    return CommentsResponse(
        success=False, video_id=tweet_id, video_title=None,
        total_comments=0, comments=[],
        error=f"All Twitter comment strategies failed: {'; '.join(errors)}",
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

    apply_proxy(ydl_opts, use_proxy, proxy_url)

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
                followers=_get_follower_count(info),
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

    apply_proxy(ydl_opts, use_proxy, proxy_url)

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

    apply_proxy(ydl_opts, use_proxy, proxy_url)

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
            followers=_get_follower_count(info),
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


def _tiktok_comments_playwright(video_url: str, video_id: str, max_comments: int,
                                 video_title: Optional[str], comment_count: Optional[int],
                                 proxy_url: Optional[str] = None) -> CommentsResponse:
    """Load TikTok video page in Playwright and intercept the comments API responses."""
    from playwright.sync_api import sync_playwright

    all_comments: List[Comment] = []
    seen_ids: set = set()

    with sync_playwright() as p:
        launch_kwargs: Dict[str, Any] = {'headless': True}
        if proxy_url:
            launch_kwargs['proxy'] = _playwright_proxy_config(proxy_url)

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        page = context.new_page()

        def on_response(response):
            try:
                if '/api/comment/list' in response.url and response.status == 200:
                    data = response.json()
                    for c in (data.get('comments') or []):
                        cid = str(c.get('cid', ''))
                        if cid and cid in seen_ids:
                            continue
                        if cid:
                            seen_ids.add(cid)
                        user = c.get('user', {})
                        all_comments.append(Comment(
                            author=user.get('nickname'),
                            author_id=user.get('unique_id'),
                            text=c.get('text'),
                            like_count=c.get('digg_count'),
                            timestamp=c.get('create_time'),
                            reply_count=c.get('reply_comment_total', 0),
                        ))
            except Exception:
                pass

        page.on('response', on_response)

        try:
            page.goto(video_url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)

            # Scroll to load more comments (TikTok loads ~20 per batch)
            scroll_attempts = min(10, max(1, max_comments // 20))
            for _ in range(scroll_attempts):
                if len(all_comments) >= max_comments:
                    break
                # Try scrolling the comments panel, fall back to page scroll
                page.evaluate("""
                    const panel = document.querySelector('[class*="CommentListContainer"]')
                                || document.querySelector('[class*="DivCommentListContainer"]');
                    if (panel) { panel.scrollTop = panel.scrollHeight; }
                    else { window.scrollBy(0, 600); }
                """)
                page.wait_for_timeout(2000)
        except Exception:
            pass
        finally:
            browser.close()

    if not all_comments:
        raise ValueError("Playwright could not extract TikTok comments")

    return CommentsResponse(
        success=True, video_id=video_id, video_title=video_title,
        total_comments=comment_count or len(all_comments),
        comments=all_comments[:max_comments],
        timestamp=datetime.utcnow().isoformat()
    )


def extract_tiktok_comments(url: str, use_proxy: bool = False, max_comments: int = 100, proxy_url: Optional[str] = None) -> CommentsResponse:
    """Extract comments from a TikTok video.

    Strategy:
      1. Try the lightweight direct API (no browser needed)
      2. Fall back to TikTok-Api (Playwright) if the direct API fails
    """
    import re

    video_id = None
    video_title = None
    comment_count = None

    # Step 1: get video ID and metadata via yt-dlp
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
    apply_proxy(ydl_opts, use_proxy, proxy_url)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id')
            video_title = info.get('title') or (info.get('description', '').split('\n')[0][:100] if info.get('description') else None)
            comment_count = info.get('comment_count')
    except Exception:
        # Try to extract video ID from URL as fallback
        match = re.search(r'/video/(\d+)', url)
        if match:
            video_id = match.group(1)

    if not video_id:
        return CommentsResponse(
            success=False, video_id=None, video_title=None, total_comments=0,
            comments=[], error="Could not determine TikTok video ID",
            timestamp=datetime.utcnow().isoformat()
        )

    # Step 2: try direct API first (lightweight)
    errors = []
    try:
        return _tiktok_comments_api(video_id, max_comments, proxy_url, video_title, comment_count)
    except Exception as e:
        errors.append(f"Direct API: {e}")

    # Step 3: fall back to Playwright browser (intercept API responses)
    if proxy_url:
        try:
            return _tiktok_comments_playwright(url, video_id, max_comments, video_title, comment_count, proxy_url)
        except Exception as e:
            errors.append(f"Playwright: {e}")
    else:
        errors.append("Playwright: skipped (needs proxy to reach TikTok from datacenter)")

    return CommentsResponse(
        success=False, video_id=video_id, video_title=video_title,
        total_comments=comment_count or 0, comments=[],
        error=f"All TikTok comment strategies failed: {'; '.join(errors)}",
        timestamp=datetime.utcnow().isoformat()
    )


def _tiktok_comments_api(video_id: str, max_comments: int, proxy_url: Optional[str],
                          video_title: Optional[str], comment_count: Optional[int]) -> CommentsResponse:
    """Fetch TikTok comments via direct API call."""
    api_url = "https://www.tiktok.com/api/comment/list/"
    all_comments = []
    cursor = 0

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.tiktok.com/',
        'Accept': 'application/json, text/plain, */*',
    }

    proxies = None
    if proxy_url:
        proxies = {'http': proxy_url, 'https': proxy_url}

    while len(all_comments) < max_comments:
        params = {
            'aweme_id': video_id,
            'count': min(50, max_comments - len(all_comments)),
            'cursor': cursor,
        }

        resp = requests.get(api_url, params=params, headers=headers, proxies=proxies, timeout=30)
        if resp.status_code != 200:
            break

        data = resp.json()
        comments_data = data.get('comments')
        if not comments_data:
            break

        for c in comments_data:
            user = c.get('user', {})
            all_comments.append(Comment(
                author=user.get('nickname'),
                author_id=user.get('unique_id'),
                text=c.get('text'),
                like_count=c.get('digg_count'),
                timestamp=c.get('create_time'),
                reply_count=c.get('reply_comment_total', 0),
            ))

        if not data.get('has_more'):
            break
        cursor = data.get('cursor', cursor + len(comments_data))

    if not all_comments:
        raise ValueError("TikTok API returned no comments (may require authentication)")

    return CommentsResponse(
        success=True, video_id=video_id, video_title=video_title,
        total_comments=comment_count or len(all_comments),
        comments=all_comments[:max_comments],
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

    # Add proxy if requested
    using_proxy = apply_proxy(ydl_opts, use_proxy, proxy_url)
    if using_proxy:
        # Use Android client when using proxy (bypasses n-challenge)
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

    # Add cookies only if NOT using proxy (Android client doesn't support cookies)
    if cookies_file and os.path.exists(cookies_file) and not using_proxy:
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
            followers=_get_follower_count(info),
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

    # Add proxy if requested
    if apply_proxy(ydl_opts, use_proxy, proxy_url):
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
    
    Uses yt-dlp to extract comments. A residential proxy is recommended.
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
def extract_youtube_comments_endpoint(request: YouTubeCommentsRequest):
    """Extract comments from a YouTube video

    Fetches actual comment text, author, likes, replies, etc.
    Set `max_comments` to limit results (default: 100)
    """
    try:
        return extract_youtube_comments(
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
        
        # Stream the content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with requests.get(video_url, stream=True, headers=headers) as r:
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


def get_best_video_url(url: str, platform: str, proxy_url: Optional[str] = None) -> Optional[str]:
    """Extract the best quality video URL from a video page
    
    Uses yt-dlp to get the direct video URL. The URL is signed and expires after some time.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',  # Best quality MP4, or best available
    }
    
    # Add proxy if provided
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get formats sorted by quality
            formats = info.get('formats', [])
            
            # Find best MP4 with both video and audio
            best_format = None
            for fmt in formats:
                if fmt.get('ext') == 'mp4' and fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    if not best_format or (fmt.get('height') or 0) > (best_format.get('height') or 0):
                        best_format = fmt
            
            # If no combined format, try separate video+audio
            if not best_format:
                # Get best video
                best_video = None
                for fmt in formats:
                    if fmt.get('vcodec') != 'none':
                        if not best_video or (fmt.get('height') or 0) > (best_video.get('height') or 0):
                            best_video = fmt
                
                # Get best audio
                best_audio = None
                for fmt in formats:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        if not best_audio or (fmt.get('abr') or 0) > (best_audio.get('abr') or 0):
                            best_audio = fmt
                
                if best_video:
                    best_format = best_video
                elif formats:
                    best_format = formats[-1]  # Fallback to last format
            
            if best_format and best_format.get('url'):
                return best_format['url']
            
            # Fallback: try info['url'] for direct videos
            if info.get('url'):
                return info['url']
                
    except Exception as e:
        print(f"Error getting video URL: {e}")
    
    return None


def select_format_url(formats: list, quality: str = "best") -> Optional[Dict[str, Any]]:
    """Select the best matching format from the metadata formats list.

    Prefers combined (video+audio) formats, but falls back to video-only
    formats when combined ones don't meet the requested quality (e.g. Android
    client caps combined MP4 at 360p while video-only streams go to 1080p+).

    Returns dict with 'url', 'height', 'ext', 'has_audio', etc. or None.
    """
    if not formats:
        return None

    combined = [f for f in formats if f.get('has_video') and f.get('has_audio') and f.get('url')]
    video_only = [f for f in formats if f.get('has_video') and not f.get('has_audio') and f.get('url')]
    all_video = [f for f in formats if f.get('has_video') and f.get('url')]

    if not all_video:
        return None

    # Parse target height
    target = None
    if quality != "best":
        try:
            target = int(quality.replace('p', ''))
        except ValueError:
            pass

    def _pick(pool, target_h):
        """Pick best format from pool at or below target_h (None = best)."""
        if not pool:
            return None
        if target_h is None:
            return pool[0]  # Already sorted by height descending
        best = None
        for fmt in pool:
            h = fmt.get('height') or 0
            if h <= target_h and (not best or h > (best.get('height') or 0)):
                best = fmt
        return best or pool[-1]

    # Try combined first
    combined_pick = _pick(combined, target)

    # If combined meets or exceeds the target (or target is "best" and combined is available), use it
    if combined_pick:
        combined_h = combined_pick.get('height') or 0
        if target is None:
            # "best" quality: check if video-only offers significantly higher resolution
            video_only_pick = _pick(video_only, None)
            if video_only_pick:
                vo_h = video_only_pick.get('height') or 0
                if vo_h > combined_h:
                    # Return video-only for higher quality
                    return video_only_pick
            return combined_pick
        elif combined_h >= target:
            return combined_pick

    # Combined doesn't meet quality — fall back to video-only
    video_only_pick = _pick(video_only, target)
    if video_only_pick:
        return video_only_pick

    # Last resort: anything with video
    return _pick(all_video, target)


def _yt_dlp_format_string(quality: str = "best") -> str:
    """Build a yt-dlp format selector string for the requested quality."""
    if quality == "best":
        return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    try:
        height = int(quality.replace('p', ''))
    except ValueError:
        return 'best[ext=mp4]/best'
    return f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'


def download_video_file(url: str, platform: str, proxy_url: Optional[str] = None, quality: str = "best") -> Optional[Dict]:
    """Download video file to memory and return content + metadata"""
    import tempfile
    import os

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': _yt_dlp_format_string(quality),
        'merge_output_format': 'mp4',
        'outtmpl': tempfile.gettempdir() + '/%(id)s.%(ext)s',
    }

    if apply_proxy(ydl_opts, proxy_url=proxy_url):
        if platform == 'youtube':
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id', 'unknown')
            ext = info.get('ext', 'mp4')
            
            # Download to temp file
            ydl.download([url])
            
            # Find the downloaded file
            temp_path = os.path.join(tempfile.gettempdir(), f"{video_id}.{ext}")
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    content = f.read()
                
                # Clean up temp file
                os.remove(temp_path)
                
                return {
                    'content': content,
                    'ext': ext,
                    'video_id': video_id,
                    'size': len(content)
                }
    except Exception as e:
        print(f"Error downloading video: {e}")
    
    return None


def _try_extract_comments(platform: str, url: str, max_comments: int,
                           proxy_url: Optional[str] = None) -> 'CommentsResponse':
    """Dispatch comment extraction to the right platform function."""
    if platform == "youtube":
        return extract_youtube_comments(url, False, max_comments, proxy_url)
    elif platform == "tiktok":
        return extract_tiktok_comments(url, False, max_comments, proxy_url)
    elif platform == "twitter":
        return extract_twitter_comments(url, False, max_comments, proxy_url)
    elif platform == "instagram":
        return extract_instagram_comments(url, None, False, max_comments, proxy_url)
    raise ValueError(f"Unsupported platform: {platform}")


# Apify Actor Entry Point
async def apify_main():
    """Main entry point for Apify Actor"""
    try:
        from apify import Actor
    except ImportError:
        print("Apify not installed. Install with: pip install apify")
        return

    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get("url")
        extract_comments = actor_input.get("extractComments", False)
        download_video = actor_input.get("downloadVideo", False)
        max_comments = actor_input.get("maxComments", 50)
        video_quality = actor_input.get("videoQuality", "best")

        if not url:
            await Actor.fail("No URL provided. Please provide a video URL.")
            return

        Actor.log.info(f"Processing URL: {url}")

        # Determine platform from URL
        platform = "youtube"
        url_lower = url.lower()
        if "tiktok" in url_lower:
            platform = "tiktok"
        elif "twitter" in url_lower or "x.com" in url_lower:
            platform = "twitter"
        elif "instagram" in url_lower:
            platform = "instagram"

        # Configure residential proxy - actor runs in datacenter
        proxy_configuration = None
        try:
            proxy_configuration = await Actor.create_proxy_configuration(groups=['RESIDENTIAL'])
            Actor.log.info(f"Residential proxy configured for {platform}")
        except Exception as e:
            Actor.log.warning(f"Could not configure residential proxy, trying without: {e}")

        async def fresh_proxy():
            """Get a fresh proxy URL for each operation (sessions expire after ~1 min idle)."""
            if proxy_configuration:
                return await proxy_configuration.new_url()
            return None

        try:
            Actor.log.info(f"Detected platform: {platform}")

            # Extract video metadata - fresh proxy URL for this operation
            proxy_url = await fresh_proxy()
            if platform == "youtube":
                metadata = await asyncio.to_thread(
                    extract_youtube_metadata, url, None, False, True, proxy_url
                )
            elif platform == "tiktok":
                metadata = await asyncio.to_thread(
                    extract_tiktok_metadata, url, False, True, proxy_url
                )
            elif platform == "twitter":
                metadata = await asyncio.to_thread(
                    extract_twitter_metadata, url, False, True, proxy_url
                )
            elif platform == "instagram":
                metadata = await asyncio.to_thread(
                    extract_instagram_metadata, url, None, False, True, proxy_url
                )
            else:
                await Actor.fail(f"Unsupported platform for URL: {url}")
                return

            result = metadata.model_dump()

            # Extract comments if requested
            # Comment APIs are sensitive to proxy choice - use a fallback chain:
            #   1. No proxy (datacenter IP - works for Twitter, sometimes YouTube)
            #   2. ScrapeOps proxy (proven to work for YouTube comments)
            #   3. Apify residential proxy (last resort)
            if extract_comments:
                Actor.log.info(f"Extracting up to {max_comments} comments...")
                comments_resp = None

                strategies = [
                    ("no proxy", None),
                    ("ScrapeOps proxy", SCRAPEOPS_PROXY),
                ]

                for strategy_name, strategy_proxy in strategies:
                    try:
                        Actor.log.info(f"Comments: trying {strategy_name}...")
                        comments_resp = await asyncio.to_thread(
                            _try_extract_comments, platform, url, max_comments, strategy_proxy
                        )
                        if comments_resp and comments_resp.comments:
                            Actor.log.info(f"Got {len(comments_resp.comments)} comments via {strategy_name}")
                            break
                    except Exception as e:
                        Actor.log.info(f"Comments {strategy_name}: {e}")
                        comments_resp = None

                # Last resort: Apify residential proxy
                if not (comments_resp and comments_resp.comments):
                    proxy_url = await fresh_proxy()
                    if proxy_url:
                        try:
                            Actor.log.info("Comments: trying residential proxy...")
                            comments_resp = await asyncio.to_thread(
                                _try_extract_comments, platform, url, max_comments, proxy_url
                            )
                            if comments_resp and comments_resp.comments:
                                Actor.log.info(f"Got {len(comments_resp.comments)} comments via residential proxy")
                        except Exception as e:
                            Actor.log.warning(f"All comment strategies failed. Last: {e}")

                if comments_resp and comments_resp.comments:
                    result["comments"] = [c.model_dump() for c in comments_resp.comments]
                    result["comments_extracted"] = len(comments_resp.comments)
                else:
                    result["comments"] = []
                    result["comments_extracted"] = 0
                    result["comments_error"] = "Could not extract comments with any proxy strategy"

            # Get video URL / download if requested
            if download_video:
                if platform == "youtube":
                    # YouTube: return direct format URL (fast, no download needed)
                    Actor.log.info(f"Selecting YouTube format URL (quality: {video_quality})...")
                    all_formats = result.get('formats', [])
                    fmt = select_format_url(all_formats, video_quality)
                    if fmt and fmt.get('url'):
                        has_audio = bool(fmt.get('has_audio'))
                        result["video_url"] = fmt['url']
                        result["video_quality"] = f"{fmt.get('height', '?')}p"
                        result["video_has_audio"] = has_audio
                        result["video_stored"] = False
                        if has_audio:
                            result["video_note"] = "Direct YouTube URL with audio (expires in ~6 hours)"
                        else:
                            result["video_note"] = "Direct YouTube URL, VIDEO ONLY (no audio track). Use yt-dlp to merge with audio."

                        # Build available format tiers for consumer choice
                        seen = set()
                        tiers = []
                        for f in all_formats:
                            if f.get('has_video') and f.get('url') and f.get('height'):
                                h = f['height']
                                a = bool(f.get('has_audio'))
                                key = (h, a)
                                if key not in seen:
                                    seen.add(key)
                                    tiers.append({
                                        "quality": f"{h}p",
                                        "has_audio": a,
                                        "url": f['url'],
                                        "ext": f.get('ext'),
                                        "format_id": f.get('format_id'),
                                    })
                        tiers.sort(key=lambda t: int(t['quality'].replace('p', '')), reverse=True)
                        result["video_formats"] = tiers

                        Actor.log.info(f"Selected {result['video_quality']} format URL (has_audio={has_audio})")
                    else:
                        result["video_error"] = "No suitable YouTube format found"
                        result["video_stored"] = False
                else:
                    # TikTok/Twitter/Instagram: download and store in KV store
                    Actor.log.info(f"Downloading video to key-value store (quality: {video_quality})...")
                    video_data = None
                    for attempt in range(3):
                        proxy_url = await fresh_proxy()
                        try:
                            video_data = await asyncio.to_thread(
                                download_video_file, url, platform, proxy_url, video_quality
                            )
                            if video_data:
                                break
                        except Exception as e:
                            Actor.log.warning(f"Download attempt {attempt + 1}/3 failed: {e}")
                            if attempt == 2:
                                result["video_error"] = str(e)

                    if video_data:
                        try:
                            kv_store = await Actor.open_key_value_store()
                            video_id = result.get('video_id', 'unknown')
                            ext = video_data.get('ext', 'mp4')
                            key = f"{platform}_{video_id}.{ext}"

                            await kv_store.set_value(
                                key,
                                video_data['content'],
                                content_type=f"video/{ext}"
                            )

                            store_id = os.environ.get('APIFY_DEFAULT_KEY_VALUE_STORE_ID', kv_store.id)
                            public_url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{key}"

                            result["video_key"] = key
                            result["video_url"] = public_url
                            result["video_stored"] = True
                            result["video_size_mb"] = round(len(video_data['content']) / (1024 * 1024), 2)
                            Actor.log.info(f"Video stored: {key} ({result['video_size_mb']} MB)")
                        except Exception as e:
                            result["video_error"] = str(e)
                            result["video_stored"] = False
                            Actor.log.error(f"KV store write failed: {e}")
                    else:
                        if "video_error" not in result:
                            result["video_error"] = "Could not download video after 3 attempts"
                        result["video_stored"] = False

            # Add run metadata
            result["platform"] = platform
            result["extracted_at"] = datetime.utcnow().isoformat()
            result["proxy_used"] = proxy_configuration is not None

            Actor.log.info(f"Successfully extracted data from {platform}")

            # Push to dataset
            await Actor.push_data(result)

        except Exception as e:
            Actor.log.error(f"Extraction failed: {str(e)}")
            await Actor.fail(str(e))


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
