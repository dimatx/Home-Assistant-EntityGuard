/**
 * Entity Guard Card v0.1.0
 * Custom Lovelace card for the Home Assistant Entity Guard integration.
 *
 * Config:
 *   type: custom:entity-guard-card
 *   rule_id: <config_entry_id>   # required
 *   title: <optional override>
 */

const CARD_VERSION = "0.1.0";

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

// Canonical no-build LitElement bootstrap — matches thomasloven/lovelace-card-tools pattern.
// home-assistant-main and hui-view are in HA's initial bundle; always defined before card JS runs.
// Synchronous get() avoids the iOS WKWebView timing issues caused by whenDefined("ha-panel-lovelace")
// (ha-panel-lovelace is lazy-loaded and may resolve late or not at all on the Companion App).
const LitElement = Object.getPrototypeOf(
  customElements.get("home-assistant-main") || customElements.get("hui-view")
);
const html = LitElement.prototype.html;
const nothing = LitElement.prototype.nothing ?? "";
const css = LitElement.prototype.css || (() => {
  class CSSResult {
    constructor(cssText) {
      this.cssText = cssText;
      this._styleSheet = null;
    }
    get styleSheet() {
      if (this._styleSheet === null && window.CSSStyleSheet) {
        try {
          this._styleSheet = new CSSStyleSheet();
          this._styleSheet.replaceSync(this.cssText);
        } catch (e) {
          this._styleSheet = null;
        }
      }
      return this._styleSheet;
    }
    toString() { return this.cssText; }
  }
  return (strings, ...values) => new CSSResult(
    strings.reduce((acc, str, i) => acc + str + (values[i] != null ? String(values[i]) : ""), "")
  );
})();

const STATUS_COLORS = {
  disabled: "#9e9e9e",
  suppressed: "#ff9800",
  enforcing: "#2196f3",
  cooldown: "#ffc107",
  armed: "#4caf50",
  idle: "#bdbdbd",
  starting: "#03a9f4",
  pending: "#ff5722",
};

