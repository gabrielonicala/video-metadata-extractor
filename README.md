# Video Metadata Extraction API

FastAPI-based service for extracting metadata, direct video URLs, and comments from YouTube, TikTok, Twitter/X, and Instagram videos.

## Features

- ✅ **YouTube Video Extraction**: Full metadata including views, likes, duration, thumbnails
- ✅ **TikTok Video Extraction**: Full metadata including views, likes, music info
- ✅ **Twitter/X Video Extraction**: Full metadata, no authentication required
- ⚠️ **Instagram Video Extraction**: Works but requires fresh cookies (authentication needed)
- ✅ **Direct Video URLs**: Get direct download/streaming URLs (expire after ~6 hours)
- ✅ **All Video Formats**: Multiple quality options (360p, 720p, etc.)
- ✅ **Comments Extraction**: Actual comment text, author, likes, timestamps (YouTube, Twitter/X fully working, TikTok via TikTokApi, Instagram requires cookies)
- ✅ **Proxy Support**: Built-in ScrapeOps residential proxy integration
- ✅ **Cookie Authentication**: For YouTube and Instagram fallback

## Requirements

- Python 3.8+
- FastAPI
- yt-dlp
- ScrapeOps proxy (for reliable extraction)

## Installation

```bash
# Install dependencies
pip install fastapi uvicorn yt-dlp pydantic

# Or use requirements.txt
pip install -r requirements.txt
```

## Configuration

### ScrapeOps Proxy (Recommended)

The API uses ScrapeOps residential proxy by default for reliable YouTube extraction:

1. Sign up at https://scrapeops.io/proxy-aggregator/
2. Get your API key
3. Update `main.py` with your proxy credentials:

```python
SCRAPEOPS_PROXY = "http://scrapeops:YOUR_API_KEY@residential-proxy.scrapeops.io:8181"
```

### YouTube Cookies (Optional Fallback)

If not using proxy, export cookies from your browser:

**Chrome:**
1. Install "Get cookies.txt LOCALLY" extension
2. Go to YouTube.com (logged in)
3. Click extension → Export cookies
4. Save as `youtube_cookies.txt`

## Running the Server

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server will start at `http://localhost:8000`

## API Endpoints

### 1. Extract Video Metadata

**Endpoint:** `POST /extract/youtube`

Extract full video metadata including direct URLs.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "use_proxy": true,
  "include_all_formats": true
}
```

**Parameters:**
- `url` (required): YouTube video URL
- `use_proxy` (optional): Use ScrapeOps proxy (default: false)
- `cookies_file` (optional): Path to cookies file (default: "youtube_cookies.txt")
- `include_all_formats` (optional): Include all video formats (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "platform": "youtube",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "description": "The official video...",
    "duration": 213,
    "view_count": 1740000000,
    "like_count": 18780000,
    "comment_count": 2400000,
    "upload_date": "20091025",
    "uploader": "Rick Astley",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "channel_url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "thumbnails": [...],
    "video_id": "dQw4w9WgXcQ",
    "formats": [
      {
        "format_id": "18",
        "format_note": "360p",
        "ext": "mp4",
        "quality": "360p",
        "width": 640,
        "height": 360,
        "fps": 30,
        "url": "https://rr2---sn-...googlevideo.com/videoplayback?...",
        "filesize": 15700000,
        "vcodec": "avc1.42001E",
        "acodec": "mp4a.40.2",
        "has_video": true,
        "has_audio": true
      }
    ],
    "tags": ["rick astley", "never gonna give you up"],
    "categories": ["Music"],
    "age_limit": 0
  },
  "timestamp": "2026-02-09T07:30:00"
}
```

### 2. Extract Comments

**Endpoint:** `POST /extract/youtube/comments`

Extract actual comments from a YouTube video.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "use_proxy": true,
  "max_comments": 100
}
```

**Parameters:**
- `url` (required): YouTube video URL
- `use_proxy` (optional): Use ScrapeOps proxy (default: false)
- `max_comments` (optional): Maximum comments to fetch (default: 100)

**Response:**
```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "video_title": "Rick Astley - Never Gonna Give You Up",
  "total_comments": 2400000,
  "comments": [
    {
      "author": "@someuser",
      "author_id": "UCxxxxxxxxx",
      "text": "This song never gets old!",
      "like_count": 1523,
      "timestamp": 1640000000,
      "reply_count": 0
    }
  ],
  "timestamp": "2026-02-09T07:30:00"
}
```

### 3. Extract TikTok Video Metadata

**Endpoint:** `POST /extract/tiktok`

Extract full TikTok video metadata including direct URLs.

**Request:**
```json
{
  "url": "https://www.tiktok.com/@scout2015/video/6718335390845095173",
  "use_proxy": false,
  "include_all_formats": true
}
```

**Parameters:**
- `url` (required): TikTok video URL
- `use_proxy` (optional): Use ScrapeOps proxy (default: false) - Note: TikTok often works better without proxy
- `include_all_formats` (optional): Include all video formats (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "platform": "tiktok",
    "url": "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    "title": "Scramble up ur name & I'll try to guess it😍❤️",
    "description": "Scramble up ur name & I'll try to guess it😍❤️ #foryoupage...",
    "duration": 10,
    "view_count": 154800,
    "like_count": 34300,
    "comment_count": 5666,
    "upload_date": "20191007",
    "uploader": "scout2015",
    "channel_id": "scout2015",
    "thumbnail": "https://p16-sign.tiktokcdn.com/...",
    "video_id": "6718335390845095173",
    "formats": [
      {
        "format_id": "0",
        "format_note": "watermarked",
        "ext": "mp4",
        "quality": "720p",
        "width": 720,
        "height": 1280,
        "url": "https://v16-webapp-prime.tiktok.com/video/...",
        "has_video": true,
        "has_audio": true
      }
    ],
    "raw_metadata": {
      "track": "original sound",
      "artist": "scout2015"
    }
  },
  "timestamp": "2026-02-09T07:30:00"
}
```

