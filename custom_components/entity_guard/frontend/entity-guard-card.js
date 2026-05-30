/**
 * Entity Guard Card v0.0.1
 * Custom Lovelace card for the Home Assistant Entity Guard integration.
 *
 * Config:
 *   type: custom:entity-guard-card
 *   rule_id: <config_entry_id>   # required
 *   title: <optional override>
 */

const CARD_VERSION = "0.0.1";

console.info(
  `%c ENTITY-GUARD-CARD %c v${CARD_VERSION} %c — github.com/italo-lombardi `,
  "color: white; background: #3f51b5; font-weight: bold; padding: 2px 6px; border-radius: 3px 0 0 3px;",
  "color: #3f51b5; background: #e8eaf6; font-weight: bold; padding: 2px 6px;",
  "color: #9e9e9e; background: #e8eaf6; padding: 2px 6px; border-radius: 0 3px 3px 0;"
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "entity-guard-card",
  name: "Entity Guard Card",
  description: "Status, controls, and history for an Entity Guard rule.",
  preview: true,
  documentationURL:
    "https://github.com/italo-lombardi/Home-Assistant-EntityGuard",
});

const LitElement = Object.getPrototypeOf(
  customElements.get("home-assistant-main") || customElements.get("hui-view")
);
const html = LitElement.prototype.html;
const nothing = LitElement.prototype.nothing ?? "";
const css = LitElement.prototype.css;

const STATUS_COLORS = {
  disabled: "#9e9e9e",
  suppressed: "#ff9800",
  enforcing: "#2196f3",
  cooldown: "#ffc107",
  armed: "#4caf50",
  idle: "#bdbdbd",
};

const STATUS_LABELS = {
  disabled: "Disabled",
  suppressed: "Suppressed",
  enforcing: "Enforcing",
  cooldown: "Cooldown",
  armed: "Armed",
  idle: "Idle",
};

const cardStyles = css`
  :host {
    --eg-text-primary: var(--primary-text-color, #212121);
    --eg-text-secondary: var(--secondary-text-color, #727272);
    --eg-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
  }
  ha-card { overflow: hidden; }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px 10px;
    gap: 10px;
  }
  .title {
    font-size: 16px;
    font-weight: 500;
    color: var(--eg-text-primary);
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .badge {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #fff;
    padding: 3px 8px;
    border-radius: 10px;
    white-space: nowrap;
  }
  .divider {
    height: 1px;
    background: var(--eg-divider);
    margin: 0 16px;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    font-size: 13px;
  }
  .row .label {
    color: var(--eg-text-secondary);
  }
  .row .value {
    color: var(--eg-text-primary);
    font-weight: 500;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 60%;
  }
  .stats {
    display: flex;
    padding: 8px 16px;
    gap: 8px;
  }
  .stat {
    flex: 1;
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 6px;
    padding: 8px 10px;
    text-align: center;
  }
  .stat-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--eg-text-primary);
  }
  .stat-label {
    font-size: 11px;
    color: var(--eg-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 2px;
  }
  .entities {
    padding: 4px 16px 8px;
  }
  .section-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--eg-text-secondary);
    padding: 8px 0 4px;
  }
  .entity-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 13px;
  }
  .entity-name {
    flex: 1;
    color: var(--eg-text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .entity-state {
    color: var(--eg-text-secondary);
    white-space: nowrap;
  }
  .actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding: 8px 16px 14px;
  }
  button.action {
    flex: 1;
    min-width: 90px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid var(--eg-divider);
    border-radius: 4px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    cursor: pointer;
    transition: opacity 0.2s;
  }
  button.action:hover { opacity: 0.8; }
  button.action.primary {
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    border-color: transparent;
  }
  button.action.warn {
    background: var(--warning-color, #ff9800);
    color: var(--text-primary-color, #fff);
    border-color: transparent;
  }
  .toggle {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .error {
    padding: 16px;
    color: var(--error-color, #db4437);
    font-size: 13px;
  }
`;

