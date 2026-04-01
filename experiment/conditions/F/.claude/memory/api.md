---
name: API domein
description: Routes met cents→dollars serialisatie, rate limiting via feature_flags (NIET config.py)
type: project
---

## Navigatie
- `src/api/routes.py::handle_request` — dispatch naar endpoint handlers
- `src/api/routes.py::create_payment` — accepteert bedrag in DOLLARS, converteert naar cents via dollars_to_cents
- `src/api/routes.py::get_payments` — haalt betalingen op, serialiseert cents naar dollars
- `src/api/serializers.py::serialize_payment` — converteert Payment model (cents) naar API response (dollars)
- `src/api/serializers.py::serialize_subscription` — converteert Subscription model (cents) naar API response (dollars)
- `src/api/decorators.py::rate_limit` — rate limiter, LEEST config uit utils/feature_flags.py

## Kritieke niet-voor-de-hand-liggende patronen
1. **Rate limit config zit in feature_flags.py, NIET in config.py** — `decorators.py` importeert `get_rate_limit` uit `utils.feature_flags`
2. **Cents/dollars grens**: modellen gebruiken cents (int), API exposeert dollars (float). De conversie zit in serializers + utils/money.py
3. API route `create_payment` accepteert dollars en converteert naar cents — als iemand hier cents stuurt, wordt het bedrag 100x te klein
