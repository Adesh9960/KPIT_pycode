// Live Dashboard tab: gauges, live strip chart, and the ambient weather widget.

import { state } from "./state.js";
import { updatePreConditions } from "./advanced.js";
import { setText } from "./ui.js";

const LIVE_BUF = 80;
let time_count = 0;
let bufTime = [],
    bufSpeed = [],
    bufRpm = [];
// Update the Live tab's gauges, readouts, and status strip from a polled data payload.
export function updateLive(d) {
    state.lastSpeed = d.speed || 0;
    if (d.date) setText("live-date-display", d.date);

    const badge = document.getElementById("engine-state-badge");
    if (badge) {
        badge.textContent = d.engine_state || "IDLE";
        badge.className =
            "state-badge" +
            (["BRAKING", "STALLED", "DEAD", "OVERHEATING"].includes(
                d.engine_state,
            )
                ? " warn"
                : "");
    }

    updateGauge(
        "speed-gauge",
        d.speed || 0,
        0,
        220,
        "km/h",
        "#00d4aa",
        "#0a1a14",
    );
    updateGauge("rpm-gauge", d.rpm || 0, 0, 7000, "RPM", "#4ade80", "#0a1a14");
    updateGauge(
        "fuel-gauge",
        d.fuel || d.fuel_pct || 0,
        0,
        100,
        "%",
        "#34d399",
        "#0a1a14",
    );

    setText("distance-main-val", (d.distance_km || 0).toFixed(2));
    setText();
    // Derived
    const fr = d.fuel_rate || 0;
    const sp = d.speed || 0;
    const fuelL = d.remaining_fuel_l || d.fuel_l || 0;
    const econKmL = fr > 0.01 && sp > 0 ? (sp / (fr * 3.6)).toFixed(1) : "--";
    const estRange =
        fr > 0.01 && sp > 0
            ? Math.round(((fuelL * 1000) / fr / 3600) * sp) + " km"
            : "-- km";
    setText("fuel-economy", econKmL === "--" ? "-- km/L" : econKmL + " km/L");
    setText("est-range", estRange);

    // Transmission
    const gn = d.gear_num || 0;
    setText("gear-display", gn === 0 ? "N" : String(gn));
    setText("gear-name", gn === 0 ? "Neutral" : "gear " + gn);
    const rpm = d.rpm || 0;
    const shiftHint = document.getElementById("shift-hint");
    if (shiftHint) {
        if (rpm > 5500) {
            shiftHint.textContent = "⬆ SHIFT UP";
            shiftHint.style.color = "#f87171";
        } else if (rpm < 1200 && gn > 1) {
            shiftHint.textContent = "⬇ SHIFT DOWN";
            shiftHint.style.color = "#fbbf24";
        } else {
            shiftHint.textContent = "—";
            shiftHint.style.color = "";
        }
    }

    const clutchEl = document.getElementById("chip-clutch");
    const clutchVal = document.getElementById("clutch-val");

    const clutchState = d.clutch_state == 1 ? "DOWN" : "UP";
    if (clutchVal) clutchVal.textContent = clutchState;
    if (clutchEl) clutchEl.classList.toggle("active", clutchState === "DOWN");

    const brakeEl = document.getElementById("chip-brake");
    const brakeVal = document.getElementById("brake-val");
    const brakeState = d.brake_state == 1 ? "DOWN" : "UP";

    if (brakeVal) brakeVal.textContent = brakeState;
    if (brakeEl) brakeEl.classList.toggle("active", brakeState === "PRESSED");

    // Thermals
    const cT = d.coolant || d.coolant_temp || 0;
    const coolEl = document.getElementById("coolantTemp");
    if (coolEl) {
        coolEl.textContent = cT.toFixed(1);
        coolEl.className =
            "lv-th-val" + (cT > 103 ? " hot" : cT < 60 ? " cool" : "");
    }
    setText("oil-val", (d.oil_temp || 0).toFixed(1));
    setText("ambient-val", (d.ambient_temp || 0).toFixed(1));
    setText("eng-state-text", d.engine_state || "IDLE");

    const warmupPct = Math.min(100, Math.max(0, ((cT - 30) / 60) * 100));
    setText("warmup-pct", warmupPct.toFixed(0));
    const warmBar = document.getElementById("bar-warmup");
    if (warmBar) warmBar.style.width = warmupPct + "%";
    const coolBar = document.getElementById("bar-coolant");
    if (coolBar) {
        coolBar.style.width =
            Math.min(100, ((cT - 40) / 80) * 100).toFixed(0) + "%";
        coolBar.style.background = cT > 103 ? "#f87171" : "#00d4aa";
    }

    // Headlights
    if (d.head_lamp) {
        document
            .getElementById("chip-highbeam")
            .classList.toggle("active", true);
        document
            .getElementById("chip-lowbeam")
            .classList.toggle("active", false);
    } else {
        document
            .getElementById("chip-lowbeam")
            .classList.toggle("active", true);
        document
            .getElementById("chip-highbeam")
            .classList.toggle("active", false);
    }

    // Indicators — assumes d.indicator_state is "LEFT" | "RIGHT" | "HAZARD" | "OFF"
    const leftEl = document.getElementById("ind-left");
    const rightEl = document.getElementById("ind-right");
    leftEl.classList.toggle("active", d.steering_direction === 1);
    rightEl.classList.toggle("active", d.steering_direction === 2);

    // Fuel panel
    const fp = Math.max(0, Math.min(100, d.fuel || d.fuel_pct || 0));
    const fb = document.getElementById("fuel-bar");
    if (fb) fb.style.width = fp + "%";
    setText("fuelLevel", fp.toFixed(1) + "%");
    setText("fuel-l-val", (d.remaining_fuel_l || d.fuel_l || 0).toFixed(2));
    setText("fuel-rate-val", (d.fuel_rate || 0).toFixed(2));

    // NEW: Actuator states from Parameters.py
    setText(
        "fuel-pump-val",
        d.fuel_pump != null ? (d.fuel_pump ? "ON" : "OFF") : "--",
    );
    setText(
        "headlamp-val",
        d.head_lamp != null ? (d.head_lamp ? "ON" : "OFF") : "--",
    );
    setText(
        "radfan-val",
        d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "--",
    );

    // Electrical
    const bv = d.voltage || d.battery_v || 0;
    const batEl = document.getElementById("batteryVoltage");
    if (batEl) {
        batEl.textContent = bv.toFixed(2);
        batEl.className = "lv-th-val" + (bv < 12.2 ? " hot" : "");
    }
    const battBar = document.getElementById("bar-batt");
    if (battBar) {
        battBar.style.width =
            Math.min(100, ((bv - 11) / 4) * 100).toFixed(0) + "%";
        battBar.style.background =
            bv < 12 ? "#f87171" : bv < 12.5 ? "#fbbf24" : "#34d399";
    }

    const rlEl = document.getElementById("revlim-val");
    if (rlEl) {
        rlEl.textContent = d.rev_limiter ? "ACTIVE" : "OK";
        rlEl.className = "lv-th-val" + (d.rev_limiter ? " hot" : " cool");
    }
    const stallEl = document.getElementById("stall-live");
    if (stallEl) {
        stallEl.textContent = d.stall_risk ? "WARNING" : "OK";
        stallEl.className = "lv-th-val" + (d.stall_risk ? " hot" : " cool");
    }

    // Update pre-condition bar in technician mode
    updatePreConditions(d.speed || 0);

    bufTime.push(time_count);
    time_count += 1;
    bufSpeed.push(d.speed || 0);
    bufRpm.push(d.rpm || 0);
    if (bufTime.length > LIVE_BUF) {
        bufTime.shift();
        bufSpeed.shift();
        bufRpm.shift();
    }
    updateLiveChart();
}

