---
name: Architectuurbeslissingen
description: Kernbeslissingen en hun rationale — waarom de code zo is als die is
type: project
---

## Beslissing 1: Thread-local voor authenticatiecontext
**Wat:** validate_token zet current_user als thread-local in plaats van het als parameter door te geven.
**Waarom:** Vermijdt dat elke functie in de call chain een user parameter nodig heeft. Simuleert request-scoped context zoals in web frameworks.
**Risico:** Impliciete koppeling — code die current_user leest faalt stil als validate_token niet eerst aangeroepen is.

## Beslissing 2: Cents als interne representatie
**Wat:** Alle monetaire bedragen intern als int (cents), API exposeert als float (dollars).
**Waarom:** Voorkomt floating-point afrondingsfouten bij berekeningen. Standaardpatroon in betalingssystemen.
**Risico:** Conversiefouten aan de API-grens. Wie dollars stuurt waar cents verwacht wordt, krijgt 100x verkeerd bedrag.

## Beslissing 3: Rate limit config in feature_flags
**Wat:** Rate limiting configuratie zit in utils/feature_flags.py, niet in config.py.
**Waarom:** Rate limits moeten runtime aanpasbaar zijn zonder herstart. feature_flags.py ondersteunt dynamische wijzigingen, config.py niet.
**Risico:** Ontwikkelaars zoeken rate limit config in config.py en vinden het niet.

## Beslissing 4: Cascade delete via applicatielaag
**Wat:** delete_user roept cancel_all_user_subscriptions aan in applicatiecode, niet via database constraints.
**Waarom:** Geen echte database — in-memory stores. Cascade moet expliciet in code.
**Risico:** Als iemand een alternatieve delete-path toevoegt zonder de cascade, blijven orphan subscriptions achter.
