// ============================================================
// ECU Dashboard — script.js
// ============================================================

let currentMode = "live";
const socket = io("http://localhost:5000")
socket.on("connect", () => {
  console.log("Connected to server! ID:", socket.id); // 20-character unique ID
});

// Listen for a custom message event from the server
socket.on("analytics", (data) => {
    console.log("Message received from server:");
    console.log(data)
    if(typeof data === "string")
        updateLive(JSON.parse(data));
    else updateLive(data);

});

// Handle disconnections
socket.on("disconnect", () => {
    setStatus(false, "Connection error");
  console.log("Disconnected from server");
});
// Rolling buffers for live trend chart (60 ticks ≈ 24 sec at 400ms)
const LIVE_BUF = 60;
let bufTime  = [];
let bufSpeed = [];
let bufRpm   = [];

// ── Gauge init flags (avoid re-init on every poll) ──
let gaugesInitialized = false;

// ============================================================
// MODE SWITCHING
// ============================================================
function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach(b =>
        b.classList.toggle("active", b.dataset.mode === mode));
    document.getElementById("live-mode").classList.toggle("active", mode === "live");
    document.getElementById("history-mode").classList.toggle("active", mode === "history");
    if (mode === "history") loadHistory();
    // else pollLive();
}

// ============================================================
// STATUS HELPERS
// ============================================================
function setStatus(ok, msg) {
    const pill = document.getElementById("connection-status");
    const upd  = document.getElementById("last-update");
    if (!pill) return;
    if (ok) {
        pill.textContent = "● LIVE";
        pill.className = "status-pill status-ok";
        upd.textContent = new Date().toLocaleTimeString();
    } else {
        pill.textContent = "● " + (msg || "Disconnected");
        pill.className = "status-pill status-error";
    }
}

// ============================================================
// LIVE DATA FETCH  (fast — tail-read endpoint)
// ============================================================
async function fetchLiveData() {
    try {
        const res  = await fetch("/live-data");
        const data = await res.json();
        if (data.error) { setStatus(false, data.error); return null; }
        setStatus(true);
        return data;
    } catch(e) {
        setStatus(false, "Connection error");
        return null;
    }
}