class EntityGuardCard extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
    };
  }

  static get styles() {
    return cardStyles;
  }

  static getConfigElement() {
    return document.createElement("entity-guard-card-editor");
  }

  static getStubConfig(hass) {
    const ruleEntities = Object.keys(hass?.states || {}).filter(
      (id) => id.startsWith("switch.") && id.endsWith("_enabled")
    );
    return { rule_id: "", title: "" };
  }

  setConfig(config) {
    if (!config || (!config.rule_id && !config.entity)) {
      throw new Error(
        "entity-guard-card: 'rule_id' (config_entry_id) is required."
      );
    }
    this._config = { ...config };
  }

  getCardSize() {
    return 4;
  }

  /**
   * Locate all per-rule entities by scanning the state registry for the rule_id.
   * Falls back to anchor entity prefix when only `entity` was given.
   */
  _findRuleEntities() {
    if (!this.hass) return null;
    const ruleId = this._config.rule_id;
    const anchor = this._config.entity;
    const out = {
      enabled: null,
      status: null,
      lastEnforced: null,
      countToday: null,
      countTotal: null,
      armed: null,
      active: null,
      inCooldown: null,
      reset: null,
      testEnforce: null,
      bound: [],
    };

    const entities = this.hass.entities || {};
    const matches = [];
    for (const [entityId, entry] of Object.entries(entities)) {
      if (entry?.platform !== "entity_guard") continue;
      if (ruleId && entry?.config_entry_id !== ruleId) continue;
      if (!ruleId && anchor && !entityId.startsWith(this._anchorPrefix(anchor))) {
        continue;
      }
      matches.push(entityId);
    }

    for (const id of matches) {
      const st = this.hass.states[id];
      if (!st) continue;
      const tk = st.attributes?.translation_key;
      if (id.startsWith("switch.") && (tk === "enabled" || /(_|^)enabled$/.test(id))) {
        if (!tk || tk === "enabled") out.enabled = id;
      } else if (id.startsWith("sensor.") && tk === "status") {
        out.status = id;
      } else if (id.startsWith("sensor.") && tk === "last_enforced") {
        out.lastEnforced = id;
      } else if (id.startsWith("sensor.") && tk === "enforcement_count_today") {
        out.countToday = id;
      } else if (id.startsWith("sensor.") && tk === "enforcement_count_total") {
        out.countTotal = id;
      } else if (id.startsWith("binary_sensor.") && tk === "armed") {
        out.armed = id;
      } else if (id.startsWith("binary_sensor.") && tk === "active") {
        out.active = id;
      } else if (id.startsWith("binary_sensor.") && tk === "in_cooldown") {
        out.inCooldown = id;
      } else if (id.startsWith("button.") && tk === "reset") {
        out.reset = id;
      } else if (id.startsWith("button.") && tk === "test_enforce") {
        out.testEnforce = id;
      }
    }

    const statusEntity = out.status ? this.hass.states[out.status] : null;
    const targets = statusEntity?.attributes?.target_entities;
    if (Array.isArray(targets)) {
      out.bound = targets;
    }

    return out;
  }

  _anchorPrefix(anchorId) {
    return anchorId.replace(/_enabled$/, "");
  }

  _stateValue(entityId, fallback = "—") {
    if (!entityId) return fallback;
    const st = this.hass.states[entityId];
    if (!st) return fallback;
    if (st.state === "unavailable" || st.state === "unknown") return fallback;
    return st.state;
  }

  _attrValue(entityId, attr) {
    if (!entityId) return null;
    return this.hass.states[entityId]?.attributes?.[attr] ?? null;
  }

  _formatTimestamp(value) {
    if (!value) return "Never";
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleString();
  }

  _ruleName(refs) {
    if (this._config.title) return this._config.title;
    const statusEntity = refs.status ? this.hass.states[refs.status] : null;
    const friendly = statusEntity?.attributes?.friendly_name;
    if (friendly) return friendly.replace(/\s*Status$/i, "");
    return "Entity Guard Rule";
  }

  render() {
    if (!this._config || !this.hass) {
      return html`<ha-card><div class="error">Card not configured.</div></ha-card>`;
    }

    const refs = this._findRuleEntities();
    if (!refs || (!refs.status && !refs.enabled)) {
      return html`<ha-card>
        <div class="error">
          No Entity Guard rule entities found for rule_id
          "${this._config.rule_id}".
        </div>
      </ha-card>`;
    }

    const status = this._stateValue(refs.status, "idle");
    const color = STATUS_COLORS[status] || STATUS_COLORS.idle;
    const label = STATUS_LABELS[status] || status;
    const enabled = this.hass.states[refs.enabled]?.state === "on";

    return html`
      <ha-card>
        <div class="header">
          <span class="title">${this._ruleName(refs)}</span>
          <span class="badge" style="background-color: ${color}">${label}</span>
        </div>
        <div class="divider"></div>
        ${this._renderToggle(refs, enabled)}
        ${this._renderStats(refs)}
        ${this._renderInfo(refs)}
        ${this._renderBound(refs)}
        ${this._renderActions(refs)}
      </ha-card>
    `;
  }

  _renderToggle(refs, enabled) {
    if (!refs.enabled) return nothing;
    return html`
      <div class="row">
        <span class="label">Enabled</span>
        <div class="toggle">
          <ha-switch
            .checked=${enabled}
            @change=${(e) => this._toggleEnabled(refs.enabled, e.target.checked)}
          ></ha-switch>
        </div>
      </div>
    `;
  }

  _renderStats(refs) {
    const today = this._stateValue(refs.countToday, "0");
    const total = this._stateValue(refs.countTotal, "0");
    return html`
      <div class="stats">
        <div class="stat">
          <div class="stat-value">${today}</div>
          <div class="stat-label">Today</div>
        </div>
        <div class="stat">
          <div class="stat-value">${total}</div>
          <div class="stat-label">Total</div>
        </div>
      </div>
    `;
  }

  _renderInfo(refs) {
    const last = refs.lastEnforced ? this.hass.states[refs.lastEnforced]?.state : null;
    return html`
      <div class="row">
        <span class="label">Last enforced</span>
        <span class="value">${this._formatTimestamp(last)}</span>
      </div>
    `;
  }

  _renderBound(refs) {
    if (!refs.bound || refs.bound.length === 0) return nothing;
    return html`
      <div class="entities">
        <div class="section-title">Bound entities (${refs.bound.length})</div>
        ${refs.bound.map((id) => {
          const st = this.hass.states[id];
          const name = st?.attributes?.friendly_name || id;
          const state = st ? st.state : "unknown";
          return html`
            <div class="entity-row">
              <span class="entity-name" title="${id}">${name}</span>
              <span class="entity-state">${state}</span>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderActions(refs) {
    return html`
      <div class="actions">
        <button class="action" @click=${() => this._press(refs.reset)} ?disabled=${!refs.reset}>
          Reset
        </button>
        <button class="action primary" @click=${() => this._press(refs.testEnforce)} ?disabled=${!refs.testEnforce}>
          Test Enforce
        </button>
        <button class="action warn" @click=${() => this._suppress(60)}>
          Suppress 1h
        </button>
      </div>
    `;
  }

  async _toggleEnabled(entityId, checked) {
    if (!entityId) return;
    await this.hass.callService("switch", checked ? "turn_on" : "turn_off", {
      entity_id: entityId,
    });
  }

  async _press(entityId) {
    if (!entityId) return;
    await this.hass.callService("button", "press", { entity_id: entityId });
  }

  async _suppress(minutes) {
    const ruleId = this._config.rule_id;
    if (!ruleId) return;
    await this.hass.callService("entity_guard", "suppress", {
      rule_id: ruleId,
      duration_minutes: minutes,
    });
  }
}

