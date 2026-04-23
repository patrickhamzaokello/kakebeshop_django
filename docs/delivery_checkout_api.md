# Delivery & Checkout API — Frontend Reference

**Audience:** Frontend / mobile developers
**Feature:** Delivery mode selection during order placement
**Base URL:** `/api/v1/`

All endpoints require `Authorization: Bearer <access_token>`.

---

## Delivery Mode Reference

| Mode | Label | Typical use |
|---|---|---|
| `PICKUP` | Pickup | Buyer collects from merchant location |
| `DELIVERY` | Delivery | Merchant delivers to buyer's address |
| `DIGITAL` | Digital | Download / link (digital products) |
| `IN_PERSON` | In Person | Service performed on-site at buyer location |
| `REMOTE` | Remote | Service performed online / remotely |

---

## Flow Overview

```
User views listing
    │
    ▼
GET /listings/{id}/
    └─ read delivery_modes[] to know what's available
            │
            ▼
User adds to cart
            │
            ▼
User opens checkout screen
    │
    ├─ GET /cart/                 ← show cart items and totals
    ├─ GET /location/addresses/   ← let user pick delivery address
    │
    └─ For each merchant in cart:
         read delivery_modes[] from listings
         show available modes and fees to user
         user picks one mode per merchant*
            │
            ▼
POST /orders/orders/checkout/
    └─ include delivery_mode + delivery_fee
            │
            ▼
Order placed → status: NEW
```

> \* The current checkout creates one order per merchant in the cart.
> The same `delivery_mode` and `delivery_fee` are applied to all merchants
> in a single checkout call. If your cart has items from multiple merchants
> with different modes, either split into separate checkouts or apply the
> most common mode and fee.

---

## Step 1 — Read delivery modes from a listing

### `GET /listings/{id}/`

Returns full listing detail including all configured delivery modes.

**Response `200`**
```json
{
  "id": "uuid",
  "title": "Laptop Stand",
  "listing_type": "PRODUCT",
  "price": 45000,
  "currency": "UGX",
  "delivery_modes": [
    {
      "id": "uuid",
      "mode": "PICKUP",
      "mode_display": "Pickup",
      "notes": "Available Mon–Fri, 9am–5pm",
      "delivery_fee": null,
      "estimated_days": null
    },
    {
      "id": "uuid",
      "mode": "DELIVERY",
      "mode_display": "Delivery",
      "notes": "Kampala only",
      "delivery_fee": "5000.00",
      "estimated_days": 1
    }
  ],
  "..."
}
```

> `delivery_fee: null` means free. `estimated_days: null` means not specified.
> The list endpoint (`GET /listings/`) returns a lightweight version:
> `"delivery_modes": ["PICKUP", "DELIVERY"]` — strings only, no fee details.

---

## Step 2 — Show cart contents

### `GET /cart/`

Returns the current cart with all items grouped by merchant.

**Response `200`**
```json
{
  "id": "uuid",
  "items": [
    {
      "id": "uuid",
      "listing": {
        "id": "uuid",
        "title": "Laptop Stand",
        "merchant": { "id": "uuid", "display_name": "Tech Shop" },
        "price": 45000,
        "delivery_modes": ["PICKUP", "DELIVERY"]
      },
      "quantity": 1,
      "subtotal": 45000
    }
  ],
  "total": 45000,
  "item_count": 1
}
```

> Use the `delivery_modes` array on each listing to determine which modes
> are available. Fetch `GET /listings/{id}/` for the fee and notes per mode
> before showing the checkout delivery selection screen.

---

## Step 3 — Pick a delivery address

### `GET /location/addresses/`

Returns the authenticated user's saved addresses.

**Response `200`**
```json
{
  "results": [
    {
      "id": "uuid",
      "label": "Home",
      "street": "Kampala Road",
      "city": "Kampala",
      "country": "UG",
      "is_default": true
    }
  ]
}
```

> For `PICKUP`, `DIGITAL`, and `REMOTE` modes an address is still required
> by the order model but may be shown as optional in the UI — use the
> user's default address as a fallback.

---

## Step 4 — Place the order

### `POST /orders/orders/checkout/`

Places orders from the entire cart. Creates one `OrderIntent` per merchant.