### 4. Extract TikTok Comments

**Endpoint:** `POST /extract/tiktok/comments`

Extract comments from a TikTok video. Note: TikTok comment extraction has limited support.

**Request:**
```json
{
  "url": "https://www.tiktok.com/@scout2015/video/6718335390845095173",
  "use_proxy": false,
  "max_comments": 50
}
```

**Parameters:**
- `url` (required): TikTok video URL
- `use_proxy` (optional): Use ScrapeOps proxy (default: false)
- `max_comments` (optional): Maximum comments to fetch (default: 100)

**Response:**
```json
{
  "success": true,
  "video_id": "6718335390845095173",
  "video_title": "Scramble up ur name & I'll try to guess it😍❤️",
  "total_comments": 5666,
  "comments": [],
  "timestamp": "2026-02-09T07:30:00"
}
```

**Note:** TikTok comments extraction is currently limited and may return empty results due to API restrictions.

### 5. Extract Twitter/X Video Metadata

**Endpoint:** `POST /extract/twitter`

Extract full Twitter/X video metadata including direct URLs. No authentication required.

**Request:**
```json
{
  "url": "https://x.com/username/status/1234567890123456789",
  "use_proxy": false,
  "include_all_formats": true
}
```

**Parameters:**
- `url` (required): Twitter/X video URL (twitter.com or x.com)
- `use_proxy` (optional): Use ScrapeOps proxy (default: false)
- `include_all_formats` (optional): Include all video formats (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "platform": "twitter",
    "url": "https://x.com/username/status/1234567890123456789",
    "title": "Video description text...",
    "duration": 49,
    "view_count": 125000,
    "like_count": 8500,
    "repost_count": 1200,
    "quote_count": 300,
    "comment_count": 450,
    "upload_date": "20250209",
    "uploader": "username",
    "channel_id": "1234567890",
    "thumbnail": "https://pbs.twimg.com/media/...",
    "video_id": "1234567890123456789",
    "formats": [
      {
        "format_id": "0",
        "ext": "mp4",
        "quality": "720p",
        "width": 720,
        "height": 1280,
        "url": "https://video.twimg.com/amplify_video/.../vid/720x1280/....mp4",
        "has_video": true,
        "has_audio": true
      }
    ]
  },
  "timestamp": "2026-02-09T07:30:00"
}
```

### 6. Extract Twitter/X Comments

**Endpoint:** `POST /extract/twitter/comments`

Extract replies/comments from a Twitter/X post.

**Request:**
```json
{
  "url": "https://x.com/username/status/1234567890123456789",
  "use_proxy": false,
  "max_comments": 50
}
```

**Parameters:**
- `url` (required): Twitter/X post URL
- `use_proxy` (optional): Use ScrapeOps proxy (default: false)
- `max_comments` (optional): Maximum comments to fetch (default: 50)

**Response:**
```json
{
  "success": true,
  "video_id": "1234567890123456789",
  "video_title": "Video description text...",
  "total_comments": 450,
  "comments": [
    {
      "author": "@commenter",
      "author_id": "9876543210",
      "text": "Great video!",
      "like_count": 25,
      "timestamp": 1707494400,
      "reply_count": 0
    }
  ],
  "timestamp": "2026-02-09T07:30:00"
}
```

### 7. Health Check

**Endpoint:** `GET /`

Check API status and configuration.

**Response:**
```json
{
  "message": "Video Metadata Extraction API",
  "version": "1.0.0",
  "cookies": {
    "youtube_status": "✅ Found",
    "youtube_file": "youtube_cookies.txt",
    "instagram_status": "⚠️ Not found",
    "instagram_file": "instagram_cookies.txt"
  },
  "proxies": {
    "status": "✅ 10 proxies loaded",
    "count": 10
  },
  "endpoints": {
    "youtube": "/extract/youtube",
    "youtube_comments": "/extract/youtube/comments",
    "tiktok": "/extract/tiktok",
    "tiktok_comments": "/extract/tiktok/comments",
    "twitter": "/extract/twitter",
    "twitter_comments": "/extract/twitter/comments",
    "instagram": "/extract/instagram",
    "instagram_comments": "/extract/instagram/comments",
    "stream": "/stream"
  }
}
```

## Usage Examples

### cURL - YouTube

```bash
# Extract video metadata
curl -X POST http://localhost:8000/extract/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/dQw4w9WgXcQ", "use_proxy": true}'

