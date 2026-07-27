# SUPERSEDED — do not use

This project is dead. It has been replaced by `web/marktplaats`.

- **Successor:** `/Users/jurrejan/Documents/development/web/marktplaats`
  (`backend/` = `marktplaats-js`, a TypeScript/Bun port of this scraper; `frontend/` = SvelteKit 5 UI)
- **Superseded on:** 2026-07-27 (last commit here: 2026-03-29)
- **Where the code went:** the core Python source was carried over verbatim into
  `web/marktplaats/_reference/` (`client.py`, `providers/`, `data_mappers.py`,
  `MARKTPLAATS_API_SPEC.yaml`) as the reference implementation for the port.

## Kept only for

- `data/marktplaats_api.db`, `data/marktplaats_apix.db` — historical scrape data
- `tests/`, `scripts/` — not ported

Do not add features here, run it, or treat it as an active marktplaats project.
Anything marktplaats-related belongs in `web/marktplaats`.
