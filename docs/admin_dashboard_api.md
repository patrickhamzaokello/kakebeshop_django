# Admin Dashboard API Documentation

All endpoints are prefixed with `/api/v1/admin/`.

**Authentication:** All endpoints require a valid Bearer token and the user must have `is_staff=True`.

**Authorization Header:**
```
Authorization: Bearer <access_token>
```

---

## Table of Contents

- [Stats](#1-stats)
- [User Management](#2-user-management)
- [Merchant Management](#3-merchant-management)
- [Listing Management](#4-listing-management)
- [Category Management](#5-category-management)
- [Order Management](#6-order-management)
- [Image Management](#7-image-management)
- [Broadcast Notifications](#8-broadcast-notifications)

---

## 1. Stats

### GET `/api/v1/admin/stats/`

Returns platform-wide counts for the dashboard overview.

**Response `200`**
```json
{
  "success": true,
  "data": {
    "total_users": 0,
    "active_users": 0,
    "staff_users": 0,
    "total_merchants": 0,
    "verified_merchants": 0,
    "pending_merchants": 0,
    "total_listings": 0,
    "active_listings": 0,
    "pending_listings": 0,
    "total_orders": 0,
    "new_orders": 0,
    "completed_orders": 0,
    "cancelled_orders": 0,
    "total_categories": 0,
    "total_images": 0
  }
}
```

---

## 2. User Management

### GET `/api/v1/admin/users/`

List all users with optional search and filtering.

**Query Parameters**

| Parameter   | Type    | Description                              |
|-------------|---------|------------------------------------------|
| `q`         | string  | Search by name, email, or username       |
| `is_staff`  | boolean | Filter by staff status (`true`/`false`)  |
| `is_active` | boolean | Filter by active status (`true`/`false`) |
| `page`      | integer | Page number (default: `1`)               |
| `page_size` | integer | Items per page (default: `20`, max: `100`) |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "name": "string",
      "email": "user@example.com",
      "username": "string",
      "phone": "string",
      "profile_image": "url",
      "is_active": true,
      "is_staff": false,
      "is_verified": false,
      "auth_provider": "string",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/api/v1/admin/users/{id}/`

Retrieve a single user by ID.

**Response `200`**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "string",
    "email": "user@example.com",
    "username": "string",
    "phone": "string",
    "profile_image": "url",
    "is_active": true,
    "is_staff": false,
    "is_verified": false,
    "auth_provider": "string",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Response `404`**
```json
{
  "success": false,
  "error": "User not found"
}
```

---

### PATCH `/api/v1/admin/users/{id}/`

Update user fields.

**Request Body**
```json
{
  "name": "string",
  "phone": "string",
  "is_active": true,
  "is_staff": false,
  "is_verified": false
}
```

**Response `200`** — Returns the updated user object (same shape as GET single user).

---

### DELETE `/api/v1/admin/users/{id}/`

Soft-deactivate a user (sets `is_active=False`).

**Response `200`**
```json
{
  "success": true,
  "message": "User deactivated"
}
```

**Response `400`** — When attempting to deactivate your own account
```json
{
  "success": false,
  "error": "You cannot deactivate your own account"
}
```

---

### POST `/api/v1/admin/users/{id}/make-staff/`

Grant staff access to a user.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "user@example.com granted staff access"
}
```

---

### POST `/api/v1/admin/users/{id}/revoke-staff/`

Revoke staff access from a user.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "user@example.com staff access revoked"
}
```

**Response `400`** — When attempting to revoke your own staff access
```json
{
  "success": false,
  "error": "You cannot revoke your own staff access"
}
```

---

## 3. Merchant Management

### GET `/api/v1/admin/merchants/`

List all merchants with optional search and filtering.

**Query Parameters**

| Parameter   | Type    | Description                                          |
|-------------|---------|------------------------------------------------------|
| `q`         | string  | Search by display_name, business_name, or user email |
| `verified`  | boolean | Filter by verification status (`true`/`false`)       |
| `status`    | string  | Filter by status (`ACTIVE`, `SUSPENDED`, `BANNED`)   |
| `page`      | integer | Page number (default: `1`)                           |
| `page_size` | integer | Items per page (default: `20`, max: `100`)           |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_name": "string",
      "user_email": "merchant@example.com",
      "display_name": "string",
      "business_name": "string",
      "description": "string",
      "business_phone": "string",
      "business_email": "business@example.com",
      "logo": "url",
      "cover_image": "url",
      "verified": false,
      "verification_date": "2024-01-01T00:00:00Z",
      "featured": false,
      "featured_order": 0,
      "rating": 0.0,
      "total_reviews": 0,
      "status": "ACTIVE",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/api/v1/admin/merchants/{id}/`

Retrieve a single merchant by ID.

**Response `200`** — Returns single merchant object (same shape as list item).

---

### PATCH `/api/v1/admin/merchants/{id}/`

Update merchant fields.

**Request Body**
```json
{
  "display_name": "string",
  "business_name": "string",
  "description": "string",
  "business_phone": "string",
  "business_email": "business@example.com",
  "verified": false,
  "verification_date": "2024-01-01T00:00:00Z",
  "featured": false,
  "featured_order": 0,
  "status": "ACTIVE",
  "rating": 0.0
}
```

**Response `200`** — Returns updated merchant object.

---

### DELETE `/api/v1/admin/merchants/{id}/`

Soft-delete a merchant.

**Response `200`**
```json
{
  "success": true,
  "message": "Merchant deleted"
}
```

---

### POST `/api/v1/admin/merchants/{id}/verify/`

Verify a merchant.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Merchant verified",
  "data": { }
}
```

---

### POST `/api/v1/admin/merchants/{id}/suspend/`

Suspend a merchant (sets `status=SUSPENDED`).

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Merchant suspended",
  "data": { }
}
```

---

### POST `/api/v1/admin/merchants/{id}/ban/`

Ban a merchant (sets `status=BANNED`).

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Merchant banned",
  "data": { }
}
```

---

## 4. Listing Management

### GET `/api/v1/admin/listings/`

List all listings (any status) with optional search and filtering.

**Query Parameters**

| Parameter     | Type    | Description                                                      |
|---------------|---------|------------------------------------------------------------------|
| `q`           | string  | Search by title, description, or merchant name                   |
| `status`      | string  | Filter by status (`ACTIVE`, `PENDING`, `REJECTED`, etc.)         |
| `merchant_id` | uuid    | Filter by merchant ID                                            |
| `category_id` | uuid    | Filter by category ID                                            |
| `is_verified` | boolean | Filter by verification status (`true`/`false`)                   |
| `page`        | integer | Page number (default: `1`)                                       |
| `page_size`   | integer | Items per page (default: `20`, max: `100`)                       |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "merchant_id": "uuid",
      "merchant_name": "string",
      "title": "string",
      "description": "string",
      "listing_type": "string",
      "category": "uuid",
      "category_name": "string",
      "price_type": "FIXED",
      "price": "100.00",
      "price_min": "50.00",
      "price_max": "150.00",
      "currency": "USD",
      "is_price_negotiable": false,
      "status": "ACTIVE",
      "is_verified": true,
      "is_featured": false,
      "featured_until": "2024-01-01T00:00:00Z",
      "views_count": 0,
      "contact_count": 0,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "deleted_at": null
    }
  ]
}
```

---

### GET `/api/v1/admin/listings/{id}/`

Retrieve a single listing by ID.

**Response `200`** — Returns single listing object (same shape as list item).

---

### PATCH `/api/v1/admin/listings/{id}/`

Update listing fields.

**Request Body**
```json
{
  "title": "string",
  "description": "string",
  "category": "uuid",
  "price_type": "FIXED",
  "price": "100.00",
  "price_min": "50.00",
  "price_max": "150.00",
  "currency": "USD",
  "status": "ACTIVE",
  "is_verified": true,
  "is_featured": false,
  "featured_until": "2024-01-01T00:00:00Z"
}
```

**Response `200`** — Returns updated listing object.

---

### DELETE `/api/v1/admin/listings/{id}/`

Soft-delete a listing.

**Response `200`**
```json
{
  "success": true,
  "message": "Listing deleted"
}
```

---

### POST `/api/v1/admin/listings/{id}/approve/`

Approve a listing (sets `status=ACTIVE`, `is_verified=True`).

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Listing approved",
  "data": { }
}
```

---

### POST `/api/v1/admin/listings/{id}/reject/`

Reject a listing (sets `status=REJECTED`, `is_verified=False`).

**Request Body**
```json
{
  "reason": "string (optional)"
}
```

**Response `200`**
```json
{
  "success": true,
  "message": "Listing rejected",
  "reason": "string",
  "data": { }
}
```

---

### POST `/api/v1/admin/listings/{id}/feature/`

Toggle listing featured status.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Listing featured",
  "data": { }
}
```

---

## 5. Category Management

### GET `/api/v1/admin/categories/`

List all categories (including inactive) with optional filtering.

**Query Parameters**

| Parameter     | Type    | Description                                        |
|---------------|---------|----------------------------------------------------|
| `q`           | string  | Search by name or description                      |
| `is_active`   | boolean | Filter by active status (`true`/`false`)           |
| `parent_only` | boolean | Only return top-level categories (no subcategories)|
| `page`        | integer | Page number (default: `1`)                         |
| `page_size`   | integer | Items per page (default: `20`, max: `100`)         |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "name": "string",
      "slug": "string",
      "description": "string",
      "icon": "url",
      "parent": "uuid",
      "parent_name": "string",
      "is_active": true,
      "is_featured": false,
      "sort_order": 0,
      "allows_order_intent": true,
      "allows_cart": true,
      "is_contact_only": false,
      "listings_count": 0,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/api/v1/admin/categories/{id}/`

Retrieve a single category by ID.

**Response `200`** — Returns single category object (same shape as list item).

---

### POST `/api/v1/admin/categories/`

Create a new category.

**Request Body**
```json
{
  "name": "string",
  "description": "string",
  "icon": "url",
  "parent": "uuid (optional)",
  "is_active": true,
  "is_featured": false,
  "sort_order": 0,
  "allows_order_intent": true,
  "allows_cart": true,
  "is_contact_only": false
}
```

**Response `201`**
```json
{
  "success": true,
  "data": { }
}
```

---

### PATCH `/api/v1/admin/categories/{id}/`

Update category fields. All fields are optional.

**Request Body** — Same fields as POST (all optional).

**Response `200`** — Returns updated category object.

---

### DELETE `/api/v1/admin/categories/{id}/`

Delete a category.

**Response `200`**
```json
{
  "success": true,
  "message": "Category deleted"
}
```

**Response `400`** — When the category has subcategories or active listings
```json
{
  "success": false,
  "error": "Cannot delete a category that has subcategories"
}
```

---

### POST `/api/v1/admin/categories/{id}/toggle-active/`

Toggle the active status of a category.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Category activated",
  "data": { }
}
```

---

## 6. Order Management

### GET `/api/v1/admin/orders/`

List all orders with optional search and filtering.

**Query Parameters**

| Parameter   | Type    | Description                                                              |
|-------------|---------|--------------------------------------------------------------------------|
| `q`         | string  | Search by order_number, buyer name/email, or merchant name               |
| `status`    | string  | Filter by status (`NEW`, `CONTACTED`, `CONFIRMED`, `COMPLETED`, `CANCELLED`) |
| `merchant_id` | uuid  | Filter by merchant ID                                                    |
| `buyer_id`  | uuid    | Filter by buyer ID                                                       |
| `date_from` | date    | Filter orders from date (`YYYY-MM-DD`)                                   |
| `date_to`   | date    | Filter orders up to date (`YYYY-MM-DD`)                                  |
| `page`      | integer | Page number (default: `1`)                                               |
| `page_size` | integer | Items per page (default: `20`, max: `100`)                               |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "order_number": "string",
      "status": "NEW",
      "buyer": "uuid",
      "buyer_name": "string",
      "buyer_email": "buyer@example.com",
      "buyer_phone": "string",
      "merchant": "uuid",
      "merchant_name": "string",
      "total_amount": "100.00",
      "delivery_fee": "10.00",
      "notes": "string",
      "cancellation_reason": "string",
      "cancelled_by": "string",
      "expected_delivery_date": "2024-01-01T00:00:00Z",
      "items": [
        {
          "id": "uuid",
          "listing_id": "uuid",
          "listing_title": "string",
          "quantity": 1,
          "unit_price": "100.00",
          "total_price": "100.00"
        }
      ],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/api/v1/admin/orders/{id}/`

Retrieve a single order by ID.

**Response `200`** — Returns single order object (same shape as list item).

---

### PATCH `/api/v1/admin/orders/{id}/`

Update order fields.

**Request Body**
```json
{
  "status": "NEW",
  "notes": "string",
  "cancellation_reason": "string",
  "cancelled_by": "string"
}
```

**Response `200`** — Returns updated order object.

---

### POST `/api/v1/admin/orders/{id}/update-status/`

Convenience endpoint to change an order's status.

**Request Body**
```json
{
  "status": "CONFIRMED",
  "notes": "string (optional)"
}
```

**Valid status values:** `NEW`, `CONTACTED`, `CONFIRMED`, `COMPLETED`, `CANCELLED`

**Response `200`**
```json
{
  "success": true,
  "message": "Order status updated to CONFIRMED",
  "data": { }
}
```

**Response `400`** — Invalid status value
```json
{
  "success": false,
  "error": "Invalid status. Must be one of: NEW, CONTACTED, CONFIRMED, COMPLETED, CANCELLED"
}
```

---

## 7. Image Management

### GET `/api/v1/admin/images/`

List all confirmed image assets.

**Query Parameters**

| Parameter    | Type    | Description                            |
|--------------|---------|----------------------------------------|
| `image_type` | string  | Filter by image type                   |
| `owner_id`   | uuid    | Filter by owner ID                     |
| `object_id`  | uuid    | Filter by object ID                    |
| `page`       | integer | Page number (default: `1`)             |
| `page_size`  | integer | Items per page (default: `20`, max: `100`) |

**Response `200`**
```json
{
  "count": 0,
  "total_pages": 0,
  "current_page": 1,
  "next": null,
  "previous": null,
  "success": true,
  "results": [
    {
      "id": "uuid",
      "owner": "uuid",
      "owner_email": "owner@example.com",
      "image_group_id": "uuid",
      "object_id": "uuid",
      "image_type": "string",
      "variant": "string",
      "s3_key": "string",
      "cdn_url": "url",
      "width": 1920,
      "height": 1080,
      "size_bytes": 1000000,
      "order": 0,
      "is_confirmed": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/api/v1/admin/images/{id}/`

Retrieve a single image asset by ID.

**Response `200`** — Returns single image object (same shape as list item).

---

### DELETE `/api/v1/admin/images/{id}/`

Delete an image record.

**Response `200`**
```json
{
  "success": true,
  "message": "Image deleted"
}
```

---

### GET `/api/v1/admin/images/orphans/`

List confirmed images with no `object_id` (draft or abandoned uploads).

**Query Parameters**

| Parameter   | Type    | Description                                |
|-------------|---------|--------------------------------------------|
| `page`      | integer | Page number (default: `1`)                 |
| `page_size` | integer | Items per page (default: `20`, max: `100`) |

**Response `200`** — Same paginated shape as the main images list.

---

### POST `/api/v1/admin/images/cleanup-orphans/`

Delete orphan images older than 24 hours.

**Request Body** — None

**Response `200`**
```json
{
  "success": true,
  "message": "Deleted 5 orphan image(s)"
}
```

---

## 8. Broadcast Notifications

Admin endpoints for scheduling push notifications or emails to all eligible active users.

### GET `/api/v1/admin/broadcasts/`

List scheduled and sent broadcast campaigns.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel` | string | Filter by `EMAIL` or `PUSH` |
| `status` | string | Filter by `SCHEDULED`, `SENDING`, `SENT`, `FAILED`, or `CANCELLED` |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

### POST `/api/v1/admin/broadcasts/schedule-email/`

Schedule an email broadcast to all active users with email addresses.

```json
{
  "title": "Weekend deals",
  "message": "New offers are live on Kakebe Shop.",
  "scheduled_at": "2026-04-27T12:00:00Z",
  "metadata": {
    "campaign": "weekend_deals"
  }
}
```

Use `"send_now": true` instead of `scheduled_at` to queue immediately.

### POST `/api/v1/admin/broadcasts/schedule-push/`

Schedule a push broadcast to all active users with active push tokens.

```json
{
  "title": "Price drops nearby",
  "message": "Check fresh listings from merchants near you.",
  "send_now": true
}
```

### POST `/api/v1/admin/broadcasts/`

Generic scheduler. Include `channel` as `EMAIL` or `PUSH`.

```json
{
  "channel": "PUSH",
  "title": "New arrivals",
  "message": "Fresh listings just landed.",
  "scheduled_at": "2026-04-27T12:00:00Z"
}
```

**Response `201`**

```json
{
  "success": true,
  "message": "Push broadcast scheduled",
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

### POST `/api/v1/admin/broadcasts/{id}/cancel/`

Cancel a campaign that is still `SCHEDULED`.
