# Admin Broadcast Frontend Reference

Base URL: `/api/v1/admin/broadcasts/`

All requests require a staff user JWT:

```http
Authorization: Bearer <access_token>
```

## Feature Summary

Admins can schedule a broadcast email or push notification to all eligible active users.

- Email campaigns target active users with email addresses.
- Push campaigns target active users with active push tokens.
- A campaign may be scheduled for a future time or queued immediately with `send_now: true`.
- Campaigns can only be cancelled while their status is `SCHEDULED`.

## Suggested Screens

### Broadcast List

Route suggestion: `/admin/broadcasts`

Use this screen for campaign history and operational status.

Controls:

- Channel filter: `ALL`, `EMAIL`, `PUSH`
- Status filter: `ALL`, `SCHEDULED`, `SENDING`, `SENT`, `FAILED`, `CANCELLED`
- Pagination: `page`, `page_size`
- Primary action: create broadcast

Recommended columns:

| Column | Field |
|---|---|
| Title | `title` |
| Channel | `channel` |
| Status | `status` |
| Scheduled | `scheduled_at` |
| Sent | `sent_at` |
| Target users | `target_count` |
| Notifications queued | `notification_count` |
| Created by | `created_by_email` |

Status display:

| Status | Meaning | UI behavior |
|---|---|---|
| `SCHEDULED` | Waiting for Celery ETA | Show cancel action |
| `SENDING` | Task is creating notification deliveries | Disable cancel |
| `SENT` | Notification deliveries were queued | Show final counts |
| `FAILED` | Task failed after retry/error | Show `error_message` |
| `CANCELLED` | Admin cancelled before send | No actions |

### Create Broadcast

Route suggestion: `/admin/broadcasts/new`

Fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `channel` | enum | Yes | `EMAIL` or `PUSH`; omit only when using schedule-specific endpoints |
| `title` | string | Yes | Non-empty, max 255 chars |
| `message` | string | Yes | Non-empty |
| `send_now` | boolean | No | If true, `scheduled_at` is ignored |
| `scheduled_at` | datetime | Required unless `send_now=true` | Must be future ISO datetime |
| `metadata` | object | No | Optional campaign tags, deep links, etc. |

Recommended form behavior:

- Use a segmented control for `Email` / `Push`.
- Use a toggle for `Send now`.
- Hide or disable the date-time picker when `Send now` is enabled.
- Show a preview panel with title/message exactly as entered.
- Disable submit while request is pending.
- After success, navigate to the campaign detail screen.

## Endpoints

### List Campaigns

`GET /api/v1/admin/broadcasts/`

Query parameters:

```text
channel=EMAIL|PUSH
status=SCHEDULED|SENDING|SENT|FAILED|CANCELLED
page=1
page_size=20
```

Example:

```http
GET /api/v1/admin/broadcasts/?channel=PUSH&status=SCHEDULED&page=1&page_size=20
```

Paginated response:

```json
{
  "count": 42,
  "total_pages": 3,
  "current_page": 1,
  "next": "https://example.com/api/v1/admin/broadcasts/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "channel": "PUSH",
      "title": "New arrivals",
      "message": "Fresh listings just landed.",
      "metadata": {
        "campaign": "new_arrivals"
      },
      "scheduled_at": "2026-04-27T12:00:00Z",
      "status": "SCHEDULED",
      "created_by": "uuid",
      "created_by_email": "admin@example.com",
      "celery_task_id": "celery-task-id",
      "target_count": 120,
      "notification_count": 0,
      "error_message": "",
      "sent_at": null,
      "created_at": "2026-04-27T10:00:00Z",
      "updated_at": "2026-04-27T10:00:00Z"
    }
  ]
}
```

### Retrieve Campaign

`GET /api/v1/admin/broadcasts/{id}/`

Response:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "channel": "EMAIL",
    "title": "Weekend deals",
    "message": "New offers are live on Kakebe Shop.",
    "status": "SENT",
    "target_count": 450,
    "notification_count": 450,
    "error_message": "",
    "scheduled_at": "2026-04-27T12:00:00Z",
    "sent_at": "2026-04-27T12:00:05Z"
  }
}
```

### Schedule Email

`POST /api/v1/admin/broadcasts/schedule-email/`

Use this from an email-specific form.

```json
{
  "title": "Weekend deals",
  "message": "New offers are live on Kakebe Shop.",
  "scheduled_at": "2026-04-27T12:00:00Z",
  "metadata": {
    "campaign": "weekend_deals",
    "source": "admin_dashboard"
  }
}
```

### Schedule Push

`POST /api/v1/admin/broadcasts/schedule-push/`

Use this from a push-specific form.

```json
{
  "title": "Price drops nearby",
  "message": "Check fresh listings from merchants near you.",
  "send_now": true,
  "metadata": {
    "campaign": "price_drops",
    "deep_link": "kakebeshop://listings"
  }
}
```

### Generic Create

`POST /api/v1/admin/broadcasts/`

Use this if the same form supports both channels.

```json
{
  "channel": "PUSH",
  "title": "New arrivals",
  "message": "Fresh listings just landed.",
  "scheduled_at": "2026-04-27T12:00:00Z"
}
```

Success response:

```json
{
  "success": true,
  "message": "Push Notification broadcast scheduled",
  "data": {
    "id": "uuid",
    "channel": "PUSH",
    "title": "New arrivals",
    "message": "Fresh listings just landed.",
    "scheduled_at": "2026-04-27T12:00:00Z",
    "status": "SCHEDULED",
    "target_count": 120,
    "notification_count": 0,
    "celery_task_id": "celery-task-id"
  }
}
```

### Cancel Campaign

`POST /api/v1/admin/broadcasts/{id}/cancel/`

No body required.

Only show this action when `status === "SCHEDULED"`.

Success response:

```json
{
  "success": true,
  "message": "Broadcast campaign cancelled",
  "data": {
    "id": "uuid",
    "status": "CANCELLED"
  }
}
```

Failure response when no longer cancellable:

```json
{
  "success": false,
  "error": "Cannot cancel a campaign with status SENT"
}
```

## Validation Handling

The backend returns standard DRF validation errors for bad form data.

Examples:

```json
{
  "scheduled_at": ["This field is required unless send_now is true."]
}
```

```json
{
  "scheduled_at": ["Schedule time cannot be in the past."]
}
```

```json
{
  "title": ["Title cannot be empty."]
}
```

Frontend validation should mirror these rules before submit.

## Polling

After creating or cancelling a campaign:

- Refetch the campaign detail immediately.
- For `SCHEDULED` campaigns, the list can refresh every 30-60 seconds.
- For `SENDING` campaigns, poll detail every 5-10 seconds until it becomes `SENT` or `FAILED`.

## Notes

- `target_count` is calculated when the campaign is scheduled.
- `notification_count` is populated after the Celery task queues notification deliveries.
- `SENT` means delivery records were queued; individual delivery success/failure is tracked in the notification delivery system.
- `metadata` is optional and is included on generated notification records for analytics, deep links, and campaign attribution.
