# Changelog

## [0.1.0-beta.5] — 2026-05-31

### Added

- Status sensor `flags` attribute — exposes each configured flag with `entity`, `required`, `current`, `matches` so dashboards can see which conditions are unmet.
- Lovelace card `show_conditions` toggle (default off) — when enabled, renders a "Conditions" section listing each flag with current vs required state.

## [0.1.0-beta.4] — 2026-05-31

### Fixed

- `async_unload_entry` no longer unloads services when a hub entry remains — previously, removing the last rule would strip services even with the hub still active.
- `panic_stop` service now uses the correct dispatcher signal (`entity_guard_master_update`) — the master switch now updates instantly on panic stop.
- Debounce switch (`switch.<rule>_debounce_enabled`) now persists to entry **options** instead of `data` — fixes the case where a value set via options flow would shadow the toggle.
- Cooldown post-broadcast callback no longer leaks into `_unsub_callbacks` — entries are removed after they fire.

### Changed

- `flag_entity_ids` cached as `frozenset` on engine init — eliminates per-evaluation set rebuild.

## [0.1.0-beta.3] — 2026-05-31

### Changed

- Status `idle` renamed to `conditional` — the chip now reads "Waiting on conditions" when flag entities are configured but their states do not match the required values. Disambiguates from rules with no flags configured.

### Added

- New `error` status — surfaces after 3 consecutive enforcement failures (e.g. target entity unavailable). Auto-clears on next successful enforcement or via `clear_history` service. Status sensor exposes `consecutive_errors` and `last_error` attributes.
- Lovelace card shows an error banner with the failure detail when status is `error`.

### Fixed

- Card no longer flashes "No Entity Guard rule entities found" while the entity registry loads (rule selection or `show_entities` / `show_actions` toggle in the editor).
- All 11 translations updated for the new statuses.

## [0.1.0-beta.2] — 2026-05-31

### Fixed

- Prevent HA crash caused by unbounded task creation on rapid state changes — state events now deduplicate per entity, cancelling any still-pending evaluation before scheduling a new one
- Startup grace sweep and flag-change target sweep use same deduplication logic
- `rate_limit_window` cleanup changed from O(n) list comprehension to O(log n) bisect slice
- Pending eval tasks are cancelled on engine unload
- `engine.async_setup()` failure now returns `False` from `async_setup_entry` instead of crashing HA
- `_async_ensure_hub` spawned task is wrapped with exception handler — silent failure instead of unhandled exception
- Services (`suppress`, `unsuppress`, `clear_history`, `panic_stop`) now raise `HomeAssistantError` on failure instead of propagating raw exceptions to HA
- `async_unload_services` is now called when the last engine unloads — prevents stale service handlers on reload
- Binary sensors and rule/master switches now push initial state via `async_write_ha_state()` immediately on registration

## [0.1.0-beta.1] — 2026-05-31

First release of Entity Guard.

- Declarative rules keep entities in a desired state — lights off, switches locked, volume capped, and more
- Rules activate only when configured flag entities match their target states
- Built-in debounce, configurable delay, and rate limiting with automatic loop protection
- Suppress a rule temporarily from the dashboard or via service call
- Custom Lovelace card with live rule status, enforcement history, and bound entity compliance
- Every enforcement is recorded in the HA logbook
