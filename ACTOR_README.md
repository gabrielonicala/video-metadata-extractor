# Video Metadata Extractor

Extract comprehensive metadata, comments, and direct video URLs from YouTube, TikTok, Twitter/X, and Instagram videos.

## Features

- **Multi-Platform Support**: YouTube, TikTok, Twitter/X, Instagram
- **Video Metadata**: Title, description, views, likes, comments count, duration, uploader info
- **Direct URLs**: Get direct video download links (platform-dependent, expire quickly)
- **Video Streaming**: Optional streaming endpoint to proxy videos through the API (bypasses IP restrictions)
- **Comments Extraction**: Extract actual comment text, author, likes, timestamps
- **Twitter Comments**: Uses Playwright browser automation for reliable comment extraction
- **Proxy Support**: Residential proxy support for better reliability

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Video URL (YouTube, TikTok, Twitter/X, or Instagram) |
| `extractComments` | boolean | No | false | Also extract video comments |
| `useProxy` | boolean | No | true | Use residential proxy for better reliability |
| `maxComments` | integer | No | 50 | Maximum comments to extract (1-500) |

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
- `formats` - Available video formats with direct URLs (expire quickly!)
- `comments` - Array of comments (if requested)

## Platform Notes

| Platform | Video | Comments | Notes |
|----------|-------|----------|-------|
| YouTube | ✅ | ✅ | Proxy recommended for reliability |
| TikTok | ✅ | ✅ | Uses browser automation |
| Twitter/X | ✅ | ✅ (Playwright) | No auth required |
| Instagram | ✅ | ✅ | Requires cookies for most content |

### Important: Direct Video URLs
**Direct URLs expire after ~1-6 hours and are IP-locked.** They will NOT work if opened from a different IP than the API server.

**For reliable video access:** Use the separate `/stream` endpoint which proxies videos through the API server.

## Example Usage

### Basic metadata extraction:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "extractComments": false,
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

## Pricing

This actor uses platform credits based on extraction complexity:
- **Video metadata only**: 1 platform credit
- **Video + comments**: 2-5 platform credits (depends on comment count and platform)

**Twitter comments** use Playwright browser automation and cost slightly more due to compute overhead.

## Support

For issues or feature requests, please contact the developer.
