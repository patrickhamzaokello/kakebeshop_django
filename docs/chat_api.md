# Chat API Documentation

Base URL: `/api/v1/`

All endpoints require authentication (`Authorization: Bearer <token>`).

## Overview

Buyers initiate conversations with merchants. Merchants can reply after a conversation exists. Each sent message creates a chat notification for the other participant and queues notification delivery through the existing notification delivery system.

Conversation payloads include user profile pictures and merchant store profile data:

- Buyer/seller user profiles include `profile_image`.
- Merchant profiles include `store_name`, `profile_picture`, `logo`, and `cover_image`.

## Endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/conversations/` | List my chats |
| `GET` | `/api/v1/conversations/unread-count/` | Total unread chat messages |
| `POST` | `/api/v1/conversations/start/` | Buyer starts or resumes a chat with a merchant |
| `GET` | `/api/v1/conversations/{id}/` | Get one chat |
| `GET` | `/api/v1/conversations/{id}/messages/` | List messages in a chat |
| `POST` | `/api/v1/conversations/{id}/messages/` | Send a new message |
| `POST` | `/api/v1/conversations/{id}/mark-read/` | Mark received messages as read |

## Start Conversation

`POST /api/v1/conversations/start/`

Provide one of `merchant_id`, `listing_id`, or `order_intent_id`. If `listing_id` or `order_intent_id` is provided, the merchant is resolved from that object.

```json
{
  "listing_id": "uuid",
  "message": "Hi, is this still available?",
  "attachment": "https://example.com/file.jpg"
}
```

Response:

```json
{
  "success": true,
  "created": true,
  "conversation": {
    "id": "uuid",
    "buyer_profile": {
      "id": "uuid",
      "name": "Buyer Name",
      "email": "buyer@example.com",
      "phone": "+256...",
      "profile_image": "https://..."
    },
    "seller_profile": {
      "id": "uuid",
      "name": "Merchant User",
      "email": "merchant@example.com",
      "phone": "+256...",
      "profile_image": "https://..."
    },
    "merchant": {
      "id": "uuid",
      "store_name": "Store Name",
      "profile_picture": "https://...",
      "logo": "https://...",
      "cover_image": "https://..."
    },
    "last_message": {}
  },
  "message": {}
}
```

## Send Message

`POST /api/v1/conversations/{id}/messages/`

```json
{
  "message": "Yes, I can deliver today.",
  "attachment": ""
}
```

At least one of `message` or `attachment` is required.

## Read State

`POST /api/v1/conversations/{id}/mark-read/`

Marks all unread messages in the conversation that were sent by the other participant.

```json
{
  "success": true,
  "marked_read": 3
}
```
