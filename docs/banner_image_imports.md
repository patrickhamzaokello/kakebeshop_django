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

## Remote AI Agent Uploads

AI agents can upload remotely without filesystem access:

```http
POST /api/v1/banner-agent/upload/
Authorization: Bearer <banner-agent-secret>
Content-Type: multipart/form-data
```

Multipart fields:

| Field | Required | Description |
|---|---|---|
| `image` | yes | Banner image file (`jpg`, `jpeg`, `png`, `webp`) |
| `metadata` | no | JSON object using the sidecar format above |
| `target` | no | `image` or `mobile_image` |
| `banner_id` | no | Existing banner to update |
| `title` | no | New/updated banner title |
| `placement` | no | Banner placement such as `HOME_TOP` |
| `link_type` | no | `LISTING`, `LISTINGS`, `CATEGORY`, `MERCHANT`, `URL`, or `NONE` |
| `listing_id` / `listing_ids` | no | Listing target(s) |
| `category_id` | no | Category target |
| `merchant_id` | no | Merchant target |
| `link_url` | no | External URL target |

Response:

```json
{
  "success": true,
  "message": "Banner image queued for moderation and upload.",
  "data": {
    "id": "queue-id",
    "status": "PENDING",
    "target_field": "image"
  }
}
```

Uploaded files are queued first. The background job still uploads to S3 and creates or updates the banner.

## Moderation and Preview

AI-created banners are not live by default:

- New banners are created with `is_verified=false`.
- Public banner endpoints only return active, verified, in-date banners that have an image URL.
- Admins can preview banners from Django admin before verification.
- Admins can review upload queue records in `Banner image imports`.
- Failed imports keep `error_message` and are visible in admin.

## Agent Credentials

Credentials are managed in Django admin under `Banner agent credentials`.

- Create a credential to generate a secret.
- Reset selected credentials from the admin action menu.
- The raw secret is shown only once when created or reset.
- The database stores only a token prefix and SHA-256 hash.
- Deactivate a credential to immediately block uploads.

Agents can send the secret either as:

```http
Authorization: Bearer <secret>
```

or:

```http
X-Banner-Agent-Secret: <secret>
```

Bootstrap/reset from the server shell:

```bash
python manage.py reset_banner_agent_credential --name default-ai-banner-agent
```

To set a known secret during deployment:

```bash
python manage.py reset_banner_agent_credential --name default-ai-banner-agent --secret "kbai_replace_with_secret"
```
