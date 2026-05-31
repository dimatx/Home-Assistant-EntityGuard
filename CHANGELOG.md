# Changelog

## [0.1.0-beta.1] — 2026-05-31

First release of Entity Guard.

- Declarative rules keep entities in a desired state — lights off, switches locked, volume capped, and more
- Rules activate only when configured flag entities match their target states
- Built-in debounce, configurable delay, and rate limiting with automatic loop protection
- Suppress a rule temporarily from the dashboard or via service call
- Custom Lovelace card with live rule status, enforcement history, and bound entity compliance
- Every enforcement is recorded in the HA logbook
