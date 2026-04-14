# Comments API Documentation

Base URL: `/api/v1/`

All endpoints require authentication (`Authorization: Bearer <token>`).

---

## Overview

Comments are scoped to listings. A comment can optionally be a **reply** to another top-level comment (one level of nesting only). Comments are soft-deleted — they are never permanently removed from the database.

### Pagination

List endpoints use page-number pagination.

| Query Param | Default | Max |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 20 | 100 |

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/listings/{listing_id}/comments/` | List top-level comments for a listing |
| `POST` | `/api/v1/listings/{listing_id}/comments/` | Post a comment or reply on a listing |
| `GET` | `/api/v1/listings/{listing_id}/comments/total/` | Get total comment count for a listing |
| `GET` | `/api/v1/listing-comments/{id}/` | Retrieve a single comment |
| `PATCH` | `/api/v1/listing-comments/{id}/` | Edit a comment (owner only) |
| `DELETE` | `/api/v1/listing-comments/{id}/` | Delete a comment (owner only) |
| `GET` | `/api/v1/listing-comments/{id}/replies/` | List paginated replies for a comment |

---

## 1. List Comments

**GET** `/api/v1/listings/{listing_id}/comments/`

Returns paginated top-level (non-reply) comments for the given listing, ordered by most recent first. Deleted comments are excluded.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `listing_id` | UUID | The listing to fetch comments for |

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page (default: 20, max: 100) |

**Response `200`**
```json
{
  "count": 42,
  "next": "https://example.com/api/v1/listings/{listing_id}/comments/?page=2",
  "previous": null,
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "listing": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "parent": null,
      "user_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "user_name": "Jane Doe",
      "body": "Is this item still available?",
      "reply_count": 2,
      "is_owner": false,
      "created_at": "2026-04-10T14:22:00Z",
      "updated_at": "2026-04-10T14:22:00Z"
    }
  ]
}
```

---

## 2. Create Comment or Reply

**POST** `/api/v1/listings/{listing_id}/comments/`

Posts a new top-level comment or a reply to an existing comment on a listing. The listing must be `ACTIVE`.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `listing_id` | UUID | The listing to comment on |

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `body` | string | Yes | Comment text (1–2000 characters) |
| `parent` | UUID | No | ID of the comment being replied to (must belong to the same listing; cannot reply to a reply) |

> **Note:** When posting via the nested URL (`/listings/{listing_id}/comments/`), the `listing` field is resolved from the URL and should **not** be included in the body.

**Request Example — Top-level comment**
```json
{
  "body": "Is this item still available?"
}
```

**Request Example — Reply**
```json
{
  "body": "Yes, it is!",
  "parent": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response `201`**
```json
{
  "success": true,
  "comment": {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "listing": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "parent": null,
    "user_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "user_name": "Jane Doe",
    "body": "Is this item still available?",
    "reply_count": 0,
    "is_owner": true,
    "created_at": "2026-04-13T09:00:00Z",
    "updated_at": "2026-04-13T09:00:00Z"
  }
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | `body` is empty or exceeds 2000 characters |
| `400` | `parent` does not belong to this listing |
| `400` | `parent` is itself a reply (no nested replies allowed) |
| `400` | `parent` comment has been deleted |
| `404` | Listing not found or not `ACTIVE` |

---

## 3. Get Total Comment Count

**GET** `/api/v1/listings/{listing_id}/comments/total/`

Returns the total number of non-deleted comments (including replies) for a listing.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `listing_id` | UUID | The listing to count comments for |

**Response `200`**
```json
{
  "listing_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "total_comments": 42
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `404` | Listing not found |

---

## 4. Retrieve a Single Comment

**GET** `/api/v1/listing-comments/{id}/`

Returns a single comment by its ID. Deleted comments are excluded.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | The comment ID |

**Response `200`**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "listing": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "parent": null,
  "user_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "user_name": "Jane Doe",
  "body": "Is this item still available?",
  "reply_count": 2,
  "is_owner": false,
  "created_at": "2026-04-10T14:22:00Z",
  "updated_at": "2026-04-10T14:22:00Z"
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `404` | Comment not found or deleted |

---

## 5. Edit a Comment

**PATCH** `/api/v1/listing-comments/{id}/`

Updates the body of an existing comment. Only the comment owner can edit their own comment.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | The comment ID |

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `body` | string | Yes | Updated comment text (1–2000 characters) |

**Request Example**
```json
{
  "body": "Updated comment text here."
}
```

**Response `200`**
```json
{
  "success": true,
  "comment": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "listing": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "parent": null,
    "user_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "user_name": "Jane Doe",
    "body": "Updated comment text here.",
    "reply_count": 2,
    "is_owner": true,
    "created_at": "2026-04-10T14:22:00Z",
    "updated_at": "2026-04-13T10:05:00Z"
  }
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `400` | `body` is empty or exceeds 2000 characters |
| `403` | Authenticated user is not the comment owner |
| `404` | Comment not found or deleted |

---

## 6. Delete a Comment

**DELETE** `/api/v1/listing-comments/{id}/`

Soft-deletes a comment. The record is kept in the database but excluded from all list and retrieve responses. Only the comment owner can delete their own comment.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | The comment ID |

**Response `200`**
```json
{
  "success": true,
  "message": "Comment deleted."
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `403` | Authenticated user is not the comment owner |
| `404` | Comment not found or already deleted |

---

## 7. List Replies for a Comment

**GET** `/api/v1/listing-comments/{id}/replies/`

Returns paginated replies for a specific comment, ordered by oldest first. Deleted replies are excluded.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | The parent comment ID |

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page (default: 20, max: 100) |

**Response `200`**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "user_name": "John Smith",
      "body": "Yes, still available!",
      "is_owner": false,
      "created_at": "2026-04-11T08:15:00Z",
      "updated_at": "2026-04-11T08:15:00Z"
    }
  ]
}
```

**Error Responses**

| Status | Condition |
|---|---|
| `404` | Parent comment not found or deleted |

---

## Response Object Reference

### Comment Object (full)

Returned by List, Retrieve, Create, and Edit endpoints.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique comment identifier |
| `listing` | UUID | ID of the listing this comment belongs to |
| `parent` | UUID \| null | ID of the parent comment if this is a reply; `null` for top-level comments |
| `user_id` | UUID | ID of the user who posted the comment |
| `user_name` | string | Display name of the user who posted the comment |
| `body` | string | Comment text |
| `reply_count` | integer | Number of non-deleted replies to this comment |
| `is_owner` | boolean | `true` if the authenticated user is the comment author |
| `created_at` | datetime (ISO 8601) | When the comment was created |
| `updated_at` | datetime (ISO 8601) | When the comment was last edited |

### Reply Object (lightweight)

Returned only by the **List Replies** endpoint.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique reply identifier |
| `user_id` | UUID | ID of the user who posted the reply |
| `user_name` | string | Display name of the user who posted the reply |
| `body` | string | Reply text |
| `is_owner` | boolean | `true` if the authenticated user is the reply author |
| `created_at` | datetime (ISO 8601) | When the reply was created |
| `updated_at` | datetime (ISO 8601) | When the reply was last edited |

---

## Business Rules

- **One level of nesting only:** Replies cannot themselves be replied to.
- **Soft delete:** Deleted comments and replies remain in the database with `is_deleted=true` and are excluded from all responses.
- **Listing must be active:** Comments can only be posted on listings with status `ACTIVE`.
- **Owner-only mutations:** Only the user who created a comment can edit or delete it.
- **Body length:** Comment and reply bodies must be between 1 and 2000 characters.
