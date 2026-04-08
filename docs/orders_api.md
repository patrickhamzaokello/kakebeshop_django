# Orders API Documentation

Base URL: `/api/v1/orders/`

All endpoints require authentication (`Authorization: Bearer <token>`).

---

## Order Status Flow

```
NEW → CONTACTED → CONFIRMED → COMPLETED
 └──────────────────────────→ CANCELLED
```

---

## Orders

### List Orders

**GET** `/api/v1/orders/`

Returns all orders where the authenticated user is the buyer. If the user has a merchant profile, also returns orders where they are the merchant.

**Response `200`**
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "id": "uuid",
      "order_number": "ORD-20260408-AB12CD",
      "buyer": {
        "name": "John Doe",
        "phone": "+255700000000",
        "email": "john@example.com"
      },
      "buyer_name": "John Doe",
      "merchant": "uuid",
      "merchant_name": "Shop Name",
      "address": {
        "id": "uuid",
        "user": "uuid",
        "label": "HOME",
        "region": "Dar es Salaam",
        "district": "Ilala",
        "area": "Kariakoo",
        "landmark": "Near the market",
        "latitude": "-6.8161",
        "longitude": "39.2803",
        "is_default": true,
        "created_at": "2026-04-08T10:00:00Z"
      },
      "notes": "Please handle with care",
      "total_amount": "55000.00",
      "delivery_fee": "5000.00",
      "expected_delivery_date": "2026-04-10",
      "status": "NEW",
      "created_at": "2026-04-08T10:00:00Z",
      "updated_at": "2026-04-08T10:00:00Z",
      "items": [
        {
          "id": "uuid",
          "listing": {
            "id": "uuid",
            "merchant": { "...": "MerchantListSerializer fields" },
            "title": "Product Name",
            "listing_type": "PRODUCT",
            "category_name": "Electronics",
            "price_type": "FIXED",
            "price": "50000.00",
            "price_min": null,
            "price_max": null,
            "currency": "TZS",
            "is_featured": false,
            "is_verified": true,
            "views_count": 120,
            "primary_image": {
              "id": "uuid",
              "image": "https://cdn.example.com/path/to/image.jpg",
              "width": 800,
              "height": 600,
              "variant": "thumb",
              "image_group_id": "uuid"
            },
            "created_at": "2026-01-01T00:00:00Z"
          },
          "quantity": 1,
          "unit_price": "50000.00",
          "total_price": "50000.00"
        }
      ],
      "order_group": "uuid or null",
      "order_group_number": "GRP-20260408-XY12 or null",
      "is_grouped": false
    }
  ]
}
```

---

### Get Single Order

**GET** `/api/v1/orders/{id}/`

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order ID |

**Response `200`**
```json
{
  "success": true,
  "data": { "...": "same as order object above" }
}
```

---

### My Orders (Filtered)

**GET** `/api/v1/orders/my-orders/`

Get orders with optional filtering by status and role.

**Query Parameters**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status: `NEW`, `CONTACTED`, `CONFIRMED`, `COMPLETED`, `CANCELLED` |
| `role` | string | No | Filter by role: `buyer` or `merchant` |

**Response `200`**
```json
{
  "success": true,
  "count": 1,
  "data": [ { "...": "same as order object" } ]
}
```

---

### Checkout

**POST** `/api/v1/orders/checkout/`

Creates orders from the authenticated user's cart. If the cart has items from multiple merchants, a separate order is created per merchant and they are grouped under an `OrderGroup`.

**Request Body**
```json
{
  "address_id": "uuid",
  "notes": "Handle with care",
  "delivery_fee": "5000.00",
  "expected_delivery_date": "2026-04-10"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address_id` | UUID | Yes | Delivery address ID (must belong to the user) |
| `notes` | string | No | Order notes |
| `delivery_fee` | decimal | No | Delivery fee amount |
| `expected_delivery_date` | date `YYYY-MM-DD` | No | Expected delivery date |

**Response `201`**
```json
{
  "success": true,
  "message": "Order(s) placed successfully",
  "data": {
    "orders": [ { "...": "array of order objects" } ],
    "order_group": {
      "id": "uuid",
      "group_number": "GRP-20260408-XY12",
      "total_orders": 2,
      "total_amount": "110000.00"
    }
  }
}
```

> `order_group` is `null` when all cart items belong to a single merchant.

**Error Responses**

`400` — Cart is empty
```json
{ "success": false, "error": "Cart is empty" }
```

`400` — Items unavailable
```json
{
  "success": false,
  "error": "Some items are no longer available",
  "details": [ { "...": "validation error details" } ]
}
```

`400` — Items missing fixed price
```json
{
  "success": false,
  "error": "Some items do not have a fixed price and cannot be checked out.",
  "details": [
    { "item_id": "uuid", "error": "\"Product Name\" has no fixed price and cannot be checked out. Please remove it from your cart." }
  ]
}
```

`404` — Cart not found
```json
{ "success": false, "error": "Cart not found" }
```

---

### Confirm Order (Merchant)

**POST** `/api/v1/orders/{id}/confirm/`

Merchant confirms an order. Order must have status `NEW` or `CONTACTED`.

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order ID |

**Request Body** — none required

**Response `200`**
```json
{
  "success": true,
  "message": "Order confirmed successfully",
  "data": { "...": "updated order object" }
}
```

**Error Responses**

`403` — Not the merchant
```json
{ "success": false, "error": "Only the merchant can confirm this order" }
```

`400` — Invalid status transition
```json
{ "success": false, "error": "Cannot confirm an order with status COMPLETED" }
```

---

### Complete Order (Merchant)

**POST** `/api/v1/orders/{id}/complete/`

Merchant marks an order as completed. Order must have status `CONFIRMED`.

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order ID |

**Request Body** — none required

**Response `200`**
```json
{
  "success": true,
  "message": "Order completed successfully",
  "data": { "...": "updated order object" }
}
```

**Error Responses**

`403` — Not the merchant
```json
{ "success": false, "error": "Only the merchant can complete this order" }
```

`400` — Invalid status
```json
{ "success": false, "error": "Cannot complete an order with status NEW. Order must be CONFIRMED first." }
```

---

### Update Order Status (Merchant)

**POST** `/api/v1/orders/{id}/update-status/`

General-purpose status update for merchant. Triggers a notification to the buyer automatically.

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order ID |

**Request Body**
```json
{
  "status": "CONFIRMED",
  "notes": "Your order has been confirmed and is being packed."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | One of: `NEW`, `CONTACTED`, `CONFIRMED`, `COMPLETED`, `CANCELLED` |
| `notes` | string | No | Optional notes appended to the order |

**Response `200`**
```json
{
  "success": true,
  "message": "Order status updated to CONFIRMED",
  "data": { "...": "updated order object" }
}
```

**Error Responses**

`403` — Not the merchant
```json
{ "success": false, "error": "Only the merchant can update order status" }
```

`400` — Invalid status value
```json
{ "success": false, "error": "Invalid status. Must be one of: NEW, CONTACTED, CONFIRMED, COMPLETED, CANCELLED" }
```

---

### Cancel Order (Buyer)

**POST** `/api/v1/orders/{id}/cancel/`

Buyer cancels their order. Cannot cancel orders that are already `COMPLETED` or `CANCELLED`. Triggers a notification to the merchant automatically.

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order ID |

**Request Body**
```json
{
  "reason": "Changed my mind"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | No | Cancellation reason (defaults to `"No reason provided"`) |

**Response `200`**
```json
{
  "success": true,
  "message": "Order cancelled successfully",
  "data": { "...": "updated order object with status CANCELLED" }
}
```

**Error Responses**

`403` — Not the buyer
```json
{ "success": false, "error": "Only the buyer can cancel their order" }
```

`400` — Already in a terminal state
```json
{ "success": false, "error": "Cannot cancel order with status COMPLETED" }
```

---

## Order Groups

An `OrderGroup` is created automatically during checkout when the cart contains items from more than one merchant.

---

### List Order Groups

**GET** `/api/v1/orders/order-groups/`

Returns all order groups for the authenticated buyer.

**Response `200`**
```json
{
  "success": true,
  "count": 1,
  "data": [
    {
      "id": "uuid",
      "group_number": "GRP-20260408-XY12",
      "buyer": "uuid",
      "buyer_name": "John Doe",
      "total_amount": "110000.00",
      "total_orders": 2,
      "created_at": "2026-04-08T10:00:00Z",
      "orders": [ { "...": "array of order objects" } ]
    }
  ]
}
```

---

### Get Single Order Group

**GET** `/api/v1/orders/order-groups/{id}/`

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order group ID |

**Response `200`**
```json
{
  "success": true,
  "data": { "...": "same as order group object above" }
}
```

---

### Get Orders in Group

**GET** `/api/v1/orders/order-groups/{id}/orders/`

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order group ID |

**Response `200`**
```json
{
  "success": true,
  "count": 2,
  "data": [ { "...": "array of order objects" } ]
}
```

---

### Update All Order Statuses in Group (Buyer)

**POST** `/api/v1/orders/order-groups/{id}/update-all-statuses/`

Bulk cancel all non-terminal orders in the group. Only `CANCELLED` status is accepted. Orders already in `COMPLETED` or `CANCELLED` are skipped. Triggers notifications automatically for each updated order.

**Path Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Order group ID |

**Request Body**
```json
{
  "status": "CANCELLED",
  "notes": "Cancelling the entire order"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | Must be `CANCELLED` |
| `notes` | string | No | Notes added to each updated order |

**Response `200`**
```json
{
  "success": true,
  "message": "Updated 2 orders to CANCELLED",
  "data": { "...": "updated order group object" }
}
```

**Error Responses**

`403` — Not the buyer
```json
{ "success": false, "error": "Only the buyer can update order group status" }
```

`400` — Unsupported status
```json
{ "success": false, "error": "Only CANCELLED status is allowed for order groups" }
```

---

## Common Error Responses

| Code | Meaning |
|------|---------|
| `401` | Unauthenticated — missing or invalid token |
| `403` | Forbidden — authenticated but not authorized for this action |
| `404` | Resource not found |
| `400` | Bad request — validation error or invalid state transition |
| `500` | Server error — unexpected failure |
