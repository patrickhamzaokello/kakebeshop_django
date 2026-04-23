# Phone Number API Documentation

Base URL: `/auth/`

All endpoints require authentication (`Authorization: Bearer <token>`).

---

## Flow Overview

```
User logs in
    │
    ▼
GET /auth/profile/
    │
    ├─ phone is not null ──► user goes to main app
    │
    └─ phone is null ──────► "Add Phone Number" screen
                                    │
                                    ▼
                          POST /auth/phone/add/
                                    │
                          ┌─────────┴──────────┐
                    details error          success or OTP error
                    (bad format /          (number saved)
                     already in use)            │
                          │               local flag set
                      show error          → main app
                      stay on screen
                                    (later, from profile settings)
                                                │
                                                ▼
                                    POST /auth/phone/verify/
                                    phone_verified = true on profile
```

---

## Profile

### Get Profile

**GET** `/auth/profile/`

Returns the authenticated user's full profile including phone fields.

**Response `200`**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+256787250196",
    "phone_verified": false,
    "profile_image": "https://...",
    "bio": "...",
    "is_verified": false,
    "intent": { "...": "..." },
    "onboarding": { "...": "..." }
  }
}
```

> `phone` is `null` if no number has been added. `phone_verified` is always present.

---

## Phone Endpoints

### Get Phone Status

**GET** `/auth/phone/status/`

Returns just the phone state for the authenticated user.

**Response `200`**
```json
{
  "phone": "+256787250196",
  "phone_verified": false,
  "has_phone": true
}
```

> `phone` is `null` and `has_phone` is `false` if no number has been added.

---

### Add Phone Number

**POST** `/auth/phone/add/`

Saves the phone number to the user record and sends an OTP via Twilio Verify.

**Request**
```json
{ "phone": "+256787250196" }
```

> Must include country code. Accepts E.164 format (e.g. `+256700000000`).

**Response `200` — Success**
```json
{
  "success": true,
  "message": "Verification code sent to +256787250196"
}
```

**Response `400` — Invalid format**
```json
{
  "error": "Validation failed",
  "details": {
    "phone": ["Enter a valid phone number."]
  }
}
```

**Response `400` — Number already in use**
```json
{
  "error": "Validation failed",
  "details": {
    "phone": ["This phone number is already registered to another account."]
  }
}
```

> Only blocked if the number belongs to a **verified** account. Unverified registrations do not block reuse.

**Response `500` — OTP delivery failure**
```json
{
  "error": "Failed to send verification code",
  "message": "..."
}
```

> The phone number is saved to the user record **before** Twilio is called. If OTP delivery fails, the number remains stored with `phone_verified: false`. The client should proceed past the gate on this error.

---

### Verify Phone Number

**POST** `/auth/phone/verify/`

Submits the OTP code the user received.

**Request**
```json
{ "code": "123456" }
```

> Must be exactly 6 digits.

**Response `200` — Success**
```json
{
  "success": true,
  "message": "Phone number verified successfully",
  "phone": "+256787250196",
  "verified": true
}
```

> Sets `phone_verified: true` on the user record. Reflected immediately on `GET /auth/profile/`.

**Response `200` — Already verified**
```json
{
  "success": true,
  "message": "Phone number is already verified",
  "phone": "+256787250196"
}
```

**Response `400` — Invalid or expired code**
```json
{
  "error": "Verification failed",
  "details": {
    "code": ["Invalid or expired verification code."]
  }
}
```

**Response `400` — No phone on account**
```json
{
  "error": "No phone number found",
  "message": "Please add a phone number first"
}
```

---

### Resend OTP

**POST** `/auth/phone/resend/`

Resends the OTP to the phone number already stored on the user record.

**Request**
```json
{ "phone": "+256787250196" }
```

> `phone` field is accepted but ignored — the stored number is always used.

**Response `200` — Success**
```json
{
  "success": true,
  "message": "Verification code resent successfully",
  "phone": "+256787250196",
  "expires_in": "10 minutes"
}
```

**Response `200` — Already verified**
```json
{
  "message": "Phone number is already verified",
  "phone": "+256787250196"
}
```

**Response `400` — No phone on account**
```json
{
  "error": "No phone number found",
  "message": "Please add a phone number first"
}
```

---

### Update Phone Number

**PUT** `/auth/phone/update/`

Replaces the stored phone number and sends a new OTP. Resets `phone_verified` to `false`.

**Request**
```json
{ "phone": "+256700000000" }
```

**Response `200` — Success**
```json
{
  "success": true,
  "message": "Phone number updated. Verification code sent.",
  "phone": "+256700000000",
  "verified": false,
  "expires_in": "10 minutes"
}
```

**Response `400` — Invalid format**
```json
{
  "error": "Validation failed",
  "details": {
    "phone": ["Enter a valid phone number."]
  }
}
```

**Response `400` — Number already in use**
```json
{
  "error": "Validation failed",
  "details": {
    "phone": ["This phone number is already in use by another account."]
  }
}
```

**Response `500` — OTP delivery failure**
```json
{
  "error": "Failed to send verification code",
  "message": "..."
}
```

> Same save-before-send guarantee as `/add/` — the number is updated on the record even if OTP delivery fails.

---

### Remove Phone Number

**DELETE** `/auth/phone/remove/`

Removes the phone number from the user record and resets `phone_verified` to `false`.

No request body required.

**Response `200` — Success**
```json
{
  "success": true,
  "message": "Phone number removed successfully"
}
```

**Response `200` — Nothing to remove**
```json
{
  "message": "No phone number to remove"
}
```

---

## Error Shape Reference

| Scenario | Status | Shape |
|---|---|---|
| Invalid phone format | 400 | `{ "error": "Validation failed", "details": { "phone": ["..."] } }` |
| Phone number already in use | 400 | `{ "error": "Validation failed", "details": { "phone": ["..."] } }` |
| Invalid OTP code | 400 | `{ "error": "Verification failed", "details": { "code": ["..."] } }` |
| No phone on account | 400 | `{ "error": "...", "message": "..." }` |
| Twilio / server failure | 500 | `{ "error": "...", "message": "..." }` |

> The app identifies errors to show the user by the presence of the `details` key. Responses without `details` are treated as service errors and the client proceeds.

---

## Twilio Configuration

The OTP service requires a Twilio Verify Service SID to be set on the server.

```
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

To get the SID: [Twilio Console](https://console.twilio.com) → Verify → Services → copy the `VA...` SID.

If this variable is empty, every `/add/` and `/resend/` call will return a `500` OTP delivery failure. The phone number will still be saved to the user record.
