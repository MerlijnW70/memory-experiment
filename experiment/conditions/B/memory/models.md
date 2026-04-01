---
name: Models domein
description: Datamodellen met strikte typechecks, bedragen altijd int cents
type: project
---

## Navigatie
- `src/models/user.py::User` — dataclass, velden: id, username, email, role, is_active
- `src/models/payment.py::Payment` — dataclass, amount_cents MOET int zijn (__post_init__ TypeError), status enum
- `src/models/subscription.py::Subscription` — dataclass, price_cents (int), status, user_id koppeling

## Invariant
Alle monetaire velden zijn `int` (cents). `Payment.__post_init__` gooit `TypeError` als `amount_cents` geen int is. Dit vangt fouten vroeg maar de foutmelding wijst niet naar de cents/dollars conversie als oorzaak.
