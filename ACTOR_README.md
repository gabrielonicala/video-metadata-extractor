# Video Metadata Extractor

Extract comprehensive metadata, comments, and direct video URLs from YouTube, TikTok, Twitter/X, and Instagram videos.

## Features

- **Multi-Platform Support**: YouTube, TikTok, Twitter/X, Instagram
- **Video Metadata**: Title, description, views, likes, comments count, duration, uploader info
- **Direct URLs**: Get direct video download links (platform-dependent)
- **Comments Extraction**: Extract actual comment text, author, likes, timestamps
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
- `formats` - Available video formats with direct URLs
- `comments` - Array of comments (if requested)

## Platform Notes

| Platform | Video | Comments | Notes |
|----------|-------|----------|-------|
| YouTube | ✅ | ✅ | Proxy recommended for reliability |
| TikTok | ✅ | ✅ | Uses browser automation |
| Twitter/X | ✅ | ✅ | No auth required |
| Instagram | ✅ | ✅ | Requires cookies for most content |

## Example Usage

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
- Video metadata only: 1 platform credit
- Video + comments: 2-5 platform credits (depends on comment count)

## Support

For issues or feature requests, please contact the developer.
