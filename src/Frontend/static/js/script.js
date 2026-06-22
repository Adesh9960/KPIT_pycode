// ═══════════════════════════════════════════════════════════════
// ECU Dashboard — script.js
// Socket.IO replaces SSE (matches new app.py with flask-socketio)
// UDS REST endpoints: /DID, /security_access, /diagnostics_session_control, /IO_control
// ═══════════════════════════════════════════════════════════════
"use strict";

let currentMode     = "live";
const LIVE_BUF      = 80;
let bufTime = [], bufSpeed = [], bufRpm = [];
let advSparkBuf     = { x: [], y: [] };
let techUnlocked    = false;
let progUnlocked    = false;
let secAttemptsLeft = 3;
let secLockout      = false;
let tpInterval      = null;
let lastSpeed       = 0;

const savedTheme = localStorage.getItem("ecu-theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);

// ══════════════════════════════════════════════════
// UDS SESSION UNLOCK
// ══════════════════════════════════════════════════
const UDS_SEQUENCE = ["0","x","1","0","0","x","0","3"];
let udsBuffer = [];

document.addEventListener("keydown", (e) => {
    if (["INPUT","SELECT","TEXTAREA","BUTTON"].includes(e.target.tagName)) return;
    udsBuffer.push(e.key.toLowerCase());
    if (udsBuffer.length > UDS_SEQUENCE.length) udsBuffer.shift();
    if (udsBuffer.join("") === UDS_SEQUENCE.join("")) {
        udsBuffer = [];
        if (!techUnlocked) showUDSModal();
    }
    checkBackdoor(e.key.toLowerCase());
});

const PROG_BACKDOOR = ["p","r","o","g","1","2","3"];
let progBuffer = [];
function checkBackdoor(key) {
    if (!techUnlocked) return;
    progBuffer.push(key);
    if (progBuffer.length > PROG_BACKDOOR.length) progBuffer.shift();
    if (progBuffer.join("") === PROG_BACKDOOR.join("")) {
        progBuffer = [];
        if (lastSpeed > 0) {
            showToastMessage("⚠ Pre-condition failed: vehicle must be stopped.", false);
            return;
        }
        enterProgrammingSessionBackdoor();
    }
}

let backdoorClearTimer = null;
document.addEventListener("keydown", () => {
    clearTimeout(backdoorClearTimer);
    backdoorClearTimer = setTimeout(() => { progBuffer = []; }, 3000);
});

function showUDSModal() { document.getElementById("uds-overlay").classList.add("visible"); }

function confirmTechUnlock() {
    techUnlocked = true;
    document.getElementById("uds-overlay").classList.remove("visible");
    const techBtn = document.getElementById("tech-tab-btn");
    if (techBtn) techBtn.classList.remove("hidden");
    const udsStatus = document.getElementById("uds-status");
    const udsLabel  = document.getElementById("uds-label");
    if (udsStatus) udsStatus.classList.add("extended");
    if (udsLabel)  udsLabel.textContent = "EXT 0x03";
    startTesterPresent();
    setMode("technician");
    sendSessionControl(3);
}

function cancelTechUnlock() { document.getElementById("uds-overlay").classList.remove("visible"); }

function exitTechMode() {
    if (progUnlocked) exitProgrammingSession();
    techUnlocked = false;
    stopTesterPresent();
    const techBtn = document.getElementById("tech-tab-btn");
    if (techBtn) techBtn.classList.add("hidden");
    const udsStatus = document.getElementById("uds-status");
    const udsLabel  = document.getElementById("uds-label");
    if (udsStatus) udsStatus.classList.remove("extended");
    if (udsLabel)  udsLabel.textContent = "DEFAULT";
    sendSessionControl(1);
    setMode("advanced");
}

function startTesterPresent() {
    if (tpInterval) return;
    const tpIndicator = document.getElementById("tp-indicator");
    if (tpIndicator) tpIndicator.classList.remove("hidden");
    tpInterval = setInterval(() => { sendTesterPresent(); }, 4000);
}

function stopTesterPresent() {
    if (tpInterval) { clearInterval(tpInterval); tpInterval = null; }
    const tpIndicator = document.getElementById("tp-indicator");
    if (tpIndicator) tpIndicator.classList.add("hidden");
}

async function sendTesterPresent() {
    try {
        await fetch("/diagnostics_session_control/3", { method: "GET" });
        const dot = document.querySelector(".tp-dot");
        if (dot) { dot.classList.add("tp-flash"); setTimeout(() => dot.classList.remove("tp-flash"), 200); }
    } catch(_) {}
}

document.addEventListener("visibilitychange", () => {
    if (document.hidden && techUnlocked) {
        showToastMessage("⚠ Tab hidden — TesterPresent paused. Session may drop.", false);
    }
});

// ══════════════════════════════════════════════════
// PROGRAMMING SESSION ACTIVATION LOGIC
// ══════════════════════════════════════════════════
function showProgPanel() {
    // Reveal the new Programming tab in the navbar
    const progBtn = document.getElementById("prog-tab-btn");
    if (progBtn) progBtn.classList.remove("hidden");
    
    // Automatically switch the dashboard over to the new Programming page
    setMode("programming");
}

function enterProgrammingSessionBackdoor() {
    progUnlocked = true;
    showProgPanel();
    updateProgControls(true);
    updateSessionDisplay("PROG 0x02");
    showToastMessage("Programming session entered via alternate access.", false);
    sendSessionControl(2);
}

function exitProgrammingSession() {
    progUnlocked = false;
    
    // Hide the tab button again
    const progBtn = document.getElementById("prog-tab-btn");
    if (progBtn) progBtn.classList.add("hidden");
    
    updateProgControls(false);
    updateSessionDisplay("EXT 0x03");
    sendSessionControl(3);
    
    // Drop the user back to the technician tab
    setMode("technician");
}
function updateSessionDisplay(label) {
    const el = document.getElementById("uds-label");
    const udsStatus = document.getElementById("uds-status");
    if (el) el.textContent = label;
    
    if (udsStatus) {
        udsStatus.classList.remove("extended", "programming");
        if (label.includes("EXT")) udsStatus.classList.add("extended");
        if (label.includes("PRG")) udsStatus.classList.add("programming");
    }
    
    const can = document.getElementById("can-session-display");
    if (can) can.textContent = label;
}
// ⚠️ IMPORTANT: Update these two functions to use "PRG 0x02" instead of "PROG 0x02"
function enterProgrammingSessionBackdoor() {
    progUnlocked = true;
    showProgPanel();
    updateProgControls(true);
    updateSessionDisplay("PRG 0x02"); // <-- Changed to match image
    showToastMessage("Programming session entered via alternate access.", false);
    sendSessionControl(2);
}

function updateProgControls(enabled) {
    const resetBtn = document.getElementById("btn-ecu-reset");
    if (resetBtn) resetBtn.disabled = !enabled;
    const dtcClear = document.getElementById("dtc-clear-btn");
    if (dtcClear) dtcClear.disabled = !enabled;
    const wrap = document.getElementById("prog-controls-wrap");
    if (wrap) wrap.style.opacity = enabled ? "1" : "0.4";
}

// ══════════════════════════════════════════════════
// UDS REST CALLS
// ══════════════════════════════════════════════════
async function readDID(did, targetId, unit) {
    showUDSResponse(`Sending 0x22 ${hexStr(did)} ...`);
    try {
        const res  = await fetch(`/DID/${did}`);
        const data = await res.json();
        if (data.status === "success") {
            const val = data.data != null ? data.data : "—";
            setText(targetId, val + (unit ? " " + unit : ""));
            showUDSResponse(`0x62 ${hexStr(did)} → ${val} ${unit}  [Positive Response]`);
        } else {
            setText(targetId, "NRC");
            showUDSResponse(`0x7F 0x22 — ${data.message || "Request failed"}`);
        }
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function writeDID(did, value) {
    showUDSResponse(`Sending 0x2E ${hexStr(did)} ${value} ...`);
    try {
        const res  = await fetch("/DID", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ DID: did, value: value }) });
        const data = await res.json();
        if (data.status === "success") { showUDSResponse(`0x6E ${hexStr(did)} — Write successful [Positive Response]`); }
        else { showUDSResponse(`0x7F 0x2E — ${data.data || "Write failed"}`); }
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function requestSeed() {
    if (secLockout) { showUDSResponse("0x7F 0x27 0x37 — Required time delay not expired"); return; }
    if (lastSpeed > 0) {
        showUDSResponse("0x7F 0x10 0x22 — conditionsNotCorrect: vehicle moving");
        showToastMessage("Pre-condition failed: vehicle must be stopped.", true); return;
    }
    showUDSResponse("Sending 0x27 0x01 — Request Seed ...");
    try {
        const res  = await fetch("/security_access/1");
        const data = await res.json();
        if (data.status === "success") {
            const seed = data.message || "0xABCD";
            document.getElementById("prog-seed-display").textContent = seed;
            document.getElementById("btn-send-key").disabled = false;
            showUDSResponse(`0x67 0x01 ${seed} — Seed received`);
        } else { showUDSResponse(`0x7F 0x27 — ${data.message}`); }
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function sendKey() {
    const key = document.getElementById("prog-key-input").value.trim();
    if (!key) { showUDSResponse("Enter a key value first"); return; }
    showUDSResponse(`Sending 0x27 0x02 ${key} ...`);
    try {
        const res  = await fetch("/security_access/2");
        const data = await res.json();
        if (data.status === "success") {
            progUnlocked = true;
            showProgPanel();
            updateProgControls(true);
            updateSessionDisplay("PRG 0x02");
            sendSessionControl(2);
            showUDSResponse("0x67 0x02 — Security Access Granted [Positive Response]");
            secAttemptsLeft = 3;
            setText("sec-attempts-left", "3");
        } else {
            secAttemptsLeft = Math.max(0, secAttemptsLeft - 1);
            setText("sec-attempts-left", String(secAttemptsLeft));
            if (secAttemptsLeft === 0) {
                secLockout = true;
                const lockMsg = document.getElementById("prog-lockout-msg");
                if (lockMsg) lockMsg.classList.remove("hidden");
                showUDSResponse("0x7F 0x27 0x36 — Exceeded number of attempts. Locked.");
                setTimeout(() => {
                    secLockout = false; secAttemptsLeft = 3;
                    setText("sec-attempts-left","3");
                    const lm = document.getElementById("prog-lockout-msg");
                    if (lm) lm.classList.add("hidden");
                }, 30000);
            } else { showUDSResponse(`0x7F 0x27 0x35 — Invalid key. ${secAttemptsLeft} attempt(s) remaining.`); }
        }
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function ioControl(did, controlParam, controlState) {
    const stateNames = { "F410": "io-headlamp-state", "F411": "io-radfan-state", "F412": "io-fuelpump-state" };
    const didHex = did.toString(16).toUpperCase();
    const stateId = stateNames[didHex];
    const label = controlParam === 0 ? "ECU CONTROL" : (controlState ? "FORCED ON" : "FORCED OFF");
    showUDSResponse(`Sending 0x2F ${hexStr(did)} ${controlParam} ${controlState} ...`);
    try {
        const res  = await fetch("/IO_control", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ DID: did, control_parameter: controlParam, control_state: controlState }) });
        const data = await res.json();
        if (data.status === "success") {
            if (stateId) setText(stateId, label);
            showUDSResponse(`0x6F ${hexStr(did)} — IO Control applied: ${label}`);
        } else { showUDSResponse(`0x7F 0x2F — ${data.message}`); }
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function sendSessionControl(session) {
    try { await fetch(`/diagnostics_session_control/${session}`); } catch(_) {}
}

async function ecuReset() {
    if (!progUnlocked) { showUDSResponse("0x7F 0x11 0x33 — Security access denied"); return; }
    if (!confirm("Hard reset will clear session, adaptations and restart signal generation. Continue?")) return;
    showUDSResponse("Sending 0x11 0x01 — Hard Reset ...");
    try {
        const res  = await fetch("/diagnostics_session_control/1");
        const data = await res.json();
        showUDSResponse("0x51 0x01 — ECU Reset acknowledged. Returning to Default session.");
        exitProgrammingSession();
        exitTechMode();
    } catch(e) { showUDSResponse(`Error: ${e.message}`); }
}

async function clearDTCs() {
    if (!progUnlocked) { showUDSResponse("0x7F 0x14 0x33 — Security access denied"); return; }
    showUDSResponse("Sending 0x14 0xFF 0xFF 0xFF — Clear all DTCs ...");
    setTimeout(() => {
        document.getElementById("tech-dtc-list").innerHTML = '<div class="tech-dtc-empty">No DTCs stored. All systems nominal.</div>';
        setText("dtc-count-badge", "No Active DTCs");
        document.getElementById("dtc-count-badge").className = "dtc-count-badge ok";
        showUDSResponse("0x54 — DTCs cleared successfully [Positive Response]");
    }, 600);
}

function showUDSResponse(msg) {
    setText("uds-response-text", msg);
    const bar = document.getElementById("tech-uds-response");
    if (bar) { bar.classList.add("uds-resp-flash"); setTimeout(() => bar.classList.remove("uds-resp-flash"), 400); }
}

function hexStr(val) { return "0x" + val.toString(16).toUpperCase().padStart(4,"0"); }

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("ecu-theme", next);
}

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".tab-btn").forEach(b =>
        b.classList.toggle("active", b.dataset.mode === mode));
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    const target = document.getElementById(mode + "-mode");
    if (target) {
        requestAnimationFrame(() => target.classList.add("active"));
    }
    // Updated line to also strip mode-programming
    document.body.classList.remove("mode-live","mode-advanced","mode-technician","mode-history","mode-programming");
    document.body.classList.add("mode-" + mode);
    if (mode === "history") loadHistory();
}

function setStatus(ok, msg) {
    const pill  = document.getElementById("connection-status");
    const upd   = document.getElementById("last-update");
    const dot   = document.getElementById("conn-dot");
    const label = document.getElementById("conn-label");
    if (ok) {
        if (pill)  { pill.textContent = "● LIVE"; pill.className = "status-pill ok"; }
        if (upd)   upd.textContent = new Date().toLocaleTimeString();
        if (dot)   dot.classList.add("live");
        if (label) label.textContent = "LIVE";
    } else {
        if (pill)  { pill.textContent = "● " + (msg || "Disconnected"); pill.className = "status-pill error"; }
        if (dot)   dot.classList.remove("live");
        if (label) label.textContent = msg || "ERROR";
    }
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function showToastMessage(msg, critical) {
    const stack = document.getElementById("alert-toast-stack");
    if (!stack) return;
    const toast = document.createElement("div");
    toast.className = "alert-toast" + (critical ? " crit" : "");
    toast.innerHTML = `
        <div class="alert-toast-head">${critical ? "🔴 CRITICAL" : "⚠️ WARNING"}</div>
        <div class="alert-toast-body">${msg}</div>
        <div class="alert-toast-bar"><div class="alert-toast-bar-fill"></div></div>
    `;
    stack.appendChild(toast);
    const fill = toast.querySelector(".alert-toast-bar-fill");
    setTimeout(() => { if (fill) { fill.style.transition="width 6s linear"; fill.style.width="0%"; } }, 50);
    setTimeout(() => { toast.classList.add("closing"); setTimeout(() => toast.remove(), 220); }, 6000);
}

function startClock() {
    const timeEl = document.getElementById("sys-time");
    const liveDateEl = document.getElementById("live-date-display");
    const advDateEl = document.getElementById("adv-date-display");
    setInterval(() => {
        const now = new Date();
        if (timeEl) timeEl.textContent = now.toLocaleTimeString("en-IN", { hour12: false });
        const dateStr = now.toLocaleDateString("en-IN", { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase(); 
        if (liveDateEl) liveDateEl.textContent = dateStr;
        if (advDateEl) advDateEl.textContent = dateStr;
    }, 1000);
}

const ALERT_RULES = [
    { key:"coolant_high", critical:true, targets:["coolantTemp","sn-cool","adv-cool-mini"], test: d => (d.coolant||d.coolant_temp||0) > 110, message: d => `Coolant ${(d.coolant||d.coolant_temp||0).toFixed(1)}°C — engine overheating.` },
    { key:"oil_temp_high", critical:true, targets:["oil-val","sn-oil","adv-oiltemp-kpi"], test: d => (d.oil_temp||0) > 130, message: d => `Oil temp ${(d.oil_temp||0).toFixed(1)}°C — above safe range.` },
    { key:"voltage_low", critical:false, targets:["batteryVoltage","sn-volt"], test: d => (d.voltage||d.battery_v||0) < 12.0, message: d => `Battery voltage low (${(d.voltage||d.battery_v||0).toFixed(2)} V).` },
    { key:"fuel_low", critical:false, targets:["fuelLevel","sn-fuel","adv-fuel-mini"], test: d => (d.fuel||d.fuel_pct||0) < 10, message: d => `Low fuel — ${(d.fuel||d.fuel_pct||0).toFixed(1)}% remaining.` },
    { key:"stall_risk", critical:true, targets:["adv-stall-badge"], test: d => !!(d.stall_risk), message: () => `Stall risk — low RPM at low speed. Press clutch or shift down.` },
    { key:"rev_limiter", critical:false, targets:["revlim-val","adv-revlim-badge"], test: d => !!(d.rev_limiter), message: () => `Rev limiter engaged — back off the throttle.` }
];

const activeAlerts = {};
function applyHighlight(targets, critical) { targets.forEach(id => { const el = document.getElementById(id); if (el) { el.classList.remove("param-warn","param-crit"); el.classList.add(critical ? "param-crit" : "param-warn"); }});}
function clearHighlight(targets) { targets.forEach(id => { const el = document.getElementById(id); if (el) el.classList.remove("param-warn","param-crit"); });}
function spawnToast(rule, msg) {
    const stack = document.getElementById("alert-toast-stack");
    if (!stack) return null;
    const toast = document.createElement("div");
    toast.className = "alert-toast" + (rule.critical ? " crit" : "");
    toast.innerHTML = `
        <div class="alert-toast-head">${rule.critical ? "🔴 CRITICAL" : "⚠️ WARNING"}</div>
        <div class="alert-toast-body">${msg}</div>
        ${rule.critical ? `<button class="alert-toast-ack" onclick="dismissToast('${rule.key}',false)">✓ Acknowledge</button>` : `<div class="alert-toast-bar"><div class="alert-toast-bar-fill"></div></div>`}
    `;
    stack.appendChild(toast);
    if (!rule.critical) {
        const fill = toast.querySelector(".alert-toast-bar-fill");
        setTimeout(() => { if (fill) { fill.style.transition="width 10s linear"; fill.style.width="0%"; } }, 50);
        const timer = setTimeout(() => dismissToast(rule.key, false), 10000);
        if (activeAlerts[rule.key]) activeAlerts[rule.key].autoTimer = timer;
    }
    return toast;
}
function dismissToast(key, deleteEntry=true) {
    const entry = activeAlerts[key];
    if (!entry || !entry.toastEl) return;
    if (entry.autoTimer) { clearTimeout(entry.autoTimer); entry.autoTimer=null; }
    const el = entry.toastEl;
    el.classList.add("closing");
    setTimeout(() => { if (el.parentNode) el.remove(); }, 220);
    entry.toastEl = null;
    if (deleteEntry) delete activeAlerts[key];
}
function checkAlerts(d) {
    ALERT_RULES.forEach(rule => {
        let triggered = false;
        try { triggered = !!rule.test(d); } catch(_) { triggered=false; }
        if (triggered) {
            applyHighlight(rule.targets, rule.critical);
            if (!activeAlerts[rule.key]) {
                activeAlerts[rule.key] = { critical:rule.critical, toastEl:null, autoTimer:null };
                activeAlerts[rule.key].toastEl = spawnToast(rule, rule.message(d));
            }
        } else {
            if (activeAlerts[rule.key]) { clearHighlight(rule.targets); dismissToast(rule.key, true); }
        }
    });
}

function updateLive(d) {
    lastSpeed = d.speed || 0;
    if (d.date) setText("live-date-display", d.date);

    const badge = document.getElementById("engine-state-badge");
    if (badge) { badge.textContent = d.engine_state || "IDLE"; badge.className = "state-badge" + (["BRAKING","STALLED","DEAD","OVERHEATING"].includes(d.engine_state) ? " warn" : ""); }

    updateGauge("speed-gauge", d.speed||0, 0, 220, "km/h", "#00d4aa", "#0a1a14");
    updateGauge("rpm-gauge", d.rpm||0, 0, 7000, "RPM", "#4ade80", "#0a1a14");
    updateGauge("fuel-gauge", d.fuel||d.fuel_pct||0, 0, 100, "%", "#34d399", "#0a1a14");

    setText("distance-main-val", (d.distance_km||0).toFixed(2));

    const fr = d.fuel_rate || 0, sp = d.speed || 0, fuelL = d.remaining_fuel_l || d.fuel_l || 0;
    const econKmL = (fr > 0.01 && sp > 0) ? (sp / (fr * 3.6)).toFixed(1) : "--";
    const estRange = (fr > 0.01 && sp > 0) ? Math.round((fuelL*1000/fr/3600)*sp) + " km" : "-- km";
    setText("fuel-economy", econKmL === "--" ? "-- km/L" : econKmL + " km/L");
    setText("est-range", estRange);

    const gn = d.gear_num || 0;
    setText("gear-display", gn === 0 ? "N" : String(gn));
    setText("gear-name", d.gear || "Neutral");
    const rpm = d.rpm || 0;
    const shiftHint = document.getElementById("shift-hint");
    if (shiftHint) {
        if (rpm > 5500) { shiftHint.textContent = "⬆ SHIFT UP"; shiftHint.style.color = "#f87171"; }
        else if (rpm < 1200 && gn > 1) { shiftHint.textContent = "⬇ SHIFT DOWN"; shiftHint.style.color = "#fbbf24"; }
        else { shiftHint.textContent = "—"; shiftHint.style.color = ""; }
    }

    const clutchEl  = document.getElementById("chip-clutch"), clutchVal = document.getElementById("clutch-val"), clutchState = d.clutch_state || d.clutch || "UP";
    if (clutchVal) clutchVal.textContent = clutchState;
    if (clutchEl) clutchEl.classList.toggle("active", clutchState === "DOWN");

    const brakeEl  = document.getElementById("chip-brake"), brakeVal = document.getElementById("brake-val"), brakeState = d.brake_state || d.brake || "OFF";
    if (brakeVal) brakeVal.textContent = brakeState;
    if (brakeEl) brakeEl.classList.toggle("active", brakeState === "PRESSED");

    const cT = d.coolant || d.coolant_temp || 0, coolEl = document.getElementById("coolantTemp");
    if (coolEl) { coolEl.textContent = cT.toFixed(1); coolEl.className = "lv-th-val" + (cT > 103 ? " hot" : cT < 60 ? " cool" : ""); }
    setText("oil-val", (d.oil_temp||0).toFixed(1));
    setText("ambient-val", (d.ambient_temp||0).toFixed(1));
    setText("eng-state-text", d.engine_state || "IDLE");

    const warmupPct = Math.min(100, Math.max(0, ((cT - 30) / 60) * 100));
    setText("warmup-pct", warmupPct.toFixed(0));
    const warmBar = document.getElementById("bar-warmup"); if (warmBar) warmBar.style.width = warmupPct + "%";
    const coolBar = document.getElementById("bar-coolant"); if (coolBar) { coolBar.style.width = Math.min(100,((cT-40)/80)*100).toFixed(0)+"%"; coolBar.style.background = cT>103?"#f87171":"#00d4aa"; }

    const fp = Math.max(0, Math.min(100, d.fuel||d.fuel_pct||0)), fb = document.getElementById("fuel-bar");
    if (fb) fb.style.width = fp + "%";
    setText("fuelLevel", fp.toFixed(1) + "%");
    setText("fuel-l-val", (d.remaining_fuel_l||d.fuel_l||0).toFixed(2));
    setText("fuel-rate-val",(d.fuel_rate||0).toFixed(2));

    setText("fuel-pump-val", d.fuel_pump != null ? (d.fuel_pump ? "ON" : "OFF") : "--");
    setText("headlamp-val",  d.head_lamp  != null ? (d.head_lamp  ? "ON" : "OFF") : "--");
    setText("radfan-val",    d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "--");

    const bv = d.voltage || d.battery_v || 0, batEl = document.getElementById("batteryVoltage");
    if (batEl) { batEl.textContent = bv.toFixed(2); batEl.className = "lv-th-val" + (bv < 12.2 ? " hot" : ""); }
    const battBar = document.getElementById("bar-batt");
    if (battBar) { battBar.style.width = Math.min(100,((bv-11)/4)*100).toFixed(0)+"%"; battBar.style.background = bv<12?"#f87171":bv<12.5?"#fbbf24":"#34d399"; }

    const rlEl = document.getElementById("revlim-val");
    if (rlEl) { rlEl.textContent = d.rev_limiter ? "ACTIVE" : "OK"; rlEl.className = "lv-th-val"+(d.rev_limiter?" hot":" cool"); }
    const stallEl = document.getElementById("stall-live");
    if (stallEl) { stallEl.textContent = d.stall_risk ? "WARNING" : "OK"; stallEl.className = "lv-th-val"+(d.stall_risk?" hot":" cool"); }

    updatePreConditions(d.speed||0);

    bufTime.push(d.time); bufSpeed.push(d.speed||0); bufRpm.push(d.rpm||0);
    if (bufTime.length > LIVE_BUF) { bufTime.shift(); bufSpeed.shift(); bufRpm.shift(); }
    updateLiveChart();
}

function updatePreConditions(speed) {
    const isStopped = (speed === 0);
    const progPcSpeed = document.getElementById("prog-pc-speed");
    if (progPcSpeed) {
        const dot = progPcSpeed.querySelector(".prog-pc-dot");
        if (dot) dot.className = isStopped ? "prog-pc-dot prog-ok" : "prog-pc-dot prog-bad";
        const val = progPcSpeed.querySelector("#prog-speed-val");
        if (val) val.textContent = speed + " km/h";
    }
    const btnSeed = document.getElementById("btn-request-seed");
    if (btnSeed) btnSeed.disabled = !isStopped;
}

function updateAdvanced(d) {
    const tyres = d.tyres || d.tyre_pressure || {};
    const bv = d.voltage || d.battery_v || 0, bsoc = Math.max(0, Math.min(100, ((bv-11.8)/(14.4-11.8))*100));
    const fuel = d.fuel || d.fuel_pct || 0, cool = d.coolant || d.coolant_temp || 0, ot = d.oil_temp || 0, fr = d.fuel_rate || 0, sp = d.speed || 0, fuelL = d.remaining_fuel_l || d.fuel_l || 0;

    setText("adv-rpm-hero", (d.rpm||0).toLocaleString());
    setText("adv-load-hero", (d.engine_load||0).toFixed(1) + "%");
    setText("adv-iat-hero", (d.ambient_temp||0).toFixed(1) + "°C");
    setText("adv-throttle-hero", (d.throttle_pct||0).toFixed(1) + "%");

    setText("adv-engine-state-chip", d.engine_state || "IDLE");
    setText("adv-gear-chip", (d.gear_num||0)===0 ? "N" : String(d.gear_num));
    setText("adv-brake-chip", "BRAKE: " + (d.brake_state||d.brake||"OFF"));
    setText("adv-clutch-chip", "CLUTCH: " + (d.clutch_state||d.clutch||"UP"));

    setText("adv-speed-big", sp + " km/h");
    setText("adv-accel-mini", (d.accel_ms2||d.accel||0).toFixed(2));
    setText("adv-dist-mini", (d.distance_km||0).toFixed(2));
    setText("adv-fuel-mini", fuel.toFixed(1));
    setText("adv-cool-mini", cool.toFixed(1));

    setText("sn-fuel", fuel.toFixed(1) + "%"); setText("sn-oil", ot.toFixed(1) + "°C"); setText("sn-cool", cool.toFixed(1) + "°C"); setText("sn-volt", bv.toFixed(2) + " V");
    setText("sn-rpm", (d.rpm||0).toLocaleString()); setText("sn-fuelrate", fr.toFixed(2) + " mL/s"); setText("sn-dist", (d.distance_km||0).toFixed(3) + " km");
    setText("sn-headlamp", d.head_lamp != null ? (d.head_lamp ? "ON" : "OFF") : "—"); setText("sn-radfan", d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "—");

    if (d.date) setText("adv-date-display", d.date);

    setText("adv-batt", bsoc.toFixed(1) + "%"); setText("adv-batt-sub", bv.toFixed(2) + " V · " + (bv > 13.5 ? "Charging" : "Draining"));
    const battBar = document.getElementById("adv-batt-bar"); if (battBar) { battBar.style.width = bsoc.toFixed(1)+"%"; battBar.style.background = bsoc>50?"#10b981":bsoc>25?"#f59e0b":"#ef4444"; }
    setText("adv-alt", bv.toFixed(2) + " V"); setText("adv-alt-sub", bv > 13.5 ? "Alternator charging" : "Running on battery");
    const altBar = document.getElementById("adv-alt-bar"); if (altBar) altBar.style.width = Math.min(100,((bv-11)/4)*100).toFixed(0)+"%";
    setText("adv-oiltemp-kpi", ot.toFixed(1) + " °C");
    const otBar = document.getElementById("adv-oiltemp-bar"); if (otBar) { otBar.style.width=Math.min(100,((ot-40)/80)*100).toFixed(0)+"%"; otBar.style.background=ot>110?"#ef4444":"#f59e0b"; }
    setText("adv-fuelrate-kpi", fr.toFixed(2) + " mL/s");
    const frBar = document.getElementById("adv-fuelrate-bar"); if (frBar) { frBar.style.width=Math.min(100,(fr/12)*100).toFixed(0)+"%"; frBar.style.background=fr>8?"#ef4444":"#f59e0b"; }
    const estKm = (fr>0.01&&sp>0) ? Math.round((fuelL*1000/fr/3600)*sp) : 0;
    setText("adv-range-kpi", estKm > 0 ? estKm + " km" : "—");
    const rngBar = document.getElementById("adv-range-bar"); if (rngBar) rngBar.style.width = Math.min(100,(estKm/400)*100).toFixed(0)+"%";

    if (tyres.fl != null) { setTyre("t-fl","t-fl-bar",tyres.fl); setTyre("t-fr","t-fr-bar",tyres.fr); setTyre("t-rl","t-rl-bar",tyres.rl); setTyre("t-rr","t-rr-bar",tyres.rr); }

    const rlBadge = document.getElementById("adv-revlim-badge"), rlDot = document.getElementById("adv-revlim-dot");
    if (d.rev_limiter) { if (rlBadge) { rlBadge.textContent="ACTIVE"; rlBadge.className="adv-pill adv-pill-bad"; } if (rlDot) rlDot.style.background="#ef4444"; setText("adv-revlim-sub","Rev limiter triggered!"); }
    else { if (rlBadge) { rlBadge.textContent="STANDBY"; rlBadge.className="adv-pill adv-pill-warn"; } if (rlDot) rlDot.style.background="#f59e0b"; setText("adv-revlim-sub","Monitoring"); }
    const stBadge = document.getElementById("adv-stall-badge"), stDot = document.getElementById("adv-stall-dot");
    if (d.stall_risk) { if (stBadge) { stBadge.textContent="WARNING"; stBadge.className="adv-pill adv-pill-bad"; } if (stDot) stDot.style.background="#ef4444"; setText("adv-stall-sub","Low RPM + low speed"); }
    else { if (stBadge) { stBadge.textContent="OK"; stBadge.className="adv-pill adv-pill-ok"; } if (stDot) stDot.style.background="#10b981"; setText("adv-stall-sub","All clear"); }

    advSparkBuf.x.push(d.time); advSparkBuf.y.push(sp);
    if (advSparkBuf.x.length > 60) { advSparkBuf.x.shift(); advSparkBuf.y.shift(); }
    Plotly.react("adv-speed-chart", [{ x:advSparkBuf.x, y:advSparkBuf.y, mode:"lines", type:"scatter", line:{color:"#7c3aed",width:2,shape:"spline"}, fill:"tozeroy", fillcolor:"rgba(124,58,237,0.08)" }], { margin:{t:4,b:4,l:4,r:4}, paper_bgcolor:"transparent", plot_bgcolor:"transparent", xaxis:{visible:false}, yaxis:{visible:false}, showlegend:false }, { responsive:true, displayModeBar:false });
}

function setTyre(valId, barId, psi) {
    const el = document.getElementById(valId), barEl = document.getElementById(barId);
    if (psi == null) return;
    const color = psi < 26 ? "#ef4444" : psi < 29 ? "#f59e0b" : "#10b981";
    if (el) { el.innerHTML = psi.toFixed(1) + ' <span class="adv-tyre-unit">psi</span>'; el.style.color = color; }
    if (barEl) { barEl.style.width=Math.min(100,(psi/36)*100).toFixed(0)+"%"; barEl.style.background=color; }
}

function updateTechnician(d) {
    if (!techUnlocked) return;
    const tyres = d.tyres || d.tyre_pressure || {}, bv = d.voltage || d.battery_v || 0, bsoc = Math.max(0, Math.min(100, ((bv-11.8)/(14.4-11.8))*100));

    setText("tech-rpm", (d.rpm||0).toLocaleString() + " RPM"); setText("tech-load", (d.engine_load||0).toFixed(1) + "%"); setText("tech-throttle", (d.throttle_pct||0).toFixed(1) + "%"); setText("tech-coolant", (d.coolant||d.coolant_temp||0).toFixed(1) + "°C"); setText("tech-oiltemp", (d.oil_temp||0).toFixed(1) + "°C"); setText("tech-fuelrate", (d.fuel_rate||0).toFixed(2) + " mL/s"); setText("tech-accel", (d.accel_ms2||d.accel||0).toFixed(2) + " m/s²"); setText("tech-stall", d.stall_risk ? "⚠ YES" : "NO"); setText("tech-engstate", d.engine_state || "IDLE");
    setText("tech-gear", d.gear || "Neutral"); setText("tech-gearnum", (d.gear_num||0)===0 ? "N" : String(d.gear_num)); setText("tech-clutch", d.clutch_state||d.clutch||"UP"); setText("tech-brake", d.brake_state||d.brake||"OFF"); setText("tech-transtemp",(d.oil_temp||0).toFixed(1)+"°C");
    setText("tech-speed", (d.speed||0) + " km/h"); const wsp = d.speed||0; setText("tech-wfl", wsp + " km/h"); setText("tech-wfr", wsp + " km/h"); setText("tech-wrl", wsp + " km/h"); setText("tech-wrr", wsp + " km/h"); setText("tech-brakepsi", (d.brake_state||d.brake)==="PRESSED" ? "12 bar" : "0 bar");
    setText("tech-batt", bv.toFixed(2) + " V"); setText("tech-soc", bsoc.toFixed(1) + "%"); setText("tech-alt", bv > 13.5 ? "CHARGING" : "IDLE"); setText("tech-headlamp", d.head_lamp != null ? (d.head_lamp ? "ON" : "OFF") : "—"); setText("tech-radfan", d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "—"); setText("tech-fuelpump", d.fuel_pump != null ? (d.fuel_pump ? "ON" : "OFF") : "—");
    if (tyres.fl != null) { setText("tech-tfl", tyres.fl.toFixed(1) + " psi"); setText("tech-tfr", tyres.fr.toFixed(1) + " psi"); setText("tech-trl", tyres.rl.toFixed(1) + " psi"); setText("tech-trr", tyres.rr.toFixed(1) + " psi"); }

    const msgRate = 40 + Math.floor(Math.random() * 20), busLoad = Math.round((msgRate / 200) * 100);
    setText("tech-can-load", busLoad + "%"); setText("tech-can-msgrate", msgRate + " msg/s"); setText("tech-can-errrate", "0 err/s"); setText("tech-can-latency", (Math.random() * 5 + 1).toFixed(1) + " ms");
    addSnifferRow(d);
}

const snifferCanIds = ["0x7E0","0x7E1","0x7E2","0x7E3","0x200","0x100"];
const snifferSigs   = ["Engine_RPM","Gear","Wheel_Speed","Battery_V","Speed_kmh","Throttle_Pct"];
let snifferRowCount = 0;
function addSnifferRow(d) {
    const body = document.getElementById("tech-sniffer-body");
    if (!body) return;
    snifferRowCount++;
    const idx  = snifferRowCount % snifferCanIds.length;
    const values = [d.rpm||0, d.gear_num||0, d.speed||0, d.voltage||0, d.speed||0, d.throttle_pct||0];
    const hexVal = Math.round(values[idx]).toString(16).toUpperCase().padStart(4,"0");
    const hexData = `0x${hexVal.slice(0,2)} 0x${hexVal.slice(2,4)}`;
    const row = document.createElement("div"); row.className = "tech-sniffer-row";
    row.innerHTML = `<span class="tech-sr-time">${d.time||"--"}</span><span class="tech-sr-id">${snifferCanIds[idx]}</span><span class="tech-sr-data">${hexData}</span><span class="tech-sr-sig">${snifferSigs[idx]}</span><span class="tech-sr-val">${values[idx].toFixed ? values[idx].toFixed(1) : values[idx]}</span>`;
    body.insertBefore(row, body.firstChild);
    while (body.children.length > 30) body.removeChild(body.lastChild);
}

function updateGauge(id, value, min, max, suffix, barColor, bgInner) {
    const lo = min + (max-min) * 0.55, mid = min + (max-min) * 0.82;
    const isDark = document.documentElement.getAttribute("data-theme") !== "light", numColor = isDark ? "#e8f5ee" : "#0f1f14", bgColor = "transparent";
    const step1 = isDark ? "#0d1a12" : "#ddf0e6", step2 = isDark ? "#142010" : "#c5e4d0", step3 = isDark ? "#1f1208" : "#f5ddc0";
    Plotly.react(id, [{ type:"indicator", mode:"gauge+number", value:value, number:{ suffix:" "+suffix, font:{color:numColor, size:22, family:"Inter,Segoe UI"} }, gauge:{ axis:{ range:[min,max], tickcolor:isDark?"#1e3a28":"#aac8b8", tickfont:{size:9,color:isDark?"#4a7a5a":"#5a8a6a"}, nticks:8 }, bar:{ color:barColor, thickness:0.3 }, bgcolor:bgColor, borderwidth:0, steps:[{range:[min,lo],color:step1},{range:[lo,mid],color:step2},{range:[mid,max],color:step3}], threshold:{ line:{color:isDark?"rgba(255,255,255,0.3)":"rgba(0,0,0,0.2)",width:2}, thickness:0.8, value:mid } } }], { margin:{t:28,b:8,l:24,r:24}, paper_bgcolor:bgColor, font:{color:numColor} }, { responsive:true, displayModeBar:false });
}

function updateLiveChart() {
    const rpmScaled = bufRpm.map(r => r / 36), isDark = document.documentElement.getAttribute("data-theme") !== "light", gridColor = isDark ? "#1a2e20" : "#d0e8da", fontColor = isDark ? "#4a7a5a" : "#4a7a5a";
    Plotly.react("live-chart", [{ x:bufTime, y:bufSpeed, name:"Speed (km/h)", mode:"lines", type:"scatter", line:{color:"#00d4aa",width:2.5,shape:"spline",smoothing:1.3}, fill:"tozeroy", fillcolor:"rgba(0,212,170,0.10)" }, { x:bufTime, y:rpmScaled, name:"RPM ÷ 36", mode:"lines", type:"scatter", line:{color:"#4ade80",width:1.5,dash:"dot",shape:"spline",smoothing:1.3} }], { margin:{t:10,b:36,l:46,r:16}, paper_bgcolor:"transparent", plot_bgcolor:"transparent", font:{color:fontColor,size:11}, legend:{orientation:"h",x:0,y:-0.28,font:{size:11}}, xaxis:{title:"Time",gridcolor:gridColor,zeroline:false,tickfont:{size:9}}, yaxis:{title:"Speed / RPM÷36",gridcolor:gridColor,zeroline:false} }, { responsive:true, displayModeBar:false });
}

// ══════════════════════════════════════════════════
// PROGRAMMING PAGE — UDS Programming Session
// ══════════════════════════════════════════════════
const progFlashState = { running: false, cancelled: false, fileRead: false, fileSelected: false, fileVerified: false, startTime: null, timerHandle: null, lastBatteryV: 13.8, lastConnOk: true };

function progLog(msg, level) {
    const win = document.getElementById("prog-log-window"); if (!win) return;
    const ts = new Date().toLocaleTimeString("en-IN", { hour12:false });
    const line = document.createElement("div"); line.className = "prog-log-line" + (level ? " " + level : ""); line.textContent = `[${ts}] ${msg}`;
    win.appendChild(line); win.scrollTop = win.scrollHeight;
    while (win.children.length > 60) win.removeChild(win.firstChild);
}

function progSetStatus(state, label) {
    const chip = document.getElementById("prog-status-chip"); if (!chip) return;
    chip.className = "prog-status-chip " + state; chip.textContent = label; chip.style.display = 'inline-flex';
}

function progSetButtonsDuringFlash(running) {
    ["prog-btn-read","prog-btn-select","prog-btn-verify","prog-btn-write"].forEach(id => { const el = document.getElementById(id); if (el) el.disabled = running; });
    const cancelBtn = document.getElementById("prog-btn-cancel"); if (cancelBtn) cancelBtn.disabled = !running;
}

function progReadEcu() {
    if (progFlashState.running) return;
    progLog("Reading ECU... requesting Original File (Read) via UDS UploadFile.");
    setText("prog-orig-file", "Reading…");
    setTimeout(() => { progFlashState.fileRead = true; setText("prog-orig-file", "EDC17C46_Original.bin"); progLog("Original ECU file read and stored as backup: EDC17C46_Original.bin", "ok"); }, 900);
}

function progSelectFile() {
    if (progFlashState.running) return;
    if (!progFlashState.fileRead) { progLog("Select a Modified File requires Read ECU first (need a backup before writing).", "warn"); }
    progFlashState.fileSelected = true; progFlashState.fileVerified = false;
    setText("prog-mod-file", "EDC17C46_Stage2.bin"); setText("prog-checksum", "CRC32: A1B2C3D4 (unverified)"); setText("prog-filesize", "2.4 MB");
    const checksumEl = document.getElementById("prog-checksum"); if (checksumEl) checksumEl.classList.remove("valid","invalid");
    progLog("Modified File selected: EDC17C46_Stage2.bin (2.4 MB). Run Verify File before flashing.", "warn");
}

function progVerifyFile() {
    if (progFlashState.running) return;
    if (!progFlashState.fileSelected) { progLog("No Modified File selected yet — use Select Tune first.", "err"); return; }
    progLog("Verifying checksum and compatibility list against ECU identification...");
    setTimeout(() => {
        progFlashState.fileVerified = true; setText("prog-checksum", "CRC32: A1B2C3D4 (Valid)");
        const checksumEl = document.getElementById("prog-checksum"); if (checksumEl) { checksumEl.classList.add("valid"); checksumEl.classList.remove("invalid"); }
        progLog("Checksum valid. File matches Compatibility List: VW Golf MK7 2.0 TDI (2015–2020).", "ok");
    }, 700);
}

const PROG_STEPS = [
    { pct: 10, op: "Checking voltage stability and connection...", minMs: 600 }, { pct: 30, op: "Erasing Flash Memory...", minMs: 1200 },
    { pct: 65, op: "Writing Sector 0x4567...", minMs: 1600 }, { pct: 90, op: "Verifying...", minMs: 1000 }, { pct: 100, op: "Flash Successful!", minMs: 500 }
];

function progStartFlash() {
    if (progFlashState.running) return;
    if (!progFlashState.fileRead) { progLog("Start Flashing blocked — Read ECU (backup) has not been performed.", "err"); return; }
    if (!progFlashState.fileVerified) { progLog("Start Flashing blocked — Modified File has not passed Verify File.", "err"); return; }
    if (progFlashState.lastBatteryV < 12.5) { progLog(`Start Flashing blocked — Voltage Stability ${progFlashState.lastBatteryV.toFixed(1)}V is below the 12.5V safe threshold.`, "err"); return; }

    progFlashState.running = true; progFlashState.cancelled = false; progFlashState.startTime = Date.now();
    progSetButtonsDuringFlash(true); progSetStatus("running", "FLASHING");
    progLog("Write ECU confirmed — checksum and compatibility OK. Beginning flash sequence.", "ok");
    const bar = document.getElementById("prog-bar-fill"); if (bar) { bar.classList.remove("done","error"); }
    progRunStep(0); progFlashState.timerHandle = setInterval(progTickElapsed, 1000);
}

function progRunStep(i) {
    if (progFlashState.cancelled) return;
    if (i >= PROG_STEPS.length) { progFinishFlash(true); return; }
    const step = PROG_STEPS[i];
    setText("prog-current-op", step.op); setText("prog-percent", step.pct + "%");
    const bar = document.getElementById("prog-bar-fill"); if (bar) bar.style.width = step.pct + "%";
    if (!progFlashState.lastConnOk) { progLog(`Connection Status dropped to Unstable mid-write at "${step.op}" — aborting to prevent a bricked ECU.`, "err"); progFinishFlash(false); return; }
    progLog(step.op, step.pct === 100 ? "ok" : undefined);
    const remainingSteps = PROG_STEPS.length - 1 - i;
    setText("prog-remaining", remainingSteps > 0 ? `00:00:${String(remainingSteps * 1).padStart(2,"0")}` : "00:00:00");
    setTimeout(() => progRunStep(i + 1), step.minMs);
}

function progTickElapsed() {
    if (!progFlashState.startTime) return;
    const secs = Math.floor((Date.now() - progFlashState.startTime) / 1000);
    const h = String(Math.floor(secs/3600)).padStart(2,"0"), m = String(Math.floor((secs%3600)/60)).padStart(2,"0"), s = String(secs%60).padStart(2,"0");
    setText("prog-elapsed", `${h}:${m}:${s}`);
}

function progFinishFlash(success) {
    progFlashState.running = false; if (progFlashState.timerHandle) { clearInterval(progFlashState.timerHandle); progFlashState.timerHandle = null; }
    progSetButtonsDuringFlash(false); const bar = document.getElementById("prog-bar-fill");
    if (success) {
        if (bar) bar.classList.add("done");
        setText("prog-current-op", "Flash Successful!"); setText("prog-percent", "100%"); setText("prog-remaining", "00:00:00");
        progSetStatus("success", "SUCCESS"); setText("prog-sw-ver", "1037376200 (Stage2)");
        progLog("Flash complete. Software version updated. Reconnect and verify — no DTCs, confirm increased power on test drive.", "ok");
    } else {
        if (bar) bar.classList.add("error");
        setText("prog-current-op", "Error: Write Timeout (0x1234)");
        progSetStatus("error", "ERROR");
        progLog("Flash aborted. ECU state unknown — do NOT disconnect. Attempt Recovery Mode before retrying.", "err");
    }
}

function progCancelFlash() {
    if (!progFlashState.running) return;
    progFlashState.cancelled = true;
    progLog("User requested cancel. Waiting for safe abort point...", "warn");
    setTimeout(() => progFinishFlash(false), 400);
}

const SIGNAL_MAP = {
    speed: { label:"Speed (km/h)", key:"speed", color:"#00d4aa" }, rpm: { label:"Engine RPM", key:"rpm", color:"#4ade80" },
    coolant: { label:"Coolant Temp (°C)", key:"coolant", color:"#f87171" }, oil_temp: { label:"Oil Temp (°C)", key:"oil_temp", color:"#fb923c" },
    fuel_pct: { label:"Fuel Level (%)", key:"fuel_pct", color:"#34d399" }, fuel_rate: { label:"Fuel Rate (mL/s)", key:"fuel_rate", color:"#60a5fa" },
    throttle: { label:"Throttle (%)", key:"throttle", color:"#fbbf24" }, engine_load: { label:"Engine Load (%)", key:"engine_load", color:"#a78bfa" },
    accel: { label:"Acceleration (m/s²)", key:"accel", color:"#2dd4bf" }, battery: { label:"Battery Voltage (V)", key:"battery", color:"#facc15" },
    gear_num: { label:"Gear Number", key:"gear_num", color:"#00d4aa" }
};
const FILL_MAP = { "#00d4aa":"rgba(0,212,170,0.08)", "#4ade80":"rgba(74,222,128,0.08)", "#f87171":"rgba(248,113,113,0.08)", "#fb923c":"rgba(251,146,60,0.08)", "#34d399":"rgba(52,211,153,0.08)", "#60a5fa":"rgba(96,165,250,0.08)", "#fbbf24":"rgba(251,191,36,0.08)", "#a78bfa":"rgba(167,139,250,0.08)", "#2dd4bf":"rgba(45,212,191,0.08)", "#facc15":"rgba(250,204,21,0.08)" };

async function loadHistory() {
    if (currentMode !== "history") return;
    try {
        const res  = await fetch("/history");
        const data = await res.json();
        if (data.error) { setStatus(false, data.error); return; }
        renderHistoryChart(data); renderTable(data);
        const sig  = document.getElementById("signal-select").value, range = document.getElementById("range-select").value, meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed, all = data[meta.key] || [], n = range==="all" ? all.length : Math.min(all.length, parseInt(range,10)), slice = all.slice(Math.max(0,all.length-n));
        if (slice.length) { setText("hs-min", Math.min(...slice).toFixed(1)); setText("hs-max", Math.max(...slice).toFixed(1)); setText("hs-avg", (slice.reduce((a,b)=>a+b,0)/slice.length).toFixed(1)); setText("hs-cur", slice[slice.length-1].toFixed(1)); setText("hs-count", slice.length); }
    } catch(e) { setStatus(false, "Connection error"); }
}

function getSlice(arr, rangeVal) {
    if (!arr||!arr.length) return [];
    if (rangeVal==="all") return arr;
    const n = parseInt(rangeVal, 10); return arr.slice(Math.max(0, arr.length-n));
}

function renderHistoryChart(data) {
    const sig = document.getElementById("signal-select").value, range = document.getElementById("range-select").value, meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed, isDark = document.documentElement.getAttribute("data-theme") !== "light", gridColor = isDark ? "#111828" : "#dde5f0", fontColor = isDark ? "#4a5568" : "#6a7890", x = getSlice(data.time||[], range), y = getSlice(data[meta.key]||[], range), isStep = sig === "gear_num";
    Plotly.react("history-chart", [{ x, y, mode:"lines", type:"scatter", name:meta.label, line:{color:meta.color, width:2, shape:isStep?"hv":"spline", smoothing:isStep?0:1.2}, fill:"tozeroy", fillcolor:FILL_MAP[meta.color]||"rgba(0,212,170,0.08)" }], { title:{text:meta.label, font:{color:isDark?"#e0e8f0":"#0d1126",size:14}}, margin:{t:46,b:50,l:60,r:24}, paper_bgcolor:"transparent", plot_bgcolor:"transparent", font:{color:fontColor,size:11}, xaxis:{title:"Time",gridcolor:gridColor,zeroline:false,tickfont:{size:9},nticks:10,tickangle:-30}, yaxis:{title:meta.label,gridcolor:gridColor,zeroline:false} }, { responsive:true, displayModeBar:false });
}

function renderTable(data) {
    const range = document.getElementById("range-select").value, tbody = document.getElementById("table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    const all = data.time || [], n = range==="all" ? all.length : Math.min(all.length, parseInt(range,10)), start = all.length - n;
    for (let i = all.length-1; i >= start; i--) {
        const tr = document.createElement("tr"), gearVal = data.gear?.[i] ?? data.gear_num?.[i] ?? "--";
        tr.innerHTML = [ data.time?.[i]??"--", gearVal, data.speed?.[i]??"--", data.rpm?.[i]??"--", data.coolant?.[i]??"--", data.oil_temp?.[i]??"--", data.fuel_pct?.[i]??"--", data.throttle?.[i]??"--", data.engine_state?.[i]??"--" ].map(v=>`<td>${v}</td>`).join("");
        tbody.appendChild(tr);
    }
}

function connectSSE() {
    const src = new EventSource("/stream");
    src.onmessage = function(e) {
        try {
            const d = JSON.parse(e.data);
            updateLive(d); updateAdvanced(d); updateTechnician(d); checkAlerts(d); setStatus(true);
            
            // Send to programming tab too
            const bv = d.voltage || d.battery_v || 0;
            progFlashState.lastBatteryV = bv;
            const voltEl = document.getElementById("prog-voltage");
            if (voltEl) {
                voltEl.textContent = bv.toFixed(1) + " V";
                voltEl.className = "prog-meta-val" + (bv < 12.0 ? " err" : bv < 12.5 ? " warn" : " ok");
            }
            const connOk = !!d.time;
            progFlashState.lastConnOk = connOk;
            const connEl = document.getElementById("prog-conn");
            if (connEl) { connEl.textContent = connOk ? "Stable" : "Unstable"; connEl.className = "prog-meta-val" + (connOk ? " ok" : " err"); }
            
        } catch(err) {}
    };
    src.onerror = function() { setStatus(false, "Reconnecting…"); };
}

document.addEventListener("DOMContentLoaded", () => {
    startClock();
    connectSSE();
    setMode("live");
    document.getElementById("signal-select")?.addEventListener("change", () => { if (currentMode === "history") loadHistory(); });
    document.getElementById("range-select")?.addEventListener("change", () => { if (currentMode === "history") loadHistory(); });
});

setInterval(loadHistory, 3000);