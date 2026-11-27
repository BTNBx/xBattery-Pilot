const BP_VERSION = "0.3.0";

// Plan entity: English ID (new installs) or Portuguese ID (installs before 0.3.0).
const BP_PLAN_IDS = ["plan", "plano"];

const BP_I18N = {
  en: {
    notFound: "Entity not found",
    noPlan: "No plan available",
    window: "Window",
    savings: "forecast savings",
    gridForecast: "Grid forecast",
    includesCharge: "includes {v} kWh of charge",
    cost: "Cost forecast",
    socAt: "SOC at {t}",
    socStart: "SOC at window start",
    solar: "Solar forecast",
    load: "Load forecast",
    minSoc: "Minimum SOC",
    curtailed: "Forecast curtailed solar",
    accEmpty: "Yesterday's accuracy: collecting data",
    accYesterday: "Yesterday: solar {pv} · load {load}",
    updated: "Updated",
    control: "controlling",
    readOnly: "read-only",
    chargeTo: "charge → {v}%",
    windowShort: "window",
    min: "min",
    now: "now",
    lSolar: "Solar",
    lLoad: "Load",
    lGrid: "Grid",
    vazio: "Off-peak",
    cheias: "Mid-peak",
    ponta: "Peak",
  },
  pt: {
    notFound: "Entidade não encontrada",
    noPlan: "Sem plano disponível",
    window: "Janela",
    savings: "poupança prevista",
    gridForecast: "Rede prevista",
    includesCharge: "inclui {v} kWh de carga",
    cost: "Custo previsto",
    socAt: "SOC às {t}",
    socStart: "SOC início carga",
    solar: "Solar previsto",
    load: "Consumo previsto",
    minSoc: "SOC mínimo",
    curtailed: "Solar desperdiçado previsto",
    accEmpty: "Precisão de ontem: a recolher dados",
    accYesterday: "Ontem: solar {pv} · consumo {load}",
    updated: "Atualizado",
    control: "a controlar",
    readOnly: "só leitura",
    chargeTo: "carga → {v}%",
    windowShort: "janela",
    min: "mín",
    now: "agora",
    lSolar: "Solar",
    lLoad: "Consumo",
    lGrid: "Rede",
    vazio: "Vazio",
    cheias: "Cheias",
    ponta: "Ponta",
  },
};

// Values read from the plan attributes (0.3.0+), with fallback to the old sensors.
const BP_ATTRS = {
  target_soc: "soc_alvo",
  grid_forecast: "rede_prevista",
  grid_charge: "carga_pela_rede",
  cost: "custo_previsto",
  savings: "poupanca_prevista",
  pv_forecast: "solar_previsto",
  load_forecast: "consumo_previsto",
  soc_window_start: "soc_no_inicio_da_carga",
  soc_min: "soc_minimo_previsto",
  curtailed: "solar_desperdicado",
  acc_pv: "desvio_solar_ontem",
  acc_load: "desvio_consumo_ontem",
};

const BP_KEYS = [
  "soc_alvo",
  "rede_prevista",
  "carga_pela_rede",
  "custo_previsto",
  "poupanca_prevista",
  "solar_previsto",
  "consumo_previsto",
  "soc_no_inicio_da_carga",
  "soc_minimo_previsto",
  "solar_desperdicado",
  "desvio_solar_ontem",
  "desvio_consumo_ontem",
];

const W = 600;
const H = 264;
const PL = 36;
const PR = 36;
const PT = 18;
const PB = 30;

class XBatteryPilotCard extends HTMLElement {
  static getStubConfig() {
    return { prefix: "sensor.xbattery_pilot_" };
  }

  _lang() {
    const l = (this._hass?.locale?.language || this._hass?.language || "en").toLowerCase();
    return l.startsWith("pt") ? "pt" : "en";
  }

  _t(k, vars = {}) {
    const s = (BP_I18N[this._lang()] || BP_I18N.en)[k] ?? BP_I18N.en[k] ?? k;
    return s.replace(/\{(\w+)\}/g, (_, v) => vars[v] ?? "");
  }

  _locale() {
    return this._hass?.locale?.language || this._hass?.language || "en";
  }

