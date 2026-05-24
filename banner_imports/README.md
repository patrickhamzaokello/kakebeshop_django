# Banner Image Import Folder

Drop AI-generated banner images into `banner_imports/incoming/`.

Supported image files:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

The background job scans this folder, uploads each image to AWS S3 using a presigned PUT URL, creates an `ImageAsset`, updates the `PromotionalBanner.image` or `PromotionalBanner.mobile_image` URL, then moves the image and sidecar JSON to `processed/` or `failed/`.

## Attach to an existing banner

Name the image with the banner ID:

```text
<banner_id>__desktop.png
<banner_id>__mobile.png
```

Or use a sidecar JSON with the same filename stem:

```text
spring-sale.png
spring-sale.json
```

```json
{
  "banner_id": "00000000-0000-0000-0000-000000000000",
  "target": "image"
}
```

Use `"target": "mobile_image"` for the mobile-specific image.

## Create or update a banner from the sidecar

If `banner_id` is omitted, the processor creates a banner.

```json
{
  "title": "Weekend Dental Offers",
  "description": "Promotional banner for approved dental service listings.",
  "display_type": "BANNER",
  "placement": "HOME_TOP",
  "platform": "ALL",
  "target": "image",
  "link_type": "LISTINGS",
  "listing_ids": [
    "00000000-0000-0000-0000-000000000000"
  ],
  "cta_text": "View offers",
  "start_date": "2026-05-24T00:00:00Z",
  "end_date": "2026-06-24T00:00:00Z",
  "is_verified": false,
  "is_active": true,
  "sort_order": 10
}
```

Targeting options:

- `link_type: "LISTING"` with `listing_id`
- `link_type: "LISTINGS"` with `listing_ids`
- `link_type: "CATEGORY"` with `category_id`
- `link_type: "MERCHANT"` with `merchant_id`
- `link_type: "URL"` with `link_url`
- `link_type: "NONE"`

New banners default to `is_verified=false`, so admins can review before the app shows them.

Remote AI agents should use `POST /api/v1/banner-agent/upload/` with a banner-agent secret instead of writing directly to this folder. See `docs/banner_image_imports.md`.
