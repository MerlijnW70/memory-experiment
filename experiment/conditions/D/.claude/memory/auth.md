---
name: Auth domein
description: Token validatie met thread-local side effect, middleware, role-based permissions
type: project
---

## Navigatie
- `src/auth/tokens.py::validate_token` — valideert token, **ZET thread-local current_user als side effect**
- `src/auth/tokens.py::get_current_user` — leest thread-local current_user, returnt None als niet gezet
- `src/auth/tokens.py::create_token` — genereert token voor user_id, slaat op in _token_store
- `src/auth/tokens.py::clear_current_user` — ruimt thread-local op na request
- `src/auth/middleware.py::authenticate` — extraheert token uit headers/params, roept validate_token aan
- `src/auth/middleware.py::require_auth` — decorator die authenticate wrapat
- `src/auth/permissions.py::has_permission` — checkt permissie tegen rol van current_user
- `src/auth/permissions.py::require_role` — decorator die rolcheck afdwingt

## Kritieke invariant
**validate_token() heeft een side effect**: het zet `_thread_local.current_user`. De payments module leest dit via `get_current_user()` zonder expliciete parameter. Als validate_token niet eerst aangeroepen is, faalt process_payment met RuntimeError.

Dit is een IMPLICIET CONTRACT — niet afdwingbaar via type systeem of imports.