// ── Pre-condition checks for programming session ──
// ══════════════════════════════════════════════════
// PLOTLY GAUGE
// ══════════════════════════════════════════════════
// Update a single circular gauge's needle rotation and readout text.
export function updateGauge(id, value, min, max, suffix, barColor, bgInner) {
    const lo = min + (max - min) * 0.55;
    const mid = min + (max - min) * 0.82;
    const isDark =
        document.documentElement.getAttribute("data-theme") !== "light";
    const numColor = isDark ? "#e8f5ee" : "#0f1f14";
    const bgColor = "transparent";
    const step1 = isDark ? "#0d1a12" : "#ddf0e6";
    const step2 = isDark ? "#142010" : "#c5e4d0";
    const step3 = isDark ? "#1f1208" : "#f5ddc0";
    Plotly.react(
        id,
        [
            {
                type: "indicator",
                mode: "gauge+number",
                value: value,
                number: {
                    suffix: " " + suffix,
                    font: {
                        color: numColor,
                        size: 22,
                        family: "Inter,Segoe UI",
                    },
                },
                gauge: {
                    axis: {
                        range: [min, max],
                        tickcolor: isDark ? "#1e3a28" : "#aac8b8",
                        tickfont: {
                            size: 9,
                            color: isDark ? "#4a7a5a" : "#5a8a6a",
                        },
                        nticks: 8,
                    },
                    bar: { color: barColor, thickness: 0.3 },
                    bgcolor: bgColor,
                    borderwidth: 0,
                    steps: [
                        { range: [min, lo], color: step1 },
                        { range: [lo, mid], color: step2 },
                        { range: [mid, max], color: step3 },
                    ],
                    threshold: {
                        line: {
                            color: isDark
                                ? "rgba(255,255,255,0.3)"
                                : "rgba(0,0,0,0.2)",
                            width: 2,
                        },
                        thickness: 0.8,
                        value: mid,
                    },
                },
            },
        ],
        {
            margin: { t: 28, b: 8, l: 24, r: 24 },
            paper_bgcolor: bgColor,
            font: { color: numColor },
        },
        { responsive: true, displayModeBar: false },
    );
}

