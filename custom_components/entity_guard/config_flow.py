"""Config and options flow for the Entity Guard integration."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ATTRIBUTE,
    CONF_DEBOUNCE_ENABLED,
    CONF_DEBOUNCE_SECONDS,
    CONF_DELAY_SECONDS,
    CONF_ENTRY_TYPE,
    CONF_FLAG_ENTITY,
    CONF_FLAG_MATCH_STATE,
    CONF_FLAGS,
    CONF_MAX_ENFORCEMENTS_PER_MINUTE,
    CONF_MODE,
    CONF_OPERATOR,
    CONF_RULE_ID,
    CONF_RULE_NAME,
    CONF_SAFETY_ACKNOWLEDGED,
    CONF_TARGET_ENTITIES,
    CONF_TARGET_STATE,
    CONF_TARGET_VALUE,
    CONF_THRESHOLD,
    CONF_TRIGGER_STATES,
    DEFAULT_DEBOUNCE_ENABLED,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_MAX_ENFORCEMENTS_PER_MINUTE,
    DEFAULT_TARGET_STATE,
    DEFAULT_TRIGGER_STATES,
    DOMAIN,
    ENTRY_TYPE_HUB,
    ENTRY_TYPE_RULE,
    MAX_DEBOUNCE_SECONDS,
    MAX_DELAY_SECONDS,
    MAX_RATE_LIMIT,
    MIN_DEBOUNCE_SECONDS,
    MIN_DELAY_SECONDS,
    MIN_RATE_LIMIT,
    MODE_ATTRIBUTE,
    MODE_STATE,
    SAFETY_DOMAINS,
    SUPPORTED_ATTRIBUTES,
    SUPPORTED_OPERATORS,
)

_LOGGER = logging.getLogger(__name__)


def _has_safety_target(entities: list[str]) -> bool:
    """Return True when any entity belongs to a safety-sensitive domain."""
    # SAFETY_DOMAINS gate the safety_acknowledged checkbox; cheap split avoids registry lookups.
    return any(entity_id.split(".", 1)[0] in SAFETY_DOMAINS for entity_id in entities)


def _rule_name_taken(
    hass_entries: list[ConfigEntry], name: str, ignore_entry_id: str | None = None
) -> bool:
    """Return True if another rule entry already owns ``name``."""
    lowered = name.strip().lower()
    for entry in hass_entries:
        if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_RULE:
            continue
        if ignore_entry_id is not None and entry.entry_id == ignore_entry_id:
            continue
        if str(entry.data.get(CONF_RULE_NAME, entry.title)).strip().lower() == lowered:
            return True
    return False


def _build_summary(data: dict[str, Any]) -> str:
    """Build the human-readable preview shown before saving."""
    lines: list[str] = []
    lines.append(f"Name: {data.get(CONF_RULE_NAME, '')}")
    lines.append(f"Targets: {', '.join(data.get(CONF_TARGET_ENTITIES, []))}")
    mode = data.get(CONF_MODE)
    lines.append(f"Mode: {mode}")
    if mode == MODE_STATE:
        lines.append(
            f"Trigger states: {', '.join(data.get(CONF_TRIGGER_STATES, []))}"
        )
        lines.append(f"Target state: {data.get(CONF_TARGET_STATE, '')}")
    elif mode == MODE_ATTRIBUTE:
        lines.append(
            f"Attribute: {data.get(CONF_ATTRIBUTE)} "
            f"{data.get(CONF_OPERATOR)} {data.get(CONF_THRESHOLD)} "
            f"-> {data.get(CONF_TARGET_VALUE)}"
        )
    lines.append(f"Delay: {data.get(CONF_DELAY_SECONDS, 0)}s")
    flags = data.get(CONF_FLAGS, [])
    if flags:
        flag_strs = [f"{f[CONF_FLAG_ENTITY]}={f[CONF_FLAG_MATCH_STATE]}" for f in flags]
        lines.append(f"Flags (AND): {', '.join(flag_strs)}")
    else:
        lines.append("Flags: (none)")
    if data.get(CONF_DEBOUNCE_ENABLED):
        lines.append(f"Debounce: {data.get(CONF_DEBOUNCE_SECONDS)}s")
    else:
        lines.append("Debounce: disabled")
    lines.append(
        f"Rate limit: {data.get(CONF_MAX_ENFORCEMENTS_PER_MINUTE)} per minute"
    )
    if data.get(CONF_SAFETY_ACKNOWLEDGED):
        lines.append("Safety acknowledged: yes")
    return "\n".join(lines)


def _delay_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_DELAY_SECONDS,
            max=MAX_DELAY_SECONDS,
            step=1,
            unit_of_measurement="seconds",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _debounce_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_DEBOUNCE_SECONDS,
            max=MAX_DEBOUNCE_SECONDS,
            step=1,
            unit_of_measurement="seconds",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _rate_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_RATE_LIMIT,
            max=MAX_RATE_LIMIT,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _number_selector() -> selector.NumberSelector:
    # Threshold/target_value: unbounded numeric input — engine clamps domain-specifically.
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, step="any"
        )
    )


def _trigger_states_selector() -> selector.SelectSelector:
    # custom_value=True lets users add domain-specific states (locked, paused, ...).
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["on", "off", "open", "closed", "locked", "unlocked", "playing"],
            multiple=True,
            custom_value=True,
        )
    )


class EntityGuardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Entity Guard."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._rule_data: dict[str, Any] = {}
        self._flags: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial menu: pick a rule or set up the hub."""
        return self.async_show_menu(step_id="user", menu_options=["rule", "hub"])

    # ------------------------------------------------------------------ Hub

    async def async_step_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm-only step that creates the singleton hub entry."""
        # Hub is single-instance; second attempt aborts cleanly.
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_HUB:
                return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_hub")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Entity Guard Hub",
                data={CONF_ENTRY_TYPE: ENTRY_TYPE_HUB},
            )

        return self.async_show_form(step_id="hub", data_schema=vol.Schema({}))

    # ------------------------------------------------------------------ Rule basics

    async def async_step_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rule basics: name, target entities, mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = str(user_input[CONF_RULE_NAME]).strip()
            entities = user_input.get(CONF_TARGET_ENTITIES, [])

            if not name:
                errors[CONF_RULE_NAME] = "empty_rule_name"
            elif _rule_name_taken(
                self.hass.config_entries.async_entries(DOMAIN), name
            ):
                return self.async_abort(reason="name_already_exists")
            elif not entities:
                errors[CONF_TARGET_ENTITIES] = "empty_target_entities"

            if not errors:
                # UUID created here, frozen for the lifetime of the entry.
                rule_uuid = str(uuid.uuid4())
                await self.async_set_unique_id(rule_uuid)
                self._abort_if_unique_id_configured()

                self._rule_data = {
                    CONF_ENTRY_TYPE: ENTRY_TYPE_RULE,
                    CONF_RULE_ID: rule_uuid,
                    CONF_RULE_NAME: name,
                    CONF_TARGET_ENTITIES: entities,
                    CONF_MODE: user_input[CONF_MODE],
                    CONF_FLAGS: [],
                }
                if user_input[CONF_MODE] == MODE_STATE:
                    return await self.async_step_state()
                return await self.async_step_attribute()

        schema = vol.Schema(
            {
                vol.Required(CONF_RULE_NAME): str,
                vol.Required(CONF_TARGET_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                ),
                vol.Required(CONF_MODE, default=MODE_STATE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[MODE_STATE, MODE_ATTRIBUTE],
                        translation_key="mode",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="rule", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ State mode

    async def async_step_state(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """State-mode step: trigger states, target state, delay."""
        errors: dict[str, str] = {}

        if user_input is not None:
            triggers = user_input.get(CONF_TRIGGER_STATES, [])
            target = str(user_input.get(CONF_TARGET_STATE, "")).strip()
            if not triggers:
                errors[CONF_TRIGGER_STATES] = "empty_trigger_states"
            elif not target:
                errors[CONF_TARGET_STATE] = "empty_target_state"
            else:
                self._rule_data[CONF_TRIGGER_STATES] = triggers
                self._rule_data[CONF_TARGET_STATE] = target
                self._rule_data[CONF_DELAY_SECONDS] = int(
                    user_input[CONF_DELAY_SECONDS]
                )
                return await self.async_step_flags()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TRIGGER_STATES, default=DEFAULT_TRIGGER_STATES
                ): _trigger_states_selector(),
                vol.Required(CONF_TARGET_STATE, default=DEFAULT_TARGET_STATE): str,
                vol.Required(
                    CONF_DELAY_SECONDS, default=DEFAULT_DELAY_SECONDS
                ): _delay_selector(),
            }
        )
        return self.async_show_form(
            step_id="state", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ Attribute mode

    async def async_step_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Attribute-mode step: attribute, operator, threshold, target value, delay."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                threshold = float(user_input[CONF_THRESHOLD])
                target_value = float(user_input[CONF_TARGET_VALUE])
            except (TypeError, ValueError):
                errors["base"] = "invalid_threshold"
            else:
                self._rule_data[CONF_ATTRIBUTE] = user_input[CONF_ATTRIBUTE]
                self._rule_data[CONF_OPERATOR] = user_input[CONF_OPERATOR]
                self._rule_data[CONF_THRESHOLD] = threshold
                self._rule_data[CONF_TARGET_VALUE] = target_value
                self._rule_data[CONF_DELAY_SECONDS] = int(
                    user_input[CONF_DELAY_SECONDS]
                )
                return await self.async_step_flags()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ATTRIBUTE, default=SUPPORTED_ATTRIBUTES[0]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SUPPORTED_ATTRIBUTES,
                        translation_key="attribute",
                    )
                ),
                vol.Required(
                    CONF_OPERATOR, default=SUPPORTED_OPERATORS[0]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SUPPORTED_OPERATORS,
                        translation_key="operator",
                    )
                ),
                vol.Required(CONF_THRESHOLD): _number_selector(),
                vol.Required(CONF_TARGET_VALUE): _number_selector(),
                vol.Required(
                    CONF_DELAY_SECONDS, default=DEFAULT_DELAY_SECONDS
                ): _delay_selector(),
            }
        )
        return self.async_show_form(
            step_id="attribute", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ Flags (repeating)

    async def async_step_flags(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional repeating step to collect flag conditions (AND'd)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity = user_input.get(CONF_FLAG_ENTITY)
            match_state = user_input.get(CONF_FLAG_MATCH_STATE, "")
            add_another = user_input.get("add_another", False)

            # Both fields must be set together; an empty pair just skips ahead.
            if entity and str(match_state).strip():
                self._flags.append(
                    {
                        CONF_FLAG_ENTITY: entity,
                        CONF_FLAG_MATCH_STATE: str(match_state).strip(),
                    }
                )
            elif entity or str(match_state).strip():
                errors["base"] = "incomplete_flag"

            if not errors and not add_another:
                self._rule_data[CONF_FLAGS] = self._flags
                return await self.async_step_advanced()

        schema = vol.Schema(
            {
                vol.Optional(CONF_FLAG_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig()
                ),
                vol.Optional(CONF_FLAG_MATCH_STATE, default=""): str,
                vol.Optional("add_another", default=False): selector.BooleanSelector(),
            }
        )
        description_placeholders = {
            "count": str(len(self._flags)),
            "summary": ", ".join(
                f"{f[CONF_FLAG_ENTITY]}={f[CONF_FLAG_MATCH_STATE]}" for f in self._flags
            )
            or "(none)",
        }
        return self.async_show_form(
            step_id="flags",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    # ------------------------------------------------------------------ Advanced

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Advanced step: debounce + per-rule rate limit."""
        if user_input is not None:
            self._rule_data[CONF_DEBOUNCE_ENABLED] = bool(
                user_input[CONF_DEBOUNCE_ENABLED]
            )
            self._rule_data[CONF_DEBOUNCE_SECONDS] = int(
                user_input[CONF_DEBOUNCE_SECONDS]
            )
            self._rule_data[CONF_MAX_ENFORCEMENTS_PER_MINUTE] = int(
                user_input[CONF_MAX_ENFORCEMENTS_PER_MINUTE]
            )

            if _has_safety_target(self._rule_data[CONF_TARGET_ENTITIES]):
                return await self.async_step_safety()
            return await self.async_step_preview()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEBOUNCE_ENABLED, default=DEFAULT_DEBOUNCE_ENABLED
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_DEBOUNCE_SECONDS, default=DEFAULT_DEBOUNCE_SECONDS
                ): _debounce_selector(),
                vol.Required(
                    CONF_MAX_ENFORCEMENTS_PER_MINUTE,
                    default=DEFAULT_MAX_ENFORCEMENTS_PER_MINUTE,
                ): _rate_selector(),
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema)

    # ------------------------------------------------------------------ Safety ack

    async def async_step_safety(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Safety acknowledgment for cover/lock/climate targets."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_SAFETY_ACKNOWLEDGED, False):
                errors[CONF_SAFETY_ACKNOWLEDGED] = "safety_not_acknowledged"
            else:
                self._rule_data[CONF_SAFETY_ACKNOWLEDGED] = True
                return await self.async_step_preview()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SAFETY_ACKNOWLEDGED, default=False
                ): selector.BooleanSelector(),
            }
        )
        safety_targets = [
            e
            for e in self._rule_data.get(CONF_TARGET_ENTITIES, [])
            if e.split(".", 1)[0] in SAFETY_DOMAINS
        ]
        return self.async_show_form(
            step_id="safety",
            data_schema=schema,
            errors=errors,
            description_placeholders={"entities": ", ".join(safety_targets)},
        )

    # ------------------------------------------------------------------ Preview

    async def async_step_preview(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Final confirmation that creates the rule entry."""
        if user_input is not None and user_input.get("confirm"):
            return self.async_create_entry(
                title=self._rule_data[CONF_RULE_NAME],
                data=self._rule_data,
            )

        schema = vol.Schema(
            {vol.Required("confirm", default=True): selector.BooleanSelector()}
        )
        return self.async_show_form(
            step_id="preview",
            data_schema=schema,
            description_placeholders={"summary": _build_summary(self._rule_data)},
        )

    # ------------------------------------------------------------------ Options entry

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> EntityGuardOptionsFlow:
        """Return the options flow handler for a rule entry."""
        return EntityGuardOptionsFlow()


class EntityGuardOptionsFlow(OptionsFlow):
    """Options flow for editing an existing rule entry."""

    def __init__(self) -> None:
        """Initialize."""
        self._working: dict[str, Any] = {}

    # ------------------------------------------------------------------ Init / menu

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Top-level options menu — Hub entries are read-only."""
        if self.config_entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_HUB:
            return self.async_abort(reason="hub_no_options")

        # Snapshot existing data once; each sub-step mutates ``_working`` and saves.
        if not self._working:
            self._working = dict(self.config_entry.data)
            self._working.setdefault(CONF_FLAGS, [])

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "edit_basics",
                "edit_mode",
                "edit_entities",
                "edit_flags",
                "edit_advanced",
            ],
        )

    # ------------------------------------------------------------------ Persist helper

    def _save(self) -> ConfigFlowResult:
        """Write working copy back without touching unique_id / rule_id."""
        # rule_id and unique_id are immutable; merge into stored data only.
        self._working[CONF_RULE_ID] = self.config_entry.data.get(CONF_RULE_ID)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=self._working,
            title=self._working.get(CONF_RULE_NAME, self.config_entry.title),
        )
        return self.async_create_entry(title="", data={})

    # ------------------------------------------------------------------ Basics

    async def async_step_edit_basics(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = str(user_input[CONF_RULE_NAME]).strip()
            if not name:
                errors[CONF_RULE_NAME] = "empty_rule_name"
            elif _rule_name_taken(
                self.hass.config_entries.async_entries(DOMAIN),
                name,
                ignore_entry_id=self.config_entry.entry_id,
            ):
                return self.async_abort(reason="name_already_exists")
            else:
                self._working[CONF_RULE_NAME] = name
                return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_RULE_NAME, default=self._working.get(CONF_RULE_NAME, "")
                ): str,
            }
        )
        return self.async_show_form(
            step_id="edit_basics", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ Entities

    async def async_step_edit_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit target entities (add/remove)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities = user_input.get(CONF_TARGET_ENTITIES, [])
            if not entities:
                errors[CONF_TARGET_ENTITIES] = "empty_target_entities"
            else:
                self._working[CONF_TARGET_ENTITIES] = entities
                # New safety domain present? Force re-ack if not already given.
                if (
                    _has_safety_target(entities)
                    and not self._working.get(CONF_SAFETY_ACKNOWLEDGED, False)
                ):
                    return await self.async_step_edit_safety()
                return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TARGET_ENTITIES,
                    default=self._working.get(CONF_TARGET_ENTITIES, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                ),
            }
        )
        return self.async_show_form(
            step_id="edit_entities", data_schema=schema, errors=errors
        )

    async def async_step_edit_safety(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-acknowledge safety after adding cover/lock/climate targets."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_SAFETY_ACKNOWLEDGED):
                errors[CONF_SAFETY_ACKNOWLEDGED] = "safety_not_acknowledged"
            else:
                self._working[CONF_SAFETY_ACKNOWLEDGED] = True
                return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SAFETY_ACKNOWLEDGED, default=False
                ): selector.BooleanSelector()
            }
        )
        return self.async_show_form(
            step_id="edit_safety", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ Mode-specific

    async def async_step_edit_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dispatch to the correct mode-specific edit step."""
        if self._working.get(CONF_MODE) == MODE_STATE:
            return await self.async_step_edit_state()
        return await self.async_step_edit_attribute()

    async def async_step_edit_state(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit state-mode parameters."""
        errors: dict[str, str] = {}

        if user_input is not None:
            triggers = user_input.get(CONF_TRIGGER_STATES, [])
            target = str(user_input.get(CONF_TARGET_STATE, "")).strip()
            if not triggers:
                errors[CONF_TRIGGER_STATES] = "empty_trigger_states"
            elif not target:
                errors[CONF_TARGET_STATE] = "empty_target_state"
            else:
                self._working[CONF_TRIGGER_STATES] = triggers
                self._working[CONF_TARGET_STATE] = target
                self._working[CONF_DELAY_SECONDS] = int(
                    user_input[CONF_DELAY_SECONDS]
                )
                return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TRIGGER_STATES,
                    default=self._working.get(
                        CONF_TRIGGER_STATES, DEFAULT_TRIGGER_STATES
                    ),
                ): _trigger_states_selector(),
                vol.Required(
                    CONF_TARGET_STATE,
                    default=self._working.get(CONF_TARGET_STATE, DEFAULT_TARGET_STATE),
                ): str,
                vol.Required(
                    CONF_DELAY_SECONDS,
                    default=self._working.get(
                        CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS
                    ),
                ): _delay_selector(),
            }
        )
        return self.async_show_form(
            step_id="edit_state", data_schema=schema, errors=errors
        )

    async def async_step_edit_attribute(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit attribute-mode parameters."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                threshold = float(user_input[CONF_THRESHOLD])
                target_value = float(user_input[CONF_TARGET_VALUE])
            except (TypeError, ValueError):
                errors["base"] = "invalid_threshold"
            else:
                self._working[CONF_ATTRIBUTE] = user_input[CONF_ATTRIBUTE]
                self._working[CONF_OPERATOR] = user_input[CONF_OPERATOR]
                self._working[CONF_THRESHOLD] = threshold
                self._working[CONF_TARGET_VALUE] = target_value
                self._working[CONF_DELAY_SECONDS] = int(
                    user_input[CONF_DELAY_SECONDS]
                )
                return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ATTRIBUTE,
                    default=self._working.get(CONF_ATTRIBUTE, SUPPORTED_ATTRIBUTES[0]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SUPPORTED_ATTRIBUTES, translation_key="attribute"
                    )
                ),
                vol.Required(
                    CONF_OPERATOR,
                    default=self._working.get(CONF_OPERATOR, SUPPORTED_OPERATORS[0]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SUPPORTED_OPERATORS, translation_key="operator"
                    )
                ),
                vol.Required(
                    CONF_THRESHOLD, default=self._working.get(CONF_THRESHOLD, 0)
                ): _number_selector(),
                vol.Required(
                    CONF_TARGET_VALUE, default=self._working.get(CONF_TARGET_VALUE, 0)
                ): _number_selector(),
                vol.Required(
                    CONF_DELAY_SECONDS,
                    default=self._working.get(
                        CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS
                    ),
                ): _delay_selector(),
            }
        )
        return self.async_show_form(
            step_id="edit_attribute", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------ Flags

    async def async_step_edit_flags(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit flag list — pass JSON-friendly compact representation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            action = user_input.get("action", "save")
            if action == "clear":
                self._working[CONF_FLAGS] = []
                return self._save()

            entity = user_input.get(CONF_FLAG_ENTITY)
            match_state = str(user_input.get(CONF_FLAG_MATCH_STATE, "")).strip()
            existing = list(self._working.get(CONF_FLAGS, []))

            if action == "add":
                if not entity or not match_state:
                    errors["base"] = "incomplete_flag"
                else:
                    existing.append(
                        {
                            CONF_FLAG_ENTITY: entity,
                            CONF_FLAG_MATCH_STATE: match_state,
                        }
                    )
                    self._working[CONF_FLAGS] = existing
                    return self._save()
            else:
                self._working[CONF_FLAGS] = existing
                return self._save()

        flags = self._working.get(CONF_FLAGS, [])
        summary = (
            ", ".join(
                f"{f[CONF_FLAG_ENTITY]}={f[CONF_FLAG_MATCH_STATE]}" for f in flags
            )
            or "(none)"
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_FLAG_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig()
                ),
                vol.Optional(CONF_FLAG_MATCH_STATE, default=""): str,
                vol.Required(
                    "action", default="save"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["save", "add", "clear"],
                        translation_key="flag_action",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="edit_flags",
            data_schema=schema,
            errors=errors,
            description_placeholders={"summary": summary},
        )

    # ------------------------------------------------------------------ Advanced

    async def async_step_edit_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit debounce + rate limit."""
        if user_input is not None:
            self._working[CONF_DEBOUNCE_ENABLED] = bool(
                user_input[CONF_DEBOUNCE_ENABLED]
            )
            self._working[CONF_DEBOUNCE_SECONDS] = int(
                user_input[CONF_DEBOUNCE_SECONDS]
            )
            self._working[CONF_MAX_ENFORCEMENTS_PER_MINUTE] = int(
                user_input[CONF_MAX_ENFORCEMENTS_PER_MINUTE]
            )
            return self._save()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEBOUNCE_ENABLED,
                    default=self._working.get(
                        CONF_DEBOUNCE_ENABLED, DEFAULT_DEBOUNCE_ENABLED
                    ),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_DEBOUNCE_SECONDS,
                    default=self._working.get(
                        CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS
                    ),
                ): _debounce_selector(),
                vol.Required(
                    CONF_MAX_ENFORCEMENTS_PER_MINUTE,
                    default=self._working.get(
                        CONF_MAX_ENFORCEMENTS_PER_MINUTE,
                        DEFAULT_MAX_ENFORCEMENTS_PER_MINUTE,
                    ),
                ): _rate_selector(),
            }
        )
        return self.async_show_form(step_id="edit_advanced", data_schema=schema)
