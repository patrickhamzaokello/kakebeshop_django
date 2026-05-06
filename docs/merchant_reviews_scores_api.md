# Merchant Reviews and Scores

Merchant reviews live under the engagement API, while public merchant profiles expose read-only review and score views.

## Create Or Update A Merchant Review

`POST /api/v1/merchant-reviews/`

Authentication is required. Buyers can review a merchant only after they have at least one completed order with that merchant.

```json
{
  "merchant": "merchant-uuid",
  "order_intent": "completed-order-uuid",
  "rating": 5,
  "comment": "Quick delivery and clear communication."
}
```

Rules:

- A buyer cannot review their own merchant profile.
- A buyer can leave only one review per merchant.
- If `order_intent` is provided, it must belong to the buyer, match the merchant, and have `status=COMPLETED`.
- If `order_intent` is omitted, the buyer must still have a completed order with the merchant.

Review responses include:

- `user_id`
- `user_name`
- `user_profile_image`
- `rating`
- `comment`
- `created_at`
- `updated_at`

## Public Merchant Reviews

`GET /api/v1/merchants/{merchant_id}/reviews/`

Returns paginated public reviews for a verified, active merchant.

## Public Merchant Score

`GET /api/v1/merchants/{merchant_id}/score/`

Returns the merchant score record. If a score record does not exist yet, the API calculates one before returning.

The score is calculated from:

- average merchant rating
- completed vs cancelled orders
- active listing health
- unresolved/non-dismissed reports

## Cached Rating Fields

`Merchant.rating` and `Merchant.total_reviews` are recalculated whenever a merchant review is created, updated, or deleted. Merchant list/detail responses continue to expose these cached fields, and now also include:

- `reputation_score`
- `score` on detail responses