// ══════════════════════════════════════════════════
// LIVE TREND CHART
// ══════════════════════════════════════════════════
// Redraw the live speed/RPM strip chart from the rolling sample buffers.
export function updateLiveChart() {
    const rpmScaled = bufRpm.map((r) => r / 36);
    const isDark =
        document.documentElement.getAttribute("data-theme") !== "light";
    const gridColor = isDark ? "#1a2e20" : "#d0e8da";
    const fontColor = isDark ? "#4a7a5a" : "#4a7a5a";

    Plotly.react(
        "live-chart",
        [
            {
                x: bufTime,
                y: bufSpeed,
                name: "Speed (km/h)",
                mode: "lines",
                type: "scatter",
                line: {
                    color: "#00d4aa",
                    width: 2.5,
                    shape: "spline",
                    smoothing: 1.3,
                },
                fill: "tozeroy",
                fillcolor: "rgba(0,212,170,0.10)",
            },
            {
                x: bufTime,
                y: rpmScaled,
                name: "RPM ÷ 36",
                mode: "lines",
                type: "scatter",
                line: {
                    color: "#4ade80",
                    width: 1.5,
                    dash: "dot",
                    shape: "spline",
                    smoothing: 1.3,
                },
            },
        ],
        {
            margin: { t: 10, b: 36, l: 46, r: 16 },
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: { color: fontColor, size: 11 },
            legend: { orientation: "h", x: 0, y: -0.28, font: { size: 11 } },
            xaxis: {
                title: "Time",
                gridcolor: gridColor,
                zeroline: false,
                tickfont: { size: 9 },
            },
            yaxis: {
                title: "Speed / RPM÷36",
                gridcolor: gridColor,
                zeroline: false,
            },
        },
        { responsive: true, displayModeBar: false },
    );
}

