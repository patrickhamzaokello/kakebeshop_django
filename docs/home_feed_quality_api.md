# Home Feed Quality and Ranking

The existing paginated endpoint `GET /api/v1/listings/` now powers the home feed by default. No new public endpoint is required.

## Public Feed Behavior

When `sort_by` is not supplied, the endpoint returns only listings that are:

- `status=ACTIVE`
- `is_verified=true`
- merchant is verified
- merchant is active
- the current time is inside the listing availability window
- `is_home_feed_eligible=true`
- `quality_status=APPROVED`

Availability window fields:

- `available_from`: optional datetime. If unset, the listing can appear immediately.
- `available_until`: optional datetime. If unset, the listing has no scheduled end.

Listings with no availability fields set are treated as always available.

Default ranking:

1. Active pinned listings first, ordered by `home_feed_pin_position`.
2. Active `feed_rank_boost` from highest to lowest.
3. Listings already shown recently by the client are demoted when `seen_listing_ids` is supplied.
4. Freshness score:
   - created in the last 24 hours: `30`
   - created in the last 3 days: `20`
   - created in the last 7 days: `10`
   - created in the last 14 days: `5`
   - older: `0`
5. `quality_score` from highest to lowest.
6. Featured listings.
7. Engagement score based on views and contacts.
8. Newest listings.

Expired boosts and pins are ignored automatically. They can remain stored for audit/history without affecting the feed.

Feed freshness:

- `GET /api/v1/listings/` accepts optional `seen_listing_ids`.
- Send IDs from listings the user has already seen recently, preferably the first page from the previous app open or refresh.
- The parameter can be repeated or comma-separated:
  - `?seen_listing_ids=uuid1,uuid2,uuid3`
  - `?seen_listing_ids[]=uuid1&seen_listing_ids[]=uuid2`
- The API uses up to 100 valid IDs and ignores invalid values.
- Pins still remain above everything. Boosted listings still rank above normal listings, but normal listings that were already seen are pushed below comparable unseen listings.

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
