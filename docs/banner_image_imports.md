# Banner Image Imports

Banner images now use the same AWS/CloudFront pattern as listing images.

## Folder Workflow

AI/design agents should write banner art to:

```text
banner_imports/incoming/
```

The Celery beat task `process-banner-image-imports` runs every 2 minutes and calls:

```text
kakebe_apps.promotions.tasks.process_pending_banner_image_imports
```

The worker:

1. Scans `banner_imports/incoming/`.
2. Creates a `BannerImageImport` queue record for each new image.
3. Creates or updates the `PromotionalBanner` from optional JSON metadata.
4. Generates a presigned S3 PUT URL.
5. Uploads the local image file to S3.
6. Creates a confirmed `ImageAsset` with `image_type=banner`.
7. Updates `PromotionalBanner.image` or `PromotionalBanner.mobile_image` with the CloudFront URL.
8. Moves files to `banner_imports/processed/` or `banner_imports/failed/`.

## File Naming

Attach to an existing banner without JSON:

```text
<banner_id>__desktop.png
<banner_id>__mobile.png
```

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`.

## Sidecar JSON

For more control, add a JSON file with the same stem:

```text
kampala-dental-banner.png
kampala-dental-banner.json
```

```json
{
  "title": "Weekend Dental Offers",
  "display_type": "BANNER",
  "placement": "HOME_TOP",
  "platform": "ALL",
  "target": "image",
  "link_type": "LISTINGS",
  "listing_ids": ["00000000-0000-0000-0000-000000000000"],
  "cta_text": "View offers",
  "start_date": "2026-05-24T00:00:00Z",
  "end_date": "2026-06-24T00:00:00Z"
}
```

Use `banner_id` in the JSON to update an existing banner. Omit it to create a new banner.

## Banner Targets

Public banner responses include a normalized `target` object for app navigation.

Supported targets:

- `LISTING` with `listing_id`
- `LISTINGS` with `listing_ids`
- `CATEGORY` with `category_id`
- `MERCHANT` with `merchant_id`
- `URL` with `link_url`
- `NONE`

New sidecar-created banners default to `is_verified=false`, so admins can review them before they appear in the app.