// ============================================================
// UPDATE LIVE UI
// ============================================================
function updateLive(d) {

    // ── Engine state badge ──
    const badge = document.getElementById("engine-state-badge");
    badge.textContent = d.engine_state || "IDLE";
    const warnStates = ["BRAKING","STALLED","DEAD","OVERHEATING"];
    badge.className = "state-badge" + (warnStates.includes(d.engine_state) ? " warn" : "");

    // ── Gauges ──
    if(d.speed)
        updateGauge("speed-gauge",   d.speed,        0, 220,  "km/h", "#e8a020", "#0d0d0d");
    if(d.rpm)
        updateGauge("rpm-gauge",     d.rpm,          0, 7000, "RPM",  "#00c9a7", "#0d0d0d");
    if(d.fuel_pct)
        updateGauge("fuel-gauge",    d.fuel_pct,     0, 100,  "%",    "#2ecc71", "#0d0d0d");
    if(d.coolant_temp)
        updateGauge("coolant-gauge", d.coolant_temp, 40, 120, "°C",   "#e74c3c", "#0d0d0d");

    // ── Transmission panel ──
    if(d.gear && d.gear_num){
        const gearNum = d.gear_num || 0;
        document.getElementById("gear-display").textContent = gearNum === 0 ? "N" : gearNum;
        document.getElementById("gear-name").textContent    = d.gear || "Neutral";
    }


    if(d.clutch){
            const clutchEl = document.getElementById("clutch-val");
            clutchEl.textContent = d.clutch || "--";
            clutchEl.className   = "mc-val " + (d.clutch === "DOWN" ? "bad" : "ok");
    }
    if(d.brake){
            const brakeEl = document.getElementById("brake-val");
            brakeEl.textContent = d.brake || "--";
            brakeEl.className   = "mc-val " + (d.brake === "PRESSED" ? "bad" : "");
    }


    // ── Thermal panel ──
    if(d.coolant_temp){
            const cT = d.coolant_temp || 0;
            const coolantEl = document.getElementById("coolant-val");
            coolantEl.textContent = cT.toFixed(1);
            coolantEl.className   = "th-val" + (cT > 103 ? " hot" : cT < 60 ? " cool" : "");
    }

    if(d.oil_temp)
        setText("oil-val",     (d.oil_temp     || 0).toFixed(1));
    if(d.ambient_temp)
        setText("ambient-val", (d.ambient_temp || 0).toFixed(1));

    // ── Fuel panel ──
    if(d.fuel_pct){
        const fp = Math.max(0, Math.min(100, d.fuel_pct || 0));
        document.getElementById("fuel-bar").style.width = fp + "%";
        document.getElementById("fuel-pct-text").textContent  = fp.toFixed(1) + "%";
    }
    if(d.fuel_L){
        setText("fuel-l-val",    (d.fuel_l    || 0).toFixed(2));
        setText("fuel-rate-val", (d.fuel_rate || 0).toFixed(2));
    }

    // ── Motion panel ──
    if(d.accel)
        setText("accel-val",    (d.accel       || 0).toFixed(2));
    if(d.distance_km)
        setText("dist-val",     (d.distance_km || 0).toFixed(3));
    if(d.throttle)
        setText("throttle-val", (d.throttle_pct || 0).toFixed(1));
    if(d.engine_load)
        setText("load-val",     (d.engine_load  || 0).toFixed(1));

    if(d.battery_v){
        const batEl = document.getElementById("battery-val");
        batEl.textContent = (d.battery_v || 0).toFixed(2);
        batEl.className   = "th-val" + (d.battery_v < 12.2 ? " hot" : "");
    }
    if(d.revlim_v){
        const rlEl = document.getElementById("revlim-val");
        rlEl.textContent = d.rev_limiter ? "ACTIVE" : "OK";
        rlEl.className   = "th-val" + (d.rev_limiter ? " hot" : " cool");
    }


    // ── Advanced panel ──
    if (d.tyre_pressure) {
        setAdv("tyre-fl", d.tyre_pressure.fl + " psi");
        setAdv("tyre-fr", d.tyre_pressure.fr + " psi");
        setAdv("tyre-rl", d.tyre_pressure.rl + " psi");
        setAdv("tyre-rr", d.tyre_pressure.rr + " psi");
    }

    if(d.stall_risk)
        // const stallEl = document.getElementById("stall-val");
        stallEl.textContent = d.stall_risk ? "WARNING" : "OK";
        stallEl.className   = "adv-val " + (d.stall_risk ? "bad" : "ok");

    setAdv("door-lock-val", d.speed > 0 ? "Locked" : "Unlocked");

    // ── Rolling live chart buffers ──
    if(d.time)
        bufTime.push(d.time);
    if(d.speed)
        bufSpeed.push(d.speed);
    if(d.rpm)
        bufRpm.push(d.rpm);
    if (bufTime.length > LIVE_BUF) { bufTime.shift(); bufSpeed.shift(); bufRpm.shift(); }
    // updateLiveChart();
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function setAdv(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ============================================================
// PLOTLY GAUGE (Plotly.react for smooth update without re-init)
// ============================================================
function updateGauge(id, value, min, max, suffix, barColor, bgColor) {
    const lo  = min + (max - min) * 0.55;
    const mid = min + (max - min) * 0.82;

    Plotly.react(id,
        [{
            type:  "indicator",
            mode:  "gauge+number",
            value: value,
            number: { suffix: " " + suffix, font: { color: "#e8e8e8", size: 22, family: "Segoe UI" } },
            gauge: {
                axis: {
                    range: [min, max],
                    tickcolor: "#3a3a3a",
                    tickfont: { size: 9, color: "#7a7a7a" },
                    nticks: 8,
                },
                bar: { color: barColor, thickness: 0.28 },
                bgcolor: "#161616",
                borderwidth: 0,
                steps: [
                    { range: [min, lo],  color: "#1e1e1e" },
                    { range: [lo, mid],  color: "#252015" },
                    { range: [mid, max], color: "#2a1515" },
                ],
                threshold: {
                    line: { color: "#ffffff", width: 2 },
                    thickness: 0.8,
                    value: mid
                }
            }
        }],
        {
            margin: { t: 28, b: 8, l: 24, r: 24 },
            paper_bgcolor: "transparent",
            font: { color: "#e8e8e8" }
        },
        { responsive: true, displayModeBar: false }
    );
}

// ============================================================
// LIVE TREND CHART (dual trace: speed + RPM scaled)
// ============================================================
function updateLiveChart() {
    // Scale RPM to same axis as speed for overlay (RPM / 40 ≈ km/h range)
    const rpmScaled = bufRpm.map(r => r / 36);

    Plotly.react("live-chart",
        [
            {
                x: bufTime, y: bufSpeed,
                name: "Speed (km/h)",
                mode: "lines", type: "scatter",
                line: { color: "#e8a020", width: 2.5 },
                fill: "tozeroy", fillcolor: "rgba(232,160,32,0.08)"
            },
            {
                x: bufTime, y: rpmScaled,
                name: "RPM ÷ 36",
                mode: "lines", type: "scatter",
                line: { color: "#00c9a7", width: 1.5, dash: "dot" },
            }
        ],
        {
            margin: { t: 10, b: 36, l: 46, r: 16 },
            paper_bgcolor: "transparent",
            plot_bgcolor:  "transparent",
            font:  { color: "#7a7a7a", size: 11 },
            legend: { orientation: "h", x: 0, y: -0.25, font: { size: 11 } },
            xaxis: { title: "Time",      gridcolor: "#2a2a2a", zeroline: false },
            yaxis: { title: "Speed / RPM÷36", gridcolor: "#2a2a2a", zeroline: false },
        },
        { responsive: true, displayModeBar: false }
    );
}

// ============================================================
// ADVANCED PANEL TOGGLE
// ============================================================
function toggleAdvanced() {
    const panel = document.getElementById("advanced-panel");
    const btn   = document.getElementById("advanced-toggle");
    const open  = panel.classList.toggle("open");
    btn.classList.toggle("open", open);
    btn.textContent = open ? "Advanced ▴" : "Advanced ▾";
}

// ============================================================
// HISTORY MODE
// ============================================================
async function fetchHistoryData() {
    try {
        const res  = await fetch("/csv-data");
        const data = await res.json();
        if (data.error) { setStatus(false, data.error); return null; }
        return data;
    } catch(e) {
        setStatus(false, "Connection error");
        return null;
    }
}

async function loadHistory() {
    if (currentMode !== "history") return;
    const data = await fetchHistoryData();
    if (!data) return;
    renderHistoryChart(data);
    renderTable(data);
}

function getSlice(arr, rangeVal) {
    if (!arr || !arr.length) return [];
    if (rangeVal === "all") return arr;
    const n = parseInt(rangeVal, 10);
    return arr.slice(Math.max(0, arr.length - n));
}

// Signal key → {label, arr key in /csv-data response, line color}
const SIGNAL_MAP = {
    speed:       { label: "Speed (km/h)",       key: "speed",       color: "#e8a020" },
    rpm:         { label: "Engine RPM",          key: "rpm",         color: "#00c9a7" },
    coolant:     { label: "Coolant Temp (°C)",   key: "coolant",     color: "#e74c3c" },
    oil_temp:    { label: "Oil Temp (°C)",       key: "oil_temp",    color: "#f0722a" },
    fuel_pct:    { label: "Fuel Level (%)",      key: "fuel_pct",    color: "#2ecc71" },
    fuel_rate:   { label: "Fuel Rate (mL/s)",    key: "fuel_rate",   color: "#4a9eff" },
    throttle:    { label: "Throttle (%)",        key: "throttle",    color: "#f0722a" },
    engine_load: { label: "Engine Load (%)",     key: "engine_load", color: "#9b59b6" },
    accel:       { label: "Acceleration (m/s²)", key: "accel",       color: "#1abc9c" },
    battery:     { label: "Battery Voltage (V)", key: "battery",     color: "#f1c40f" },
    gear_num:    { label: "Gear Number",         key: "gear_num",    color: "#e8a020" },
};

function renderHistoryChart(data) {
    const sig  = document.getElementById("signal-select").value;
    const range = document.getElementById("range-select").value;
    const meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed;

    const xFull = data.time    || [];
    const yFull = data[meta.key] || [];

    const x = getSlice(xFull, range);
    const y = getSlice(yFull, range);

    Plotly.react("history-chart",
        [{
            x, y,
            mode: "lines", type: "scatter",
            name: meta.label,
            line: { color: meta.color, width: 2 },
            fill: "tozeroy",
            fillcolor: meta.color.replace(")", ", 0.07)").replace("rgb", "rgba")
                                  .replace("#e8a020", "rgba(232,160,32,0.07)")
                                  .replace("#00c9a7", "rgba(0,201,167,0.07)")
                                  .replace("#e74c3c", "rgba(231,76,60,0.07)")
                                  .replace("#f0722a", "rgba(240,114,42,0.07)")
                                  .replace("#2ecc71", "rgba(46,204,113,0.07)")
                                  .replace("#4a9eff", "rgba(74,158,255,0.07)")
                                  .replace("#9b59b6", "rgba(155,89,182,0.07)")
                                  .replace("#1abc9c", "rgba(26,188,156,0.07)")
                                  .replace("#f1c40f", "rgba(241,196,15,0.07)")
        }],
        {
            title: { text: meta.label, font: { color: "#e8e8e8", size: 14 } },
            margin: { t: 46, b: 50, l: 60, r: 24 },
            paper_bgcolor: "transparent",
            plot_bgcolor:  "transparent",
            font:  { color: "#7a7a7a", size: 11 },
            xaxis: { title: "Time",       gridcolor: "#2a2a2a", zeroline: false },
            yaxis: { title: meta.label,   gridcolor: "#2a2a2a", zeroline: false },
        },
        { responsive: true, displayModeBar: false }
    );
}

function renderTable(data) {
    const range = document.getElementById("range-select").value;
    const tbody = document.getElementById("table-body");
    tbody.innerHTML = "";

    const keys = ["time","gear","speed","rpm","coolant","oil_temp","fuel_pct","throttle","engine_state"];
    const all  = data.time || [];
    const n    = range === "all" ? all.length : Math.min(all.length, parseInt(range, 10));
    const start = all.length - n;

    for (let i = all.length - 1; i >= start; i--) {
        const tr = document.createElement("tr");
        tr.innerHTML = [
            data.time?.[i]         ?? "--",
            data.gear?.[i]         ?? "--",
            data.speed?.[i]        ?? "--",
            data.rpm?.[i]          ?? "--",
            (data.coolant?.[i]     ?? "--"),
            (data.oil_temp?.[i]    ?? "--"),
            (data.fuel_pct?.[i]    ?? "--"),
            (data.throttle?.[i]    ?? "--"),
            data.engine_state?.[i] ?? "--",
        ].map(v => `<td>${v}</td>`).join("");
        tbody.appendChild(tr);
    }
}

// ============================================================
// EVENT LISTENERS
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("signal-select")?.addEventListener("change", () => {
        if (currentMode === "history") loadHistory();
    });
    document.getElementById("range-select")?.addEventListener("change", () => {
        if (currentMode === "history") loadHistory();
    });
});

// ============================================================
// POLLING
// ============================================================
async function pollLive() {
    if (currentMode !== "live") return;
    const data = await fetchLiveData();
    if (data) updateLive(data);
}

// Live: fast tail-read (400 ms)
// setInterval(pollLive, 400);

// History: full CSV read (3 s, only when visible)
// setInterval(loadHistory, 3000);

// window.onload = () => pollLive();
