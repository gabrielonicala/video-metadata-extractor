# Video Metadata Extractor

Extract comprehensive metadata, comments, and download videos from YouTube, TikTok, Twitter/X, and Instagram videos using Apify's residential proxy.

## Features

- **Multi-Platform Support**: YouTube, TikTok, Twitter/X, Instagram
- **Video Metadata**: Title, description, views, likes, comments count, duration, uploader info
- **Comments Extraction**: Extract actual comment text, author, likes, timestamps
- **Video Download**: Download videos to Apify's key-value store (persistent, signed URLs)
- **Apify Residential Proxy**: Built-in proxy for reliable extraction and downloads

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Video URL (YouTube, TikTok, Twitter/X, or Instagram) |
| `extractComments` | boolean | No | true | Extract video comments |
| `useProxy` | boolean | No | true | Use Apify's built-in residential proxy (recommended) |
| `maxComments` | integer | No | 50 | Maximum comments to extract (1-500) |
| `downloadVideo` | boolean | No | false | Download video to Apify storage (max 500MB) |

## Output

Returns JSON with:
- `title` - Video title
- `description` - Video description
- `duration` - Duration in seconds
- `views` - View count
- `likes` - Like count
- `comments_count` - Total comments
- `uploader` - Creator/channel name
- `platform` - Source platform
- `formats` - Available video formats with direct URLs
- `comments` - Array of comments (if extraction successful)
- `video_download_url` - Signed URL to downloaded video (if downloadVideo enabled)
- `video_stored` - Boolean indicating if video was successfully stored
- `video_error` - Error message if download failed

## Platform Notes

| Platform | Video | Comments | Download | Notes |
|----------|-------|----------|----------|-------|
| YouTube | ✅ | ✅ | ✅ | Best reliability with proxy |
| TikTok | ✅ | ✅ | ✅ | Uses TikTok-Api library |
| Twitter/X | ✅ | ✅ | ✅ | No auth required |
| Instagram | ✅ | ✅* | ✅* | *Requires cookies for most content |

### About TikTok Comments
TikTok comments are extracted using the [TikTok-Api](https://github.com/davidteather/TikTok-Api) library with browser automation. While we strive for reliability, TikTok's anti-bot measures may occasionally cause extraction to fail.

### About Apify Residential Proxy

This actor uses **Apify's built-in residential proxy**. When `useProxy` is enabled:
- Requests appear to come from real residential IPs
- Bypasses platform IP blocks and rate limits
- Required for reliable video downloads
- Consumes your Apify proxy bandwidth quota

### About Video Downloads

When `downloadVideo` is enabled:
- Video is downloaded using Apify's residential proxy
- Saved to Apify's key-value store with signed URLs
- Signed URLs work from any IP and don't expire
- Files are limited to 500MB (to prevent timeouts)
- Videos remain in storage based on your plan
- Uses more proxy bandwidth than metadata extraction only

**Example signed URL:**
```
https://api.apify.com/v2/key-value-stores/VeQN9U7ieYSrs0W5N/records/videos/youtube_abc123.mp4?signature=6USpGZNkFQNPdWqcTrUP
```

### Instagram Requirements

Instagram requires authentication for most content. To use Instagram features:
1. Log into Instagram in your browser
2. Export cookies using "Get cookies.txt LOCALLY" extension
3. Upload the cookies file as `instagram_cookies.txt` to the actor

## Example Usage

### Basic metadata extraction:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "useProxy": true
}
```

### With comments:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "extractComments": true,
  "useProxy": true,
  "maxComments": 50
}
```

### Download video:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "useProxy": true,
  "downloadVideo": true
}
```

### TikTok (with comments):
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890",
  "useProxy": true,
  "downloadVideo": true,
  "extractComments": true,
  "maxComments": 50
}
```

## Pricing

This actor uses platform credits based on extraction complexity:
- **Video metadata only**: 1-2 platform credits
- **Video + comments**: 3-5 platform credits
- **Video + download**: 5-15 platform credits (depends on video size)

Additional costs:
- Residential proxy bandwidth (if useProxy is enabled)
- Key-value store storage (if downloadVideo is enabled)

## Support

For issues or feature requests, please contact the developer.
