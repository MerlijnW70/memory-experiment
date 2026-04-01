---
name: Utils domein
description: Gedeelde utilities — geldconversie, feature flags (bevat rate limit config!), validatie, logging
type: project
---

## Navigatie
- `src/utils/money.py::cents_to_dollars` — int cents → float dollars (/ 100)
- `src/utils/money.py::dollars_to_cents` — float dollars → int cents (round + int)
- `src/utils/feature_flags.py::get_feature_flag` — leest feature flags uit interne dict
- `src/utils/feature_flags.py::get_rate_limit` — **RATE LIMIT CONFIG ZIT HIER**, niet in config.py
- `src/utils/feature_flags.py::set_feature_flag` — dynamisch flags wijzigen (runtime)
- `src/utils/validation.py::validate_email` — email format validatie
- `src/utils/validation.py::validate_amount` — checkt of bedrag positief getal is
- `src/utils/logging.py::get_logger` — structured logger factory

## Niet-voor-de-hand-liggend
feature_flags.py bevat MEER dan feature flags — het is de runtime configuratiebron voor rate limiting, maintenance mode, en andere operationele settings. De naam is misleidend.
