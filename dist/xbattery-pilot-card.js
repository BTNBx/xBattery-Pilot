const BP_VERSION = "0.2.0";

const BP_KEYS = [
  "plano",
  "soc_alvo",
  "rede_prevista",
  "carga_pela_rede",
  "custo_previsto",
  "poupanca_prevista",
  "solar_previsto",
  "consumo_previsto",
  "soc_minimo_previsto",
  "solar_desperdicado",
  "desvio_solar_ontem",
  "desvio_consumo_ontem",
];

const W = 600;
const H = 220;
const PL = 36;
const PR = 36;
const PT = 18;
const PB = 30;

class XBatteryPilotCard extends HTMLElement {
  static getStubConfig() {
    return { prefix: "sensor.xbattery_pilot_" };
  }

  setConfig(config) {
    this._config = { prefix: "sensor.xbattery_pilot_", title: "xBattery Pilot", ...config };
    this._sig = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    const plan = hass.states[this._e("plano")];
    const socId = plan?.attributes?.soc_entity;
    const ids = BP_KEYS.map((k) => this._e(k));
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
    return Number(v).toLocaleString("pt-PT", { minimumFractionDigits: d, maximumFractionDigits: d });
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
    return new Date(iso).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz });
  }

  _periods(rows) {
    const prices = [...new Set(rows.map((r) => r.price))].sort((a, b) => a - b);
    const lo = prices[0];
    const hi = prices[prices.length - 1];
    return rows.map((r) => (r.price === lo ? "vazio" : r.price === hi && prices.length > 2 ? "ponta" : "cheias"));
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

    let svg = "";

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
      svg += `<rect x="${wx}" y="${PT}" width="${ww}" height="${ch}" fill="var(--bp-window)" opacity="0.10" rx="6"/>`;
      svg += `<text x="${wx + ww / 2}" y="${PT - 5}" class="axis" text-anchor="middle" fill="var(--bp-window)">carga</text>`;
      if (target > 0) {
        const ty = yS(target);
        svg += `<line x1="${wx}" x2="${wx + ww}" y1="${ty}" y2="${ty}" stroke="var(--bp-soc)" stroke-width="1.5" stroke-dasharray="5 3"/>`;
        svg += `<text x="${wx + ww / 2}" y="${ty - 4}" class="axis" text-anchor="middle" fill="var(--bp-soc)">alvo ${Math.round(target)}%</text>`;
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
      svg += `<text x="${W - PR + 6}" y="${my + 3}" class="axis" fill="var(--bp-soc)">mín</text>`;
    }

    let pvPath = `M ${x(0)} ${base}`;
    rows.forEach((r, i) => (pvPath += ` L ${x(i)} ${yP(toW(r.pv))}`));
    pvPath += ` L ${x(n - 1)} ${base} Z`;
    svg += `<path d="${pvPath}" fill="var(--bp-pv)" opacity="0.35" stroke="var(--bp-pv)" stroke-width="1.5"/>`;

    rows.forEach((r, i) => {
      if (r.grid > 0) {
        const h = base - yP(toW(r.grid));
        svg += `<rect x="${PL + i * bw + bw * 0.2}" y="${base - h}" width="${bw * 0.6}" height="${h}" rx="1.5" fill="var(--bp-grid)" opacity="0.85"/>`;
      }
    });

    const loadPts = rows.map((r, i) => `${x(i)},${yP(toW(r.load))}`).join(" ");
    svg += `<polyline points="${loadPts}" fill="none" stroke="var(--bp-load)" stroke-width="1.8" stroke-linejoin="round"/>`;

    const socPts = rows.map((r, i) => `${x(i)},${yS(r.soc)}`).join(" ");
    svg += `<polyline points="${socPts}" fill="none" stroke="var(--bp-soc)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>`;

    svg += `<line x1="${PL}" x2="${PL}" y1="${PT}" y2="${base}" stroke="currentColor" stroke-width="1" opacity="0.35"/>`;
    svg += `<text x="${PL + 3}" y="${PT + 9}" class="axis">agora</text>`;

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
      <span><i class="dot" style="background:var(--bp-pv)"></i>Solar</span>
      <span><i class="dot" style="background:var(--bp-load)"></i>Consumo</span>
      <span><i class="dot" style="background:var(--bp-grid)"></i>Rede</span>
      <span><i class="dot" style="background:var(--bp-soc)"></i>SOC</span>
      <span class="sep"></span>
      <span><i class="sq" style="background:var(--bp-vazio)"></i>Vazio</span>
      <span><i class="sq" style="background:var(--bp-cheias)"></i>Cheias</span>
      <span><i class="sq" style="background:var(--bp-ponta)"></i>Ponta</span>`;
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
    info.innerHTML = `
      <b>${this._time(r.t)}</b>
      <span><i class="dot" style="background:var(--bp-pv)"></i>${this._n((r.pv * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-load)"></i>${this._n((r.load * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-grid)"></i>${this._n((r.grid * 2) / 1000, 2)} kW</span>
      <span><i class="dot" style="background:var(--bp-soc)"></i>${this._n(r.soc, 0)}%</span>
      <span><i class="sq" style="background:var(--bp-${g.periods[i]})"></i>${g.periods[i]} · ${this._n(r.price, 4)} €</span>`;
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
    const planId = this._e("plano");
    const plan = this._hass.states[planId];

    const style = `
      <style>
        :host {
          --bp-pv: #FFC93C;
          --bp-load: #5AC8FA;
          --bp-grid: #FF6B6B;
          --bp-soc: #34C759;
          --bp-window: #34C759;
          --bp-vazio: #3B82F6;
          --bp-cheias: #FF9F0A;
          --bp-ponta: #FF453A;
        }
        ha-card { padding: 16px; overflow: hidden; }
        .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
        .title { font-size: 11px; letter-spacing: .04em; font-weight: 700; opacity: .6; }
        .decision { font-size: 24px; font-weight: 700; margin-top: 4px; line-height: 1.15; }
        .reason { font-size: 13px; opacity: .8; margin-top: 4px; line-height: 1.3; }
        .sub { font-size: 12px; opacity: .55; margin-top: 2px; }
        .save { text-align: right; white-space: nowrap; }
        .save .v { font-size: 22px; font-weight: 700; color: var(--bp-soc); }
        .save .l { font-size: 11px; opacity: .6; }
        .tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 14px 0 10px; }
        .tile { background: rgba(127,127,127,.12); border-radius: 14px; padding: 10px 12px; min-width: 0; }
        .tile .v { font-size: 17px; font-weight: 600; white-space: nowrap; }
        .tile .u { font-size: 12px; opacity: .6; font-weight: 500; }
        .tile .l { font-size: 11px; opacity: .6; margin-top: 2px; }
        .tile .x { font-size: 10px; opacity: .5; margin-top: 1px; }
        svg { width: 100%; height: auto; display: block; touch-action: pan-y; color: var(--primary-text-color); }
        .axis { font-size: 10px; fill: var(--secondary-text-color); }
        .info { font-size: 12px; min-height: 20px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; margin-top: 8px; color: var(--secondary-text-color); }
        .info b { color: var(--primary-text-color); }
        .info .sep { width: 1px; height: 12px; background: currentColor; opacity: .25; }
        .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
        .sq { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
        .warn { font-size: 12px; color: var(--bp-cheias); margin-top: 6px; }
        .foot { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; color: var(--secondary-text-color); margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(127,127,127,.18); }
        .good { color: var(--bp-soc); }
        .bad { color: var(--bp-cheias); }
        .err { padding: 8px 0; color: var(--error-color, #FF453A); font-size: 13px; }
      </style>`;

    if (!plan) {
      this.shadowRoot.innerHTML = `${style}<ha-card><div class="title">${this._esc(this._config.title)}</div><div class="err">Entidade não encontrada: ${this._esc(planId)}</div></ha-card>`;
      return;
    }

    const a = plan.attributes || {};
    const rows = Array.isArray(a.slots) ? a.slots : [];
    this._rows = rows;
    const target = Number(this._v("soc_alvo") || 0);
    const charging = target > 0;
    const savings = Number(this._v("poupanca_prevista") || 0);
    const winTxt = a.window_start && a.window_end ? `Janela ${this._time(a.window_start)}–${this._time(a.window_end)}` : "";
    const curtailed = Number(this._v("solar_desperdicado") || 0);
    const socNow = a.soc_entity ? this._st(a.soc_entity) : null;
    const gridCharge = Number(this._v("carga_pela_rede") || 0);

    const tile = (val, label, unit, d, extra = "") => `
      <div class="tile"><div class="v">${this._n(val, d)} <span class="u">${unit}</span></div><div class="l">${label}</div>${extra ? `<div class="x">${extra}</div>` : ""}</div>`;

    const accCls = (v) => (v === null ? "" : Math.abs(Number(v)) <= 10 ? "good" : "bad");
    const accPv = this._v("desvio_solar_ontem");
    const accLoad = this._v("desvio_consumo_ontem");
    const accTxt =
      accPv === null && accLoad === null
        ? "Precisão de ontem: a recolher dados"
        : `Ontem: solar <span class="${accCls(accPv)}">${this._signed(accPv) ?? "–"}</span> · consumo <span class="${accCls(accLoad)}">${this._signed(accLoad) ?? "–"}</span>`;
    const updTxt = a.updated_at ? `Atualizado ${this._time(a.updated_at)}` : "";
    const modeTxt = a.mode === "controlo" ? "a controlar" : "só leitura";

    this.shadowRoot.innerHTML = `${style}
      <ha-card>
        <div class="head">
          <div>
            <div class="title">${this._esc(this._config.title)}</div>
            <div class="decision" style="color:${charging ? "var(--bp-soc)" : "inherit"}">${this._esc(plan.state)}</div>
            ${a.reason ? `<div class="reason">${this._esc(a.reason)}</div>` : ""}
            <div class="sub">${winTxt}</div>
          </div>
          ${
            savings > 0
              ? `<div class="save"><div class="v">${this._n(savings, 2)} €</div><div class="l">poupança prevista</div></div>`
              : ""
          }
        </div>
        <div class="tiles">
          ${tile(this._v("rede_prevista"), "Rede prevista", "kWh", 1, gridCharge > 0 ? `inclui ${this._n(gridCharge)} kWh de carga` : "")}
          ${tile(this._v("custo_previsto"), "Custo previsto", "€", 2)}
          ${tile(socNow, "SOC atual", "%", 0)}
          ${tile(this._v("solar_previsto"), "Solar previsto", "kWh", 1)}
          ${tile(this._v("consumo_previsto"), "Consumo previsto", "kWh", 1)}
          ${tile(this._v("soc_minimo_previsto"), "SOC mínimo", "%", 0)}
        </div>
        ${rows.length ? this._chart(rows, a, target) : `<div class="err">Sem plano disponível</div>`}
        <div class="info"></div>
        ${curtailed > 0.05 ? `<div class="warn">Solar desperdiçado previsto: ${this._n(curtailed)} kWh</div>` : ""}
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
    description: "Plano de carga da bateria (xBattery Pilot)",
    preview: false,
  });
  console.info(
    `%c xBattery Pilot CARD %c v${BP_VERSION} `,
    "color:#fff;background:#34C759;font-weight:700",
    "color:#34C759;background:#1c1c1e"
  );
}
