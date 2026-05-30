# Entity Guard for Home Assistant

Declarative state-enforcement rules. Bind one or more entities to a rule that defines a trigger condition and a desired target state — Entity Guard does the rest.

## Why

Replace N hand-written auto-off / kill-switch / curfew automations with a single rule per behaviour. Built-in cooldowns, suppression windows, rate limiting, observability, and per-rule status sensors.

## Status

This is the **0.0.1 scaffold** — package layout, manifest, and HACS metadata are in place. Runtime (state listeners, persistence, services, sensors, config flow, Lovelace card) lands in subsequent commits.

## Planned features

- Multi-entity rules — one rule binds 1+ target entities, each evaluated independently.
- Two modes — `state` (force entity to a target state) and `attribute` (clamp brightness / volume / temperature / percentage against a threshold).
- Flag conditions — optional list of `(entity, match_state)` AND'd; rule arms only when all match.
- Cooldown / debounce — per-entity cooldown after enforcement to avoid loop fights.
- Rate limit — per-rule cap on enforcements/minute; exceeding it auto-suppresses the rule.
- Suppress service — temporary pause with required duration; the `enabled` switch handles permanent disable.
- Synthetic Hub — single-instance config entry that owns the global master switch.
- Logbook integration — every enforcement is logged.
- Custom Lovelace card — visual rule status, recent enforcements, cooldown countdown, master toggle.

## Setup

1. Install via HACS (custom repository: `italo-lombardi/Home-Assistant-EntityGuard`).
2. **Settings → Devices & Services → Add Integration → Entity Guard**.

(Setup flow lands when the runtime ships.)
