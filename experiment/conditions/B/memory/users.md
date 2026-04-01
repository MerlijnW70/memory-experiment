---
name: Users domein
description: User CRUD met cascade-delete naar payment subscriptions, profielen, notificaties
type: project
---

## Navigatie
- `src/users/manager.py::create_user` — maakt user aan, stuurt welcome notificatie
- `src/users/manager.py::delete_user` — CASCADEERT: roept eerst cancel_all_user_subscriptions aan, dan verwijdert user
- `src/users/manager.py::get_user` — haalt user op uit store
- `src/users/manager.py::update_user` — update user velden
- `src/users/manager.py::list_users` — lijst alle users
- `src/users/profile.py::get_profile` — haalt profiel op, fallback display_name naar username
- `src/users/profile.py::update_profile` — update profiel met email-validatie
- `src/users/notifications.py::send_notification` — stub voor notificaties, logt naar structured logger

## Kritieke invariant
**delete_user MOET cancel_all_user_subscriptions aanroepen** voordat de user verwijderd wordt. Anders blijven orphan subscriptions achter die nooit geannuleerd worden.
