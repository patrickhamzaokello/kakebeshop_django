# AI Banner Agent Upload Guide

Use this guide when an AI agent generates banner artwork and needs to submit it to Kakebe Shop.

## Endpoint

```http
POST https://backend.kakebeshop.com/api/v1/banner-agent/upload/
Content-Type: multipart/form-data
X-Banner-Agent-Secret: <agent-secret>
```

Use the `X-Banner-Agent-Secret` header for authentication.

## Required File

Send one image file in the multipart field named `image`.

Supported formats:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`

Recommended desktop banner size:

```text
1200 x 400
```

Recommended mobile banner size:

```text
800 x 800 or 1080 x 1080
```

## Basic Upload Example

```bash
curl -X POST "https://backend.kakebeshop.com/api/v1/banner-agent/upload/" \
  -H "X-Banner-Agent-Secret: <agent-secret>" \
  -F "image=@women-shoes-banner.png;type=image/png" \
  -F "title=Women Shoes" \
  -F "description=AI-generated banner for women shoes promotion" \
  -F "display_type=BANNER" \
  -F "placement=HOME_TOP" \
  -F "platform=ALL" \
  -F "target=image" \
  -F "link_type=NONE" \
  -F "cta_text=Shop now" \
  -F "start_date=2026-05-24T00:00:00Z" \
  -F "end_date=2026-06-24T00:00:00Z" \
  -F "sort_order=50"
```

## JSON Metadata Upload

Agents can also send banner details as a JSON object in the `metadata` field.

```bash
curl -X POST "https://backend.kakebeshop.com/api/v1/banner-agent/upload/" \
  -H "X-Banner-Agent-Secret: <agent-secret>" \
  -F "image=@women-shoes-banner.png;type=image/png" \
  -F 'metadata={
    "title": "Women Shoes",
    "description": "Fresh women shoe styles",
    "display_type": "BANNER",
    "placement": "HOME_TOP",
    "platform": "ALL",
    "target": "image",
    "link_type": "NONE",
    "cta_text": "Shop now",
    "start_date": "2026-05-24T00:00:00Z",
    "end_date": "2026-06-24T00:00:00Z",
    "sort_order": 50
  }'
```

## Target Field

Use `target` to choose which banner image field is updated.

```json
{
  "target": "image"
}
```

For mobile-specific artwork:

```json
{
  "target": "mobile_image"
}
```

## Banner Link Types

### No Link

```json
{
  "link_type": "NONE"
}
```

### Single Listing

```json
{
  "link_type": "LISTING",
  "listing_id": "00000000-0000-0000-0000-000000000000"
}
```

### Multiple Listings

```json
{
  "link_type": "LISTINGS",
  "listing_ids": [
    "00000000-0000-0000-0000-000000000000",
    "11111111-1111-1111-1111-111111111111"
  ]
}
```

### Category

```json
{
  "link_type": "CATEGORY",
  "category_id": "00000000-0000-0000-0000-000000000000"
}
```

### Merchant

```json
{
  "link_type": "MERCHANT",
  "merchant_id": "00000000-0000-0000-0000-000000000000"
}
```

### External URL

```json
{
  "link_type": "URL",
  "link_url": "https://example.com"
}
```

## Updating an Existing Banner

To replace the image for an existing banner, include `banner_id`.

```json
{
  "banner_id": "00000000-0000-0000-0000-000000000000",
  "target": "image",
  "title": "Updated Women Shoes"
}
```

## Response

A successful upload returns a queue record.

```json
{
  "success": true,
  "message": "Banner image queued for moderation and upload.",
  "data": {
    "id": "ad9d1441-ab00-4035-9fd5-6a013c06cd0e",
    "status": "PENDING",
    "target_field": "image",
    "banner": null,
    "cdn_url": null
  }
}
```

Save the `data.id`. It is the banner import ID.

## Moderation Rules

AI uploads do not go live immediately.

- Uploaded banners are queued first.
- The background worker uploads the image to AWS.
- Admins preview the submitted banner in Django admin.
- Admins must verify the banner before users see it in the app.
- The API forces `is_verified=false` for remote AI submissions.

## Common Errors

### Invalid Credential

```json
{
  "detail": "Invalid banner agent credential."
}
```

Check that the `X-Banner-Agent-Secret` header is present and correct.

### Invalid Image

```json
{
  "image": ["Upload a valid image. The file you uploaded was either not an image or a corrupted image."]
}
```

Regenerate the image as a valid PNG, JPG, JPEG, or WEBP file.

### Missing Required Image

```json
{
  "image": ["No file was submitted."]
}
```

Make sure the multipart field name is exactly `image`.

## Production Notes

- Do not submit placeholder or low-quality artwork.
- Do not include text that may be too small on mobile.
- Keep important subjects away from the edges of the image.
- Use `mobile_image` when desktop artwork will crop poorly on small screens.
- Avoid setting `sort_order` too low unless the banner is meant to rank near the top.
