# Video Metadata Extractor

Extract comprehensive metadata, comments, and download videos from YouTube, TikTok, Twitter/X, and Instagram videos using Apify's built-in residential proxy.

## Features

- **Multi-Platform Support**: YouTube, TikTok, Twitter/X, Instagram
- **Video Metadata**: Title, description, views, likes, comments count, duration, uploader info
- **Comments Extraction**: Extract actual comment text, author, likes, timestamps
- **Video Download**: Download videos directly to Apify's key-value store
- **Apify Residential Proxy**: Built-in proxy for reliable extraction (bypasses IP blocks)

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Video URL (YouTube, TikTok, Twitter/X, or Instagram) |
| `extractComments` | boolean | No | false | Also extract video comments |
| `useProxy` | boolean | No | true | Use Apify's built-in residential proxy (recommended) |
| `maxComments` | integer | No | 50 | Maximum comments to extract (1-500) |
| `downloadVideo` | boolean | No | false | Download the video file to Apify storage |

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
- `comments` - Array of comments (if requested)
- `video_download_url` - URL to downloaded video (if downloadVideo is enabled)
- `video_stored` - Boolean indicating if video was successfully downloaded

## Platform Notes

| Platform | Video | Comments | Download | Notes |
|----------|-------|----------|----------|-------|
| YouTube | ✅ | ✅ | ✅ | Proxy recommended |
| TikTok | ✅ | ✅ | ✅ | Uses browser automation for comments |
| Twitter/X | ✅ | ✅ | ✅ | No auth required |
| Instagram | ✅ | ✅* | ✅* | *Requires cookies for most content |

### About Apify Residential Proxy

This actor uses **Apify's built-in residential proxy** (not third-party services). When `useProxy` is enabled:
- Requests appear to come from real residential IPs
- Bypasses platform IP blocks and rate limits
- Consumes your Apify proxy bandwidth quota
- More reliable than datacenter IPs

### About Video Downloads

When `downloadVideo` is enabled:
- Video is downloaded using Apify's residential proxy
- Saved to Apify's key-value store
- Access via the returned `video_download_url`
- Videos remain in storage for 7+ days (depending on your plan)
- Uses more proxy bandwidth than metadata extraction only

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

## Pricing

This actor uses platform credits based on extraction complexity:
- **Video metadata only**: 1 platform credit
- **Video + comments**: 2-5 platform credits
- **Video + download**: 5-15 platform credits (depends on video size)

Additional costs:
- Residential proxy bandwidth (if useProxy is enabled)
- Key-value store storage (if downloadVideo is enabled)

## Support

For issues or feature requests, please contact the developer.
