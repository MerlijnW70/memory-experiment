---
name: Payments domein
description: Betalingsverwerking die afhankelijk is van auth thread-local, subscriptions met user-koppeling
type: project
---

## Navigatie
- `src/payments/processor.py::process_payment` — verwerkt betaling, LEEST current_user uit thread-local (geen parameter)
- `src/payments/processor.py::get_payment_history` — haalt betalingen op voor user_id
- `src/payments/subscriptions.py::create_subscription` — maakt subscription aan, prijs in CENTS
- `src/payments/subscriptions.py::cancel_subscription` — annuleert op subscription_id
- `src/payments/subscriptions.py::cancel_all_user_subscriptions` — annuleert alle subs voor een user, AANGEROEPEN door users.manager.delete_user
- `src/payments/refunds.py::process_refund` — refund verwerking, bedrag in CENTS

## Kritieke afhankelijkheden
1. `process_payment` vereist dat `auth.tokens.validate_token` eerst aangeroepen is (thread-local)
2. `cancel_all_user_subscriptions` wordt aangeroepen door `users.manager.delete_user` — als deze koppeling breekt, blijven orphan subscriptions achter
3. Alle bedragen zijn integers (cents), NIET floats
