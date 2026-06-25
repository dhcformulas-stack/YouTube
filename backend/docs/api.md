# Chronicle Forge API Documentation

Base URL: `http://localhost:8000/api`

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:
```
Authorization: Bearer <jwt-token>
```

### `GET /api/health`
Returns service status. No auth required.

## Auth Endpoints

### `POST /api/auth/signup`
Register a new account.
**Body:** `{ "email", "password", "name" }`

### `POST /api/auth/login`
Authenticate and receive a JWT.
**Body:** `{ "email", "password" }`

### `GET /api/auth/me`
Get current user profile and active subscription. **Auth required.**

### `PUT /api/auth/profile`
Update user profile. **Auth required.** **Body:** `{ "name" }`

## Subscription Endpoints

### `GET /api/subscriptions/tiers`
List available subscription tiers. Public.

### `POST /api/subscriptions/create-checkout`
Create a Stripe Checkout Session. **Auth required.**
**Body:** `{ "tier": "starter|intermediate|gold", "successUrl?", "cancelUrl?" }`

### `GET /api/subscriptions/my`
Get current user's subscription. **Auth required.**

### `POST /api/subscriptions/cancel`
Cancel subscription. **Auth required.**

## Tiers

| Tier | Price | Videos/Month |
|------|-------|-------------|
| Starter | $99.00/mo | 1 |
| Intermediate | $249.99/mo | 2 |
| Gold | $499.99/mo | 4 |

## Order / Video Brief Endpoints

### `POST /api/orders`
Submit a new video brief. **Auth required.** Requires active subscription (admins bypass).
**Body:** `{ "title", "topic", "angle?", "details?", "references?" }`

### `GET /api/orders`
List user's orders. **Auth required.**

### `GET /api/orders/:id`
Get a single order. **Auth required.**

### `DELETE /api/orders/:id`
Cancel order in "received" status. **Auth required.**

### `PUT /api/orders/:id/status`
Update order status. **Auth required** (must be owner).
**Body:** `{ "status", "videoUrl?" }`

Valid statuses: `received → researching → scripting → production → rendering → delivered`

## Stripe Webhook

### `POST /api/stripe/webhook`
Handles: checkout.session.completed, invoice.paid/failed, customer.subscription.updated/deleted.

## Admin Endpoints (require `role: "admin"` in JWT)

### `GET /api/admin/stats`
Dashboard statistics.

### `GET /api/admin/users`
List all users. **Query:** `status?`, `limit?`, `offset?`

### `GET /api/admin/users/:id`
Get user with subscription and orders.

### `GET /api/admin/orders`
List all orders. **Query:** `status?`, `limit?`, `offset?`

### `GET /api/admin/orders/:id`
Get any order by ID with user info.

### `PUT /api/admin/orders/:id/status`
Update any order's status. **Body:** `{ "status", "videoUrl?" }`

## Admin User
Seeded on first startup. Default credentials:
- Email: `admin@chronicleforge.com` / Password: `admin123`
- Configurable via `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME` env vars.
- Admins bypass Stripe subscription checks and have unlimited video submissions.

## Environment Variables

| Variable | Description |
|---|---|
| `PORT` | Server port (default: 8000) |
| `HOST` | Bind address (default: 0.0.0.0) |
| `JWT_SECRET` | Secret key for JWT signing |
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret |
| `FRONTEND_URL` | Frontend URL for CORS |
| `ADMIN_EMAIL` | Admin email (default: admin@chronicleforge.com) |
| `ADMIN_PASSWORD` | Admin password (default: admin123) |
| `ADMIN_NAME` | Admin name (default: Admin) |