const STATUS_LABELS = {
  disabled: "Disabled",
  suppressed: "Suppressed",
  enforcing: "Enforcing",
  cooldown: "Cooldown",
  armed: "Armed",
  idle: "Idle",
  starting: "Starting",
  pending: "About to enforce",
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
      _entityRegistry: { state: false },
    };
  }

  constructor() {
    super();
    this._entityRegistry = null;
  }

  async _loadEntityRegistry() {
    if (!this.hass || this._entityRegistry !== null) return;
    this._entityRegistry = {};
    try {
      const entries = await this.hass.callWS({ type: "config/entity_registry/list" });
      const map = {};
      for (const e of entries || []) map[e.entity_id] = e;
      this._entityRegistry = map;
      this.requestUpdate();
    } catch (_) {
      this._entityRegistry = {};
    }
  }

  updated(changed) {
    if (changed.has("hass")) this._loadEntityRegistry();
  }

  static get styles() {
    return cardStyles;
  }

  static getConfigElement() {
    return document.createElement("entity-guard-card-editor");
  }

  static getStubConfig(hass) {
    const states = hass?.states || {};
    const entities = hass?.entities || {};
    const devices = hass?.devices || {};
    const seen = new Map();
    for (const [entityId, st] of Object.entries(states)) {
      if (!entityId.startsWith("sensor.")) continue;
      if (!Array.isArray(st?.attributes?.target_entities)) continue;
      const entry = entities[entityId];
      const entryId = entry?.config_entry_id;
      if (!entryId || seen.has(entryId)) continue;
      const dev = entry?.device_id ? devices[entry.device_id] : null;
      const friendly = (st.attributes.friendly_name || "").replace(
        /\s*Status$/i,
        ""
      );
      seen.set(entryId, dev?.name_by_user || dev?.name || friendly || entryId);
    }
    const sorted = Array.from(seen.entries()).sort((a, b) =>
      a[1].localeCompare(b[1])
    );
    return { rule_id: sorted[0]?.[0] || "", title: "" };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("entity-guard-card: invalid config.");
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
      targetState: null,
    };

    const entities = (this._entityRegistry && Object.keys(this._entityRegistry).length > 0)
      ? this._entityRegistry
      : (this.hass.entities || {});
    const hasRegistry = Object.keys(entities).length > 0;
    const matches = [];

    if (hasRegistry) {
      for (const [entityId, entry] of Object.entries(entities)) {
        if (entry?.platform !== "entity_guard") continue;
        if (ruleId && entry?.config_entry_id !== ruleId) continue;
        if (!ruleId && anchor && !entityId.startsWith(this._anchorPrefix(anchor))) continue;
        matches.push(entityId);
      }
    } else {
      // hass.entities not populated — fall back to state scan
      for (const entityId of Object.keys(this.hass.states || {})) {
        if (!ruleId && anchor && !entityId.startsWith(this._anchorPrefix(anchor))) continue;
        if (ruleId) {
          const st = this.hass.states[entityId];
          // status sensor carries target_entities and friendly_name; all rule entities share the same entry
          // without registry we can only match via state attributes — accept any entity that looks like ours
          const attrEntryId = st?.attributes?.config_entry_id;
          if (attrEntryId && attrEntryId !== ruleId) continue;
          if (!attrEntryId) {
            // heuristic: skip if name clearly belongs to a different rule
          }
        }
        matches.push(entityId);
      }
    }

    for (const id of matches) {
      const st = this.hass.states[id];
      if (!st) continue;
      const entry = entities[id];
      const tk = entry?.translation_key || st.attributes?.translation_key;
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
    out.targetState = statusEntity?.attributes?.target_state ?? null;

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

    if (!this._config.rule_id && !this._config.entity) {
      return html`<ha-card>
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 16px;gap:8px;color:var(--secondary-text-color,#727272);">
          <ha-icon icon="mdi:shield-lock" style="--mdi-icon-size:40px;color:var(--primary-color,#3f51b5)"></ha-icon>
          <span style="font-weight:500;color:var(--primary-text-color)">Entity Guard</span>
          <span style="font-size:13px">Select a rule in the card editor</span>
        </div>
      </ha-card>`;
    }

    if (this._entityRegistry === null) {
      return html`<ha-card><div class="error">Loading…</div></ha-card>`;
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
        ${this._config.show_entities !== false ? this._renderBound(refs) : nothing}
        ${this._config.show_actions ? this._renderActions(refs) : nothing}
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
          <div class="stat-label">Enforcements today</div>
        </div>
        <div class="stat">
          <div class="stat-value">${total}</div>
          <div class="stat-label">Enforcements total</div>
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
    const targetState = refs.targetState;
    return html`
      <div class="entities">
        <div class="section-title">Bound entities (${refs.bound.length})</div>
        ${refs.bound.map((id) => {
          const st = this.hass.states[id];
          const name = st?.attributes?.friendly_name || id;
          const state = st ? st.state : "unknown";
          const compliant = targetState == null || state === targetState;
          return html`
            <div class="entity-row">
              <span class="entity-name" title="${id}">${name}</span>
              <span class="entity-state">
                ${compliant
                  ? html`${state} <span style="color:var(--success-color,#4caf50)">✓</span>`
                  : html`<span style="color:var(--warning-color,#ff9800)">${state} → ${targetState} ⚠</span>`}
              </span>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderActions(refs) {
    return html`
      <div class="entities">
        <div class="section-title">Actions</div>
        <div class="actions">
          ${refs.inCooldown && this.hass.states[refs.inCooldown]?.state === "on" ? html`
          <button class="action" @click=${() => this._press(refs.reset)} ?disabled=${!refs.reset}>
            Reset Cooldowns
          </button>` : nothing}
          <button class="action primary" @click=${() => this._press(refs.testEnforce)} ?disabled=${!refs.testEnforce}>
            Test Enforce
          </button>
          <button class="action warn" @click=${() => this._suppress(60)}>
            Suppress 1h
          </button>
        </div>
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
    const ruleId = this._resolveRuleId();
    if (!ruleId) {
      console.warn("entity-guard-card: cannot suppress without rule_id");
      return;
    }
    await this.hass.callService("entity_guard", "suppress", {
      rule_id: ruleId,
      duration_minutes: minutes,
    });
  }

  _resolveRuleId() {
    if (this._config.rule_id) return this._config.rule_id;
    const anchor = this._config.entity;
    if (!anchor) return null;
    const entry = this.hass?.entities?.[anchor];
    return entry?.config_entry_id || null;
  }
}

customElements.define("entity-guard-card", EntityGuardCard);

// --- Minimal Editor ---

class EntityGuardCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _entries: { state: true },
    };
  }

  constructor() {
    super();
    this._entries = null;
  }

  async _loadEntries() {
    if (!this.hass || this._entries !== null) return;
    this._entries = [];
    try {
      const all = await this.hass.callWS({ type: "config_entries/get", domain: "entity_guard" });
      this._entries = (all || [])
        .filter((e) => e.source !== "import")
        .map((e) => ({ id: e.entry_id, name: e.title || e.entry_id }))
        .sort((a, b) => a.name.localeCompare(b.name));
    } catch (_) {
      this._entries = [];
    }
  }

  updated(changed) {
    if (changed.has("hass")) this._loadEntries();
  }

  static get styles() {
    return css`
      .editor-row {
        margin-bottom: 12px;
      }
      .editor-row label {
        display: block;
        font-weight: 500;
        margin-bottom: 4px;
      }
      .editor-row input[type="text"],
      .editor-row select {
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
    this._config = config;
  }

  render() {
    if (!this._config) return html``;
    const rules = this._entries || [];
    const loading = this._entries === null;
    const current = this._config.rule_id || "";
    const currentMissing = current && !rules.some((r) => r.id === current);
    return html`
      <div style="padding: 16px;">
        <div class="editor-row">
          <label>Rule</label>
          ${loading
            ? html`<input type="text" disabled placeholder="Loading rules…" />`
            : rules.length === 0
              ? html`<input
                  type="text"
                  .value=${current}
                  @input=${(e) => this._update("rule_id", e.target.value)}
                  placeholder="e.g. 0a1b2c3d4e5f..."
                />`
              : html`<select
                  .value=${current}
                  @change=${(e) => this._update("rule_id", e.target.value)}
                >
                  ${!current ? html`<option value="" disabled selected>Select a rule…</option>` : nothing}
                  ${rules.map(
                    (r) => html`<option value=${r.id} ?selected=${r.id === current}>${r.name}</option>`
                  )}
                  ${currentMissing
                    ? html`<option value=${current} selected>Unknown rule (${current})</option>`
                    : nothing}
                </select>`}
          <div class="help">
            Pick the Entity Guard rule this card should display.
          </div>
        </div>
        <div class="editor-row">
          <label>Title (optional)</label>
          <input
            type="text"
            .value=${this._config.title || ""}
            @input=${(e) => this._update("title", e.target.value || undefined)}
            placeholder="Override displayed name"
          />
        </div>
        <div class="editor-row" style="display:flex;align-items:center;justify-content:space-between;">
          <label style="margin-bottom:0">Show bound entities</label>
          <ha-switch
            .checked=${this._config.show_entities !== false}
            @change=${(e) => this._update("show_entities", e.target.checked)}
          ></ha-switch>
        </div>
        <div class="editor-row" style="display:flex;align-items:center;justify-content:space-between;">
          <label style="margin-bottom:0">Show actions</label>
          <ha-switch
            .checked=${!!this._config.show_actions}
            @change=${(e) => this._update("show_actions", e.target.checked)}
          ></ha-switch>
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