  _planId() {
    if (this._config.entity) return this._config.entity;
    for (const k of BP_PLAN_IDS) {
      const id = this._e(k);
      if (this._hass?.states[id]) return id;
    }
    return this._e(BP_PLAN_IDS[0]);
  }

  _a(k) {
    const plan = this._hass.states[this._planId()];
    const v = plan?.attributes?.[k];
    if (v !== undefined) return v;
    return BP_ATTRS[k] ? this._v(BP_ATTRS[k]) : null;
  }

  setConfig(config) {
    this._config = { prefix: "sensor.xbattery_pilot_", title: "xBattery Pilot", ...config };
    this._sig = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    const plan = hass.states[this._planId()];
    const socId = plan?.attributes?.soc_entity;
    const ids = [this._planId(), ...BP_KEYS.map((k) => this._e(k))];
    if (socId) ids.push(socId);
    const sig = ids
      .map((id) => {
        const st = hass.states[id];
        return st ? `${st.state}@${st.last_updated}` : "-";
      })
      .join("|");
    if (sig === this._sig) return;
    this._sig = sig;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, rows: 8, min_columns: 6 };
  }

  _e(k) {
    return `${this._config.prefix}${k}`;
  }

  _st(id) {
    const st = this._hass.states[id];
    if (!st || ["unknown", "unavailable"].includes(st.state)) return null;
    return st.state;
  }

  _v(k) {
    return this._st(this._e(k));
  }

  _n(v, d = 1) {
    if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "–";
    return Number(v).toLocaleString(this._locale(), { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  _signed(v) {
    if (v === null || v === undefined || isNaN(Number(v))) return null;
    const n = Math.round(Number(v));
    return `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n)} %`;
  }

  _esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  _time(iso) {
    const tz = this._hass?.config?.time_zone;
    return new Date(iso).toLocaleTimeString(this._locale(), { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz });
  }

  _periods(rows) {
    const prices = [...new Set(rows.map((r) => r.price))].sort((a, b) => a - b);
    const lo = prices[0];
    const hi = prices[prices.length - 1];
    return rows.map((r) => (r.price === lo ? "vazio" : r.price === hi && prices.length > 2 ? "ponta" : "cheias"));
  }

  _smooth(pts) {
    const n = pts.length;
    if (n < 3) return pts.map((p, i) => `${i ? "L" : "M"} ${p[0]} ${p[1]}`).join(" ");
    const dx = [];
    const m = [];
    for (let i = 0; i < n - 1; i++) {
      dx.push(pts[i + 1][0] - pts[i][0]);
      m.push((pts[i + 1][1] - pts[i][1]) / dx[i]);
    }
    const t = [m[0]];
    for (let i = 1; i < n - 1; i++) t.push(m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2);
    t.push(m[n - 2]);
    for (let i = 0; i < n - 1; i++) {
      if (m[i] === 0) {
        t[i] = 0;
        t[i + 1] = 0;
        continue;
      }
      const a = t[i] / m[i];
      const b = t[i + 1] / m[i];
      const h = a * a + b * b;
      if (h > 9) {
        const k = 3 / Math.sqrt(h);
        t[i] = k * a * m[i];
        t[i + 1] = k * b * m[i];
      }
    }
    let d = `M ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 0; i < n - 1; i++) {
      const h = dx[i] / 3;
      d += ` C ${pts[i][0] + h} ${pts[i][1] + t[i] * h} ${pts[i + 1][0] - h} ${pts[i + 1][1] - t[i + 1] * h} ${pts[i + 1][0]} ${pts[i + 1][1]}`;
    }
    return d;
  }

  _chart(rows, a, target) {
    const n = rows.length;
    const cw = W - PL - PR;
    const ch = H - PT - PB;
    const bw = cw / n;
    const base = PT + ch;
    const toW = (wh) => wh * 2;

    let maxP = 500;
    rows.forEach((r) => (maxP = Math.max(maxP, toW(r.pv), toW(r.load), toW(r.grid))));
    maxP = Math.ceil(maxP / 500) * 500;

    const x = (i) => PL + i * bw + bw / 2;
    const yP = (w) => PT + (1 - w / maxP) * ch;
    const yS = (s) => PT + (1 - s / 100) * ch;

    const periods = this._periods(rows);
    const tStart = new Date(a.window_start).getTime();
    const tEnd = new Date(a.window_end).getTime();

    let svg = `<defs><linearGradient id="bp-pv-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--bp-pv)" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="var(--bp-pv)" stop-opacity="0.04"/>
    </linearGradient></defs>`;

    let wi0 = -1;
    let wi1 = -1;
    rows.forEach((r, i) => {
      const t = new Date(r.t).getTime();
      if (t >= tStart && t < tEnd) {
        if (wi0 < 0) wi0 = i;
        wi1 = i;
      }
    });
    if (wi0 >= 0) {
      const wx = PL + wi0 * bw;
      const ww = (wi1 - wi0 + 1) * bw;
      const on = target > 0;
      svg += `<rect x="${wx}" y="${PT}" width="${ww}" height="${ch}" fill="${on ? "var(--bp-soc)" : "currentColor"}" opacity="${on ? 0.14 : 0.05}" rx="6"/>`;
      svg += `<text x="${wx + ww / 2}" y="${PT - 5}" class="axis" text-anchor="middle"${on ? ' fill="var(--bp-soc)"' : ""}>${on ? this._t("chargeTo", { v: Math.round(target) }) : this._t("windowShort")}</text>`;
      if (target > 0) {
        const ty = yS(target);
        svg += `<line x1="${wx}" x2="${wx + ww}" y1="${ty}" y2="${ty}" stroke="var(--bp-soc)" stroke-width="1.5" stroke-dasharray="5 3"/>`;
      }
    }

    [0, 0.5, 1].forEach((f) => {
      const y = PT + (1 - f) * ch;
      svg += `<line x1="${PL}" x2="${W - PR}" y1="${y}" y2="${y}" stroke="currentColor" opacity="0.08"/>`;
      svg += `<text x="${PL - 6}" y="${y + 3}" class="axis" text-anchor="end">${this._n((maxP * f) / 1000, 1)}</text>`;
      svg += `<text x="${W - PR + 6}" y="${y + 3}" class="axis">${Math.round(100 * f)}%</text>`;
    });
    svg += `<text x="${PL - 6}" y="${PT - 5}" class="axis" text-anchor="end">kW</text>`;
    svg += `<text x="${W - PR + 6}" y="${PT - 5}" class="axis">SOC</text>`;

    const minSoc = Number(a.min_soc);
    if (!isNaN(minSoc) && minSoc > 0) {
      const my = yS(minSoc);
      svg += `<line x1="${PL}" x2="${W - PR}" y1="${my}" y2="${my}" stroke="var(--bp-soc)" stroke-width="1" stroke-dasharray="3 4" opacity="0.55"/>`;
      svg += `<text x="${W - PR + 6}" y="${my + 3}" class="axis" fill="var(--bp-soc)">${this._t("min")}</text>`;
    }

    const ma = (k) =>
      rows.map((_, i) => {
        const v = [rows[i - 1], rows[i], rows[i + 1]].filter(Boolean).map((r) => r[k]);
        return v.reduce((s, z) => s + z, 0) / v.length;
      });
    const pvS = ma("pv");
    const loadS = ma("load");
    const pvLine = this._smooth(rows.map((r, i) => [x(i), yP(toW(r.pv > 0 ? pvS[i] : 0))]));
    svg += `<path d="${pvLine} L ${x(n - 1)} ${base} L ${x(0)} ${base} Z" fill="url(#bp-pv-grad)" stroke="none"/>`;
    svg += `<path d="${pvLine}" fill="none" stroke="var(--bp-pv)" stroke-width="1.6" stroke-linejoin="round"/>`;

    rows.forEach((r, i) => {
      if (r.grid > 0) {
        const h = base - yP(toW(r.grid));
        svg += `<rect x="${PL + i * bw + bw * 0.2}" y="${base - h}" width="${bw * 0.6}" height="${h}" rx="1.5" fill="var(--bp-grid)" opacity="0.85"/>`;
      }
    });

    const loadPath = this._smooth(rows.map((r, i) => [x(i), yP(toW(loadS[i]))]));
    svg += `<path d="${loadPath}" fill="none" stroke="var(--bp-load)" stroke-width="1.8" stroke-linejoin="round"/>`;

    const socPath = this._smooth(rows.map((r, i) => [x(i), yS(r.soc)]));
    svg += `<path d="${socPath}" fill="none" stroke="var(--bp-soc)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>`;

    svg += `<line x1="${PL}" x2="${PL}" y1="${PT}" y2="${base}" stroke="currentColor" stroke-width="1" opacity="0.35"/>`;
    svg += `<text x="${PL + 3}" y="${PT + 9}" class="axis">${this._t("now")}</text>`;

    rows.forEach((r, i) => {
      svg += `<rect x="${PL + i * bw}" y="${base + 4}" width="${bw + 0.5}" height="5" fill="var(--bp-${periods[i]})"/>`;
      const hm = this._time(r.t);
      const [hh, mm] = hm.split(":").map(Number);
      if (mm === 0 && hh % 3 === 0) {
        svg += `<text x="${PL + i * bw}" y="${H - 6}" class="axis" text-anchor="middle">${String(hh).padStart(2, "0")}h</text>`;
      }
    });

    svg += `<line id="cursor" x1="0" x2="0" y1="${PT}" y2="${base}" stroke="currentColor" opacity="0" stroke-width="1"/>`;
    svg += `<circle id="cursor-dot" r="4" cx="0" cy="0" fill="var(--bp-soc)" opacity="0"/>`;
    svg += `<rect id="hit" x="${PL}" y="0" width="${cw}" height="${H}" fill="transparent"/>`;

    this._geo = { n, bw, x, yS, periods };
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${svg}</svg>`;
  }

  _legend() {
    return `
      <div class="row">
        <span><i class="dot" style="background:var(--bp-pv)"></i>${this._t("lSolar")}</span>
        <span><i class="dot" style="background:var(--bp-load)"></i>${this._t("lLoad")}</span>
        <span><i class="dot" style="background:var(--bp-grid)"></i>${this._t("lGrid")}</span>
        <span><i class="dot" style="background:var(--bp-soc)"></i>SOC</span>
      </div>
      <div class="row">
        <span><i class="sq" style="background:var(--bp-vazio)"></i>${this._t("vazio")}</span>
        <span><i class="sq" style="background:var(--bp-cheias)"></i>${this._t("cheias")}</span>
        <span><i class="sq" style="background:var(--bp-ponta)"></i>${this._t("ponta")}</span>
      </div>`;
  }

  _select(i) {
    const root = this.shadowRoot;
    const info = root.querySelector(".info");
    const cursor = root.getElementById("cursor");
    const dot = root.getElementById("cursor-dot");
    if (!info || !cursor) return;
    if (i === null || !this._rows || i < 0 || i >= this._rows.length) {
      cursor.setAttribute("opacity", "0");
      dot.setAttribute("opacity", "0");
      info.innerHTML = this._legend();
      return;
    }
    const r = this._rows[i];
    const g = this._geo;
    const cx = g.x(i);
    cursor.setAttribute("x1", cx);
    cursor.setAttribute("x2", cx);
    cursor.setAttribute("opacity", "0.35");
    dot.setAttribute("cx", cx);
    dot.setAttribute("cy", g.yS(r.soc));
    dot.setAttribute("opacity", "1");
    info.innerHTML = `<div class="row">
      <b>${this._time(r.t)}</b>
      <span><i class="dot" style="background:var(--bp-pv)"></i>${this._n((r.pv * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-load)"></i>${this._n((r.load * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-grid)"></i>${this._n((r.grid * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-soc)"></i>${this._n(r.soc, 0)}%</span>
      </div><div class="row">
      <span><i class="sq" style="background:var(--bp-${g.periods[i]})"></i>${this._t(g.periods[i])} · ${this._n(r.price, 4)} €/kWh</span></div>`;
  }

  _bind() {
    const svg = this.shadowRoot.querySelector("svg");
    if (!svg || !this._geo) return;
    const pick = (ev) => {
      const rect = svg.getBoundingClientRect();
      const px = ((ev.clientX - rect.left) * W) / rect.width;
      const i = Math.floor((px - PL) / this._geo.bw);
      this._select(Math.max(0, Math.min(this._geo.n - 1, i)));
    };
    svg.addEventListener("pointermove", pick);
    svg.addEventListener("pointerdown", pick);
    svg.addEventListener("pointerleave", () => this._select(null));
  }

  _render() {
    if (!this._hass || !this._config) return;
    const planId = this._planId();
    const plan = this._hass.states[planId];

    const style = `
      <style>
        :host {
          --bp-pv: #22C55E;
          --bp-load: #5AC8FA;
          --bp-grid: #EF4444;
          --bp-soc: #A78BFA;
          --bp-vazio: #3B82F6;
          --bp-cheias: #F59E0B;
          --bp-ponta: #E11D48;
        }
        ha-card { padding: 16px; overflow: hidden; }
        .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
        .title { font-size: 11px; letter-spacing: .04em; font-weight: 700; opacity: .6; }
        .decision { font-size: 24px; font-weight: 700; margin-top: 4px; line-height: 1.15; }
        .reason { font-size: 13px; opacity: .8; margin-top: 4px; line-height: 1.3; }
        .sub { font-size: 12px; opacity: .55; margin-top: 2px; }
        .side { text-align: right; white-space: nowrap; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
        .bat { display: flex; align-items: center; gap: 4px; color: var(--bp-soc); }
        .bat ha-icon { --mdc-icon-size: 30px; }
        .bat .v { font-size: 26px; font-weight: 700; line-height: 1; }
        .bat .u { font-size: 13px; opacity: .7; font-weight: 600; }
        .save .v { font-size: 16px; font-weight: 700; color: var(--bp-pv); }
        .save .l { font-size: 11px; opacity: .6; }
        .tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 14px 0 10px; }
        .tile { background: rgba(127,127,127,.12); border-radius: 14px; padding: 10px 12px; min-width: 0; }
        .tile .v { font-size: 17px; font-weight: 600; white-space: nowrap; display: flex; align-items: center; gap: 6px; }
        .tile .v ha-icon { --mdc-icon-size: 16px; opacity: .55; flex-shrink: 0; }
        .tile .u { font-size: 12px; opacity: .6; font-weight: 500; }
        .tile .l { font-size: 11px; opacity: .6; margin-top: 2px; }
        .tile .x { font-size: 10px; opacity: .5; margin-top: 1px; }
        svg { width: 100%; height: auto; display: block; touch-action: pan-y; color: var(--primary-text-color); }
        .axis { font-size: 10px; fill: var(--secondary-text-color); }
        .info { font-size: 12px; min-height: 40px; display: flex; flex-direction: column; gap: 4px; margin-top: 8px; color: var(--secondary-text-color); }
        .info .row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px; }
        .info b { color: var(--primary-text-color); }
        .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
        .sq { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
        .warn { font-size: 12px; color: var(--bp-cheias); margin-top: 6px; }
        .foot { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; color: var(--secondary-text-color); margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(127,127,127,.18); }
        .good { color: var(--bp-pv); }
        .bad { color: var(--bp-cheias); }
        .err { padding: 8px 0; color: var(--error-color, #FF453A); font-size: 13px; }
      </style>`;

    if (!plan) {
      this.shadowRoot.innerHTML = `${style}<ha-card><div class="title">${this._esc(this._config.title)}</div><div class="err">${this._t("notFound")}: ${this._esc(planId)}</div></ha-card>`;
      return;
    }

    const a = plan.attributes || {};
    const rows = Array.isArray(a.slots) ? a.slots : [];
    this._rows = rows;
    const target = Number(this._a("target_soc") || 0);
    const charging = target > 0;
    const savings = Number(this._a("savings") || 0);
    const winTxt = a.window_start && a.window_end ? `${this._t("window")} ${this._time(a.window_start)}–${this._time(a.window_end)}` : "";
    const curtailed = Number(this._a("curtailed") || 0);
    const socNow = a.soc_entity ? this._st(a.soc_entity) : null;
    const gridCharge = Number(this._a("grid_charge") || 0);

    const tile = (icon, val, label, unit, d, extra = "") => `
      <div class="tile"><div class="v"><ha-icon icon="${icon}"></ha-icon><span>${this._n(val, d)} <span class="u">${unit}</span></span></div><div class="l">${label}</div>${extra ? `<div class="x">${extra}</div>` : ""}</div>`;
    const socN = socNow === null ? null : Number(socNow);
    const batIcon =
      socN === null || isNaN(socN)
        ? "mdi:battery-unknown"
        : socN >= 95
          ? "mdi:battery"
          : socN < 5
            ? "mdi:battery-outline"
            : `mdi:battery-${Math.min(90, Math.max(10, Math.round(socN / 10) * 10))}`;
    const winStart = a.window_start ? this._time(a.window_start) : "";

    const accCls = (v) => (v === null ? "" : Math.abs(Number(v)) <= 10 ? "good" : "bad");
    const accPv = this._a("acc_pv");
    const accLoad = this._a("acc_load");
    const accTxt =
      (accPv === null || accPv === undefined) && (accLoad === null || accLoad === undefined)
        ? this._t("accEmpty")
        : this._t("accYesterday", {
            pv: `<span class="${accCls(accPv ?? null)}">${this._signed(accPv) ?? "–"}</span>`,
            load: `<span class="${accCls(accLoad ?? null)}">${this._signed(accLoad) ?? "–"}</span>`,
          });
    const updTxt = a.updated_at ? `${this._t("updated")} ${this._time(a.updated_at)}` : "";
    const modeTxt = ["control", "controlo"].includes(a.mode) ? this._t("control") : this._t("readOnly");

    this.shadowRoot.innerHTML = `${style}
      <ha-card>
        <div class="head">
          <div>
            <div class="title">${this._esc(this._config.title)}</div>
            <div class="decision" style="color:${charging ? "var(--bp-soc)" : "inherit"}">${this._esc(plan.state)}</div>
            ${a.reason ? `<div class="reason">${this._esc(a.reason)}</div>` : ""}
            <div class="sub">${winTxt}</div>
          </div>
          <div class="side">
            <div class="bat"><ha-icon icon="${batIcon}"></ha-icon><span class="v">${this._n(socNow, 0)}</span><span class="u">%</span></div>
            ${savings > 0 ? `<div class="save"><div class="v">${this._n(savings, 2)} €</div><div class="l">${this._t("savings")}</div></div>` : ""}
          </div>
        </div>
        <div class="tiles">
          ${tile("mdi:transmission-tower", this._a("grid_forecast"), this._t("gridForecast"), "kWh", 1, gridCharge > 0 ? this._t("includesCharge", { v: this._n(gridCharge) }) : "")}
          ${tile("mdi:currency-eur", this._a("cost"), this._t("cost"), "€", 2)}
          ${tile("mdi:battery-clock-outline", this._a("soc_window_start"), winStart ? this._t("socAt", { t: winStart }) : this._t("socStart"), "%", 0)}
          ${tile("mdi:solar-power-variant", this._a("pv_forecast"), this._t("solar"), "kWh", 1)}
          ${tile("mdi:home-lightning-bolt-outline", this._a("load_forecast"), this._t("load"), "kWh", 1)}
          ${tile("mdi:battery-low", this._a("soc_min"), this._t("minSoc"), "%", 0)}
        </div>
        ${rows.length ? this._chart(rows, a, target) : `<div class="err">${this._t("noPlan")}</div>`}
        <div class="info"></div>
        ${curtailed > 0.05 ? `<div class="warn">${this._t("curtailed")}: ${this._n(curtailed)} kWh</div>` : ""}
        <div class="foot"><span>${accTxt}</span><span>${updTxt} · ${modeTxt}</span></div>
      </ha-card>`;

    this._select(null);
    this._bind();
  }
}

if (!customElements.get("xbattery-pilot-card")) {
  customElements.define("xbattery-pilot-card", XBatteryPilotCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "xbattery-pilot-card",
    name: "xBattery Pilot",
    description: "Overnight battery charge plan (xBattery Pilot)",
    preview: false,
  });
  console.info(
    `%c xBattery Pilot CARD %c v${BP_VERSION} `,
    "color:#fff;background:#34C759;font-weight:700",
    "color:#34C759;background:#1c1c1e"
  );
}