// ══════════════════════════════════════════════════
// PROGRAMMING SESSION — UI Logic now lives in the
// pgterm engine block near the end of this file.
// ══════════════════════════════════════════════════

// ══════════════════════════════════════════════════
// HISTORY MODE
// ══════════════════════════════════════════════════
export const SIGNAL_MAP = {
    speed: { label: "Speed (km/h)", key: "speed", color: "#00d4aa" },
    rpm: { label: "Engine RPM", key: "rpm", color: "#4ade80" },
    coolant: { label: "Coolant Temp (°C)", key: "coolant", color: "#f87171" },
    oil_temp: { label: "Oil Temp (°C)", key: "oil_temp", color: "#fb923c" },
    fuel_pct: { label: "Fuel Level (%)", key: "fuel_pct", color: "#34d399" },
    fuel_rate: {
        label: "Fuel Rate (mL/s)",
        key: "fuel_rate",
        color: "#60a5fa",
    },
    throttle: { label: "Throttle (%)", key: "throttle", color: "#fbbf24" },
    engine_load: {
        label: "Engine Load (%)",
        key: "engine_load",
        color: "#a78bfa",
    },
    accel: { label: "Acceleration (m/s²)", key: "accel", color: "#2dd4bf" },
    battery: { label: "Battery Voltage (V)", key: "battery", color: "#facc15" },
    gear_num: { label: "Gear Number", key: "gear_num", color: "#00d4aa" },
};
export const FILL_MAP = {
    "#00d4aa": "rgba(0,212,170,0.08)",
    "#4ade80": "rgba(74,222,128,0.08)",
    "#f87171": "rgba(248,113,113,0.08)",
    "#fb923c": "rgba(251,146,60,0.08)",
    "#34d399": "rgba(52,211,153,0.08)",
    "#60a5fa": "rgba(96,165,250,0.08)",
    "#fbbf24": "rgba(251,191,36,0.08)",
    "#a78bfa": "rgba(167,139,250,0.08)",
    "#2dd4bf": "rgba(45,212,191,0.08)",
    "#facc15": "rgba(250,204,21,0.08)",
};

// Update the ambient-temperature weather widget from the polled data payload.
export function updateWeatherDisplay(d) {
    const tempEl = document.getElementById("weather-temp");
    if (!tempEl) return;
    if (d.ambient_temp === null || d.ambient_temp === undefined) return;
    tempEl.textContent = Math.round(d.ambient_temp) + "°C";
}

// ══════════════════════════════════════════════════════════════
// PROGRAMMING SESSION TERMINAL  ("pgterm")
//
// A real command-line REPL bolted onto a Linux-terminal-styled
// screen. Every command below maps 1:1 onto a /prog/* Flask route
// and onto a step from the Programming Session PDF:
//   ecu.id            -> GET  /prog/ecu_info
//   security.seed     -> GET  /prog/security_access/1
//   security.key <hex>-> GET  /prog/security_access/2?key=<hex>
//   read.ecu           -> POST /prog/read_ecu
//   file.select <tag>  -> POST /prog/select_modified_file
//   flash.start         -> POST /prog/start_flash
//   flash.status        -> GET  /prog/flash_status (also auto-polls while flashing)
//   feature.list           -> local + /prog/state
//   feature.set <n> on/off -> POST /prog/feature_coding
//   immo.off / immo.on     -> POST /prog/security_extras
//   cp.remove / cp.restore -> POST /prog/security_extras
//   key.program             -> POST /prog/security_extras
//   bench.remove/power/tool -> POST /prog/bench_flash
//   dtc.clear                -> POST /prog/clear_dtc
//   report                    -> local summary of session state
//   clear / help               -> local
// ══════════════════════════════════════════════════════════════