**Request body**
```json
{
  "address_id": "uuid",
  "delivery_mode": "DELIVERY",
  "delivery_fee": 5000,
  "expected_delivery_date": "2026-04-25",
  "notes": "Leave at the gate"
}
```

| Field | Required | Notes |
|---|---|---|
| `address_id` | Yes | UUID of the user's saved address |
| `delivery_mode` | No | One of: `PICKUP`, `DELIVERY`, `DIGITAL`, `IN_PERSON`, `REMOTE` |
| `delivery_fee` | No | Numeric. Pass the fee from the listing's chosen delivery mode. `null` or omit for free |
| `expected_delivery_date` | No | ISO date `YYYY-MM-DD`. Pass if the mode has `estimated_days` |
| `notes` | No | Free text for the merchant |

**Success `201`**
```json
{
  "success": true,
  "message": "Order(s) placed successfully",
  "data": {
    "orders": [
      {
        "id": "uuid",
        "order_number": "ORD-20260423-AB12CD",
        "status": "NEW",
        "delivery_mode": "DELIVERY",
        "delivery_fee": "5000.00",
        "expected_delivery_date": "2026-04-25",
        "total_amount": "50000.00",
        "merchant_name": "Tech Shop",
        "address": {
          "street": "Kampala Road",
          "city": "Kampala"
        },
        "items": [
          {
            "listing": { "title": "Laptop Stand", "..." },
            "quantity": 1,
            "unit_price": "45000.00",
            "total_price": "45000.00"
          }
        ],
        "buyer": {
          "name": "John Doe",
          "phone": "+256787250196",
          "email": "john@example.com"
        },
        "created_at": "2026-04-23T10:00:00Z"
      }
    ],
    "order_group": null
  }
}
```

> `order_group` is non-null when the cart had items from more than one
> merchant — all orders in the group share a `group_number` for tracking.

**Empty cart — `400`**
```json
{ "success": false, "error": "Cart is empty" }
```

**Items unavailable — `400`**
```json
{
  "success": false,
  "error": "Some items are no longer available",
  "details": [{ "item_id": "uuid", "error": "..." }]
}
```

**Item missing price — `400`**
```json
{
  "success": false,
  "error": "Some items do not have a fixed price and cannot be checked out.",
  "details": [{ "item_id": "uuid", "error": "..." }]
}
```

---

## Step 5 — Order confirmation (merchant side)

After the order is placed the merchant receives a notification and confirms.

### `POST /orders/orders/{id}/confirm/`

No request body. Merchant only.

**Response `200`**
```json
{
  "success": true,
  "message": "Order confirmed successfully",
  "data": { "...order..." }
}
```

---

## How to compute `delivery_fee` in the UI

```
1. Fetch GET /listings/{id}/ for each item in cart
2. Find the delivery_mode object matching the user's selection
3. Read delivery_fee from that object
4. Sum delivery fees across merchants if multi-merchant cart
5. Pass total delivery_fee to POST /orders/orders/checkout/
```

**Example:**

| Listing | Mode chosen | Fee |
|---|---|---|
| Laptop Stand (Tech Shop) | `DELIVERY` | 5,000 UGX |
| Phone Case (Mobile Hub) | `PICKUP` | 0 UGX |

→ `delivery_fee: 5000` passed to checkout (fee for the merchant that charges one)

> If the cart spans multiple merchants, consider breaking checkout into
> separate calls per merchant so each order gets its own correct fee and mode.

---

## Delivery mode UI guidance

| Mode | Show address picker? | Show fee? | Show est. days? |
|---|---|---|---|
| `PICKUP` | No (show merchant location if available) | No | No |
| `DELIVERY` | Yes | Yes | Yes |
| `DIGITAL` | No | No | No |
| `IN_PERSON` | Yes (buyer's location) | Yes | Yes |
| `REMOTE` | No | No | No |

---

## Order status flow (for reference)

```
NEW → CONTACTED → CONFIRMED → COMPLETED
 └──────────────────────────→ CANCELLED
```

The buyer can read order status from:

### `GET /orders/orders/{id}/`

```json
{
  "success": true,
  "data": {
    "order_number": "ORD-20260423-AB12CD",
    "status": "NEW",
    "delivery_mode": "DELIVERY",
    "delivery_fee": "5000.00",
    "expected_delivery_date": "2026-04-25",
    "..."
  }
}
```
