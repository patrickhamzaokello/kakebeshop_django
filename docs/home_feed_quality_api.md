# Home Feed Quality and Ranking

The existing paginated endpoint `GET /api/v1/listings/` now powers the home feed by default. No new public endpoint is required.

## Public Feed Behavior

When `sort_by` is not supplied, the endpoint returns only listings that are:

- `status=ACTIVE`
- `is_verified=true`
- merchant is verified
- `is_home_feed_eligible=true`
- `quality_status=APPROVED`

Default ranking:

1. Active pinned listings first, ordered by `home_feed_pin_position`.
2. Active `feed_rank_boost` from highest to lowest.
3. `quality_score` from highest to lowest.
4. Featured listings.
5. Engagement score based on views and contacts.
6. Newest listings.

Expired boosts and pins are ignored automatically. They can remain stored for audit/history without affecting the feed.

If the frontend supplies `sort_by`, the endpoint still applies the quality gate, then uses the requested sort.

Supported `sort_by` values:

- `created_at`
- `-created_at`
- `price`
- `-price`
- `views`
- `-views`
- `title`
- `-title`

## Admin Fields

Admin listing responses and PATCH updates include:

- `is_home_feed_eligible`
- `quality_status`: `PENDING`, `APPROVED`, `REJECTED`, `NEEDS_REVIEW`
- `quality_score`: `0.00` to `100.00`
- `quality_rejection_reason`
- `feed_rank_boost`: `0` to `100`
- `feed_boost_until`
- `feed_boost_reason`
- `is_home_feed_pinned`
- `home_feed_pin_position`
- `home_feed_pin_until`

New listings start as `quality_status=PENDING` and `is_home_feed_eligible=false`. The migration backfills existing active, verified listings from verified merchants as `APPROVED`, eligible, and `quality_score=50.00` so the current feed does not go empty on deploy.

## Admin Controls

Use the admin listing endpoints:

- `POST /api/v1/admin/listings/{id}/approve-quality/`
- `POST /api/v1/admin/listings/{id}/reject-quality/`
- `POST /api/v1/admin/listings/{id}/mark-quality-review/`
- `POST /api/v1/admin/listings/{id}/set-feed-boost/`
- `POST /api/v1/admin/listings/{id}/pin-home-feed/`
- `POST /api/v1/admin/listings/{id}/unpin-home-feed/`

Pinned listings must already be approved and home-feed eligible. Active pin positions must be unique; the API returns `400` when another active pin is already using the requested position.