# Extract comments
curl -X POST http://localhost:8000/extract/youtube/comments \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/dQw4w9WgXcQ", "use_proxy": true, "max_comments": 50}'
```

### cURL - TikTok

```bash
# Extract video metadata
curl -X POST http://localhost:8000/extract/tiktok \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@scout2015/video/6718335390845095173"}'

# Extract comments (limited support)
curl -X POST http://localhost:8000/extract/tiktok/comments \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@scout2015/video/6718335390845095173", "max_comments": 50}'
```

### cURL - Twitter/X

```bash
# Extract video metadata
curl -X POST http://localhost:8000/extract/twitter \
  -H "Content-Type: application/json" \
  -d '{"url": "https://x.com/username/status/1234567890123456789"}'

# Extract comments
curl -X POST http://localhost:8000/extract/twitter/comments \
  -H "Content-Type: application/json" \
  -d '{"url": "https://x.com/username/status/1234567890123456789", "max_comments": 50}'
```

### Python

```python
import requests

# YouTube video extraction
response = requests.post(
    "http://localhost:8000/extract/youtube",
    json={"url": "https://youtu.be/dQw4w9WgXcQ", "use_proxy": True}
)
data = response.json()
print(f"Title: {data['data']['title']}")
print(f"Direct URL: {data['data']['formats'][0]['url']}")

# TikTok video extraction
response = requests.post(
    "http://localhost:8000/extract/tiktok",
    json={"url": "https://www.tiktok.com/@scout2015/video/6718335390845095173"}
)
data = response.json()
print(f"Title: {data['data']['title']}")
print(f"Views: {data['data']['view_count']}")
print(f"Direct URL: {data['data']['formats'][0]['url']}")

# Comments extraction (YouTube)
response = requests.post(
    "http://localhost:8000/extract/youtube/comments",
    json={"url": "https://youtu.be/dQw4w9WgXcQ", "use_proxy": True, "max_comments": 20}
)
data = response.json()
for comment in data['comments']:
    print(f"@{comment['author']}: {comment['text'][:100]}")

# Twitter/X video extraction
response = requests.post(
    "http://localhost:8000/extract/twitter",
    json={"url": "https://x.com/username/status/1234567890123456789"}
)
data = response.json()
print(f"Title: {data['data']['title']}")
print(f"Views: {data['data']['view_count']}")
print(f"Likes: {data['data']['like_count']}")
print(f"Direct URL: {data['data']['formats'][0]['url']}")

# Twitter/X comments extraction
response = requests.post(
    "http://localhost:8000/extract/twitter/comments",
    json={"url": "https://x.com/username/status/1234567890123456789", "max_comments": 20}
)
data = response.json()
for comment in data['comments']:
    print(f"@{comment['author']}: {comment['text'][:100]}")
```

## Important Notes

### Direct Video URLs
- **URLs expire** after approximately 6 hours
- URLs are unique per request and IP
- Use immediately after extraction

### Proxy Usage
- **Highly recommended** for reliable extraction
- Residential proxies bypass YouTube's bot detection
- Free tier available from ScrapeOps (100MB)

### Rate Limiting
- YouTube may throttle excessive requests
- Use delays between requests in production
- Consider caching results

### Legal Considerations
- Respect YouTube's Terms of Service
- Don't use for mass downloading
- Cache data responsibly
- Consider using official YouTube Data API for production apps

## Troubleshooting

### "Sign in to confirm you're not a bot"
- Enable `use_proxy: true` in request
- Or use valid YouTube cookies

### "Requested format is not available"
- Video may be region-restricted
- Try with proxy from different region
- Some videos don't have downloadable formats

### Empty comments list
- Comments may be disabled on video
- Try increasing `max_comments`
- Some videos have comment extraction restrictions

## Apify Deployment

To deploy as an Apify actor:

1. Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
COPY proxies.txt .
COPY youtube_cookies.txt .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Create `.actor/actor.json`:
```json
{
  "actorSpecification": 1,
  "name": "youtube-metadata-extractor",
  "title": "YouTube Metadata Extractor",
  "description": "Extract video metadata and comments from YouTube",
  "version": "1.0.0",
  "meta": {
    "templateId": "python-start"
  },
  "dockerfile": "./Dockerfile"
}
```

3. Deploy via Apify CLI or web interface

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- Code passes `flake8` linting
- Add tests for new features
- Update documentation

## Credits

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Proxy support via [ScrapeOps](https://scrapeops.io)
- FastAPI framework
