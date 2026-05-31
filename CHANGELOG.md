# Changelog

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