customElements.define("entity-guard-card", EntityGuardCard);

// --- Minimal Editor ---

class EntityGuardCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
    };
  }

  static get styles() {
    return css`
      .editor { padding: 16px; }
      .row { margin-bottom: 12px; }
      label { display: block; font-weight: 500; margin-bottom: 4px; }
      input[type="text"] {
        width: 100%;
        padding: 8px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        box-sizing: border-box;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
      }
      .help {
        font-size: 12px;
        color: var(--secondary-text-color, #727272);
        margin-top: 4px;
      }
    `;
  }

  setConfig(config) {
    this._config = { ...config };
  }

  render() {
    if (!this._config) return html``;
    return html`
      <div class="editor">
        <div class="row">
          <label>Rule ID (config entry ID)</label>
          <input
            type="text"
            .value=${this._config.rule_id || ""}
            @input=${(e) => this._update("rule_id", e.target.value)}
            placeholder="e.g. 0a1b2c3d4e5f..."
          />
          <div class="help">
            Find this in Settings → Devices & Services → Entity Guard rule → ⋮ → "Copy entry ID".
          </div>
        </div>
        <div class="row">
          <label>Title (optional)</label>
          <input
            type="text"
            .value=${this._config.title || ""}
            @input=${(e) => this._update("title", e.target.value || undefined)}
            placeholder="Override displayed name"
          />
        </div>
      </div>
    `;
  }

  _update(key, value) {
    const next = { ...this._config, [key]: value };
    Object.keys(next).forEach((k) => {
      if (next[k] === undefined) delete next[k];
    });
    this._config = next;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

customElements.define("entity-guard-card-editor", EntityGuardCardEditor);
