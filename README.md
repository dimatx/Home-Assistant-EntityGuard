# Entity Guard

Home Assistant custom integration that enforces desired entity state via declarative rules. Replaces hand-written auto-off / kill-switch / cooldown automations.

> **Status:** scaffolding — not functional yet.

## Why

You set up rules like:

- "Auto-lock the front door 10 seconds after it's unlocked."
- "Kids' TV off after 30 minutes."
- "When the diffuser reports low water, immediately turn the mist off and keep it off until the tank is refilled."
- "After midnight, force the kids' lights off if anyone turns them on."
- "Garage door auto-closes 5 minutes after it's left open."

Without Entity Guard you build N hand-written automations that all look almost the same. Entity Guard collapses them into one rule per behaviour, with built-in cooldowns, suppression windows, rate limiting, persistence, and observability.

## Status

This is the **0.0.1 scaffold** — package layout, manifest, and HACS metadata are in place. The runtime (state listeners, persistence, services, sensors, config flow) lands in subsequent commits.

See `custom_components/entity_guard/` for the package skeleton.

## Concepts (planned)

- **Rule** — a config entry binding 1+ target entities to a trigger condition and an enforcement action.
- **Mode** — `state` (force entity to a target state when it enters a trigger state) or `attribute` (clamp a numeric attribute against a threshold).
- **Flag** — optional list of `(entity, match_state)` conditions, AND'd. Rule only fires when all flags match.
- **Cooldown / debounce** — optional per-entity cooldown after enforcement, to avoid loop fights.
- **Rate limit** — per-rule cap on enforcements/minute. Exceeding it auto-suppresses the rule.
- **Suppress** — temporary pause via service (`entity_guard.suppress`, with required duration). Use the `enabled` switch for permanent pause.
- **Hub** — single synthetic config entry that owns the global master switch.

## Sibling integrations

- [Entity Availability](https://github.com/italo-lombardi/Home-Assistant-EntityAvailability)
- [Entity Distance](https://github.com/italo-lombardi/Home-Assistant-EntityDistance)
- [Fuel Compare](https://github.com/italo-lombardi/Home-Assistant-FuelCompare)

## License

GPL-3.0. See `LICENSE`.
