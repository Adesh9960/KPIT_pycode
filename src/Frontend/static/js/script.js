// ═══════════════════════════════════════════════════════════════
// ECU Dashboard — script.js
// Socket.IO replaces SSE (matches new app.py with flask-socketio)
// UDS REST endpoints: /DID, /security_access, /diagnostics_session_control, /IO_control
// ═══════════════════════════════════════════════════════════════
"use strict";

// ── State ──
let currentMode = "live";
const LIVE_BUF = 80;
let bufTime = [],
  bufSpeed = [],
  bufRpm = [];
let advSparkBuf = { x: [], y: [] };
let techUnlocked = false;
let progUnlocked = false; // Programming session security granted
let currentSecurityLevel = 0;
let secAttemptsLeft = 3;
let secLockout = false;
let tpInterval = null; // TesterPresent (0x3E) heartbeat timer
let lastSpeed = 0; // used for pre-condition checks

// ── Theme ──
const savedTheme = localStorage.getItem("ecu-theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);

// ══════════════════════════════════════════════════
// UDS SESSION UNLOCK — Extended (0x03)
// User types the sequence: 0 x 1 0 0 x 0 3
// ══════════════════════════════════════════════════
const UDS_SEQUENCE = ["0", "x", "1", "0", "0", "x", "0", "3"];
let udsBuffer = [];

document.addEventListener("keydown", (e) => {
  if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(e.target.tagName))
    return;
  udsBuffer.push(e.key.toLowerCase());
  if (udsBuffer.length > UDS_SEQUENCE.length) udsBuffer.shift();
  if (udsBuffer.join("") === UDS_SEQUENCE.join("")) {
    udsBuffer = [];
    if (!techUnlocked) showUDSModal();
  }
  // Way B — Backdoor for Programming Session (only you know this)
  // Sequence: p r o g 1 2 3  (typed while in technician mode)
  checkBackdoor(e.key.toLowerCase());
});

// ── Way B: Programming backdoor buffer ──
const PROG_BACKDOOR = ["p", "r", "o", "g", "1", "2", "3"];
let progBuffer = [];
function checkBackdoor(key) {
  if (!techUnlocked) return; // Must be in Extended session first
  progBuffer.push(key);
  if (progBuffer.length > PROG_BACKDOOR.length) progBuffer.shift();
  if (progBuffer.join("") === PROG_BACKDOOR.join("")) {
    progBuffer = [];
    // Still enforce speed pre-condition
    if (lastSpeed > 0) {
      showToastMessage(
        "⚠ Pre-condition failed: vehicle must be stopped to enter Programming session.",
        false,
      );
      return;
    }
    enterProgrammingSessionBackdoor();
  }
}

// Backdoor clears after 3s of inactivity
let backdoorClearTimer = null;
document.addEventListener("keydown", () => {
  clearTimeout(backdoorClearTimer);
  backdoorClearTimer = setTimeout(() => {
    progBuffer = [];
  }, 3000);
});

function showUDSModal() {
  document.getElementById("uds-overlay").classList.add("visible");
}

function confirmTechUnlock() {
  techUnlocked = true;
  document.getElementById("uds-overlay").classList.remove("visible");
  const techBtn = document.getElementById("tech-tab-btn");
  if (techBtn) techBtn.classList.remove("hidden");
  const udsStatus = document.getElementById("uds-status");
  const udsLabel = document.getElementById("uds-label");
  if (udsStatus) udsStatus.classList.add("extended");
  if (udsLabel) udsLabel.textContent = "EXT 0x03";
  const hint = document.getElementById("adv-uds-hint");
  if (hint) hint.textContent = "✓ Technician mode unlocked";
  // Start TesterPresent heartbeat
  startTesterPresent();
  // Switch to technician tab
  setMode("technician");
  // Notify backend — session 3 = extended
  sendSessionControl(3);
}

function cancelTechUnlock() {
  document.getElementById("uds-overlay").classList.remove("visible");
}

function exitTechMode() {
  // If in programming, exit that first
  if (progUnlocked) exitProgrammingSession();
  techUnlocked = false;
  stopTesterPresent();
  const techBtn = document.getElementById("tech-tab-btn");
  if (techBtn) techBtn.classList.add("hidden");
  const udsStatus = document.getElementById("uds-status");
  const udsLabel = document.getElementById("uds-label");
  if (udsStatus) udsStatus.classList.remove("extended");
  if (udsLabel) udsLabel.textContent = "DEFAULT";
  const hint = document.getElementById("adv-uds-hint");
  if (hint)
    hint.textContent = "🔒 Technician mode locked — type 0x10 0x03 to unlock";
  // Notify backend — session 1 = default
  sendSessionControl(1);
  setMode("advanced");
}

// ══════════════════════════════════════════════════
// TESTER PRESENT (0x3E) — Heartbeat every 4s
// Must fire while in Extended or Programming session
// S3 timeout on ECU side is 5s — we send every 4s to stay safe
// Stopped immediately on session exit or page hide
// ══════════════════════════════════════════════════
// function startTesterPresent() {
//   if (tpInterval) return;
//   const tpIndicator = document.getElementById("tp-indicator");
//   if (tpIndicator) tpIndicator.classList.remove("hidden");
//   tpInterval = setInterval(() => {
//     sendTesterPresent();
//   }, 4000);
// }

function stopTesterPresent() {
  if (tpInterval) {
    clearInterval(tpInterval);
    tpInterval = null;
  }
  const tpIndicator = document.getElementById("tp-indicator");
  if (tpIndicator) tpIndicator.classList.add("hidden");
}

async function sendTesterPresent() {
  // Sends 0x3E 0x00 to backend (suppressPosRspMsgIndicationBit set)
  try {
    await fetch("/diagnostics_session_control/3", { method: "GET" });
    // Flash TP dot
    const dot = document.querySelector(".tp-dot");
    if (dot) {
      dot.classList.add("tp-flash");
      setTimeout(() => dot.classList.remove("tp-flash"), 200);
    }
  } catch (_) {
    /* silent — ECU will detect S3 timeout on its own */
  }
}

// Stop TesterPresent if tab is hidden (browser backgrounded)
document.addEventListener("visibilitychange", () => {
  if (document.hidden && techUnlocked) {
    showToastMessage(
      "⚠ Tab hidden — TesterPresent paused. Session may drop.",
      false,
    );
  }
});

// ══════════════════════════════════════════════════
// PROGRAMMING SESSION — see pgterm engine near EOF
// for the full terminal-driven implementation.
// (showProgPanel / exitProgrammingSession / requestSeed /
//  sendKey / updateProgControls all live there now.)
// ══════════════════════════════════════════════════
function updateSessionDisplay(label) {
  const el = document.getElementById("uds-label");
  if (el) el.textContent = label;
  const can = document.getElementById("can-session-display");
  if (can) can.textContent = label;
}

// ══════════════════════════════════════════════════
// UDS REST CALLS — matches new app.py endpoints
// ══════════════════════════════════════════════════

// GET /DID/<int:DID>  — ReadDataByIdentifier (0x22)
async function readDID(did, targetId, unit) {
  showUDSResponse(`Sending 0x22 ${hexStr(did)} ...`);
  try {
    const res = await fetch(`http://127.0.0.1:5000/DID/${did}`);
    const data = await res.json();
    if (data.status === "success") {

      const val = data.data[did] != null ? data.data[did] : "—";
      console.log(val)
      setText(targetId, val + (unit ? " " + unit : ""));
      showUDSResponse(
        `0x62 ${hexStr(did)} → ${val} ${unit}  [Positive Response]`,
      );
    } else {
      setText(targetId, "NRC");
      showUDSResponse(`0x7F 0x22 — ${data.message || "Request failed"}`);
    }
  } catch (e) {
    showUDSResponse(`Error: ${e.message}`);
  }
}

// POST /DID  — WriteDataByIdentifier (0x2E)
async function writeDID(did, value) {
  showUDSResponse(`Sending 0x2E ${hexStr(did)} ${value} ...`);
  try {
    const res = await fetch("/DID", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ DID: did, value: value }),
    });
    const data = await res.json();
    if (data.status === "success") {
      showUDSResponse(
        `0x6E ${hexStr(did)} — Write successful [Positive Response]`,
      );
    } else {
      showUDSResponse(`0x7F 0x2E — ${data.data || "Write failed"}`);
    }
  } catch (e) {
    showUDSResponse(`Error: ${e.message}`);
  }
}

// requestSeed() / sendKey() — superseded by the `security.seed` /
// `security.key <hex>` terminal commands in the pgterm engine.

// POST /IO_control — InputOutputControlByIdentifier (0x2F)
// control_parameter: 0=returnToECU, 1=shortTermAdjustment
async function ioControl(did, controlParam, controlState) {
  const stateNames = {
    F410: "io-headlamp-state",
    F411: "io-radfan-state",
    F412: "io-fuelpump-state",
  };
  const didHex = did.toString(16).toUpperCase();
  const stateId = stateNames[didHex];
  const label =
    controlParam === 0
      ? "ECU CONTROL"
      : controlState
        ? "FORCED ON"
        : "FORCED OFF";
  showUDSResponse(
    `Sending 0x2F ${hexStr(did)} ${controlParam} ${controlState} ...`,
  );
  try {
    const res = await fetch("/IO_control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        DID: did,
        control_parameter: controlParam,
        control_state: controlState,
      }),
    });
    const data = await res.json();
    if (data.status === "success") {
      if (stateId) setText(stateId, label);
      showUDSResponse(`0x6F ${hexStr(did)} — IO Control applied: ${label}`);
    } else {
      showUDSResponse(`0x7F 0x2F — ${data.message}`);
    }
  } catch (e) {
    showUDSResponse(`Error: ${e.message}`);
  }
}

// GET /diagnostics_session_control/<int:session>
async function sendSessionControl(session) {
  try {
    await fetch(`/diagnostics_session_control/${session}`);
  } catch (_) {}
}

// ECU Reset (0x11) — only in Programming session
async function ecuReset() {
  if (!progUnlocked) {
    showUDSResponse("0x7F 0x11 0x33 — Security access denied");
    return;
  }
  if (
    !confirm(
      "Hard reset will clear session, adaptations and restart signal generation. Continue?",
    )
  )
    return;
  showUDSResponse("Sending 0x11 0x01 — Hard Reset ...");
  try {
    // Reuse session control endpoint as proxy for reset signal
    const res = await fetch("/diagnostics_session_control/1");
    const data = await res.json();
    showUDSResponse(
      "0x51 0x01 — ECU Reset acknowledged. Returning to Default session.",
    );
    // Drop back to default
    exitProgrammingSession();
    exitTechMode();
  } catch (e) {
    showUDSResponse(`Error: ${e.message}`);
  }
}

async function clearDTCs() {
  if (!progUnlocked) {
    showUDSResponse("0x7F 0x14 0x33 — Security access denied");
    return;
  }
  showUDSResponse("Sending 0x14 0xFF 0xFF 0xFF — Clear all DTCs ...");
  // Placeholder — backend would handle actual DTC clearing
  setTimeout(() => {
    document.getElementById("tech-dtc-list").innerHTML =
      '<div class="tech-dtc-empty">No DTCs stored. All systems nominal.</div>';
    setText("dtc-count-badge", "No Active DTCs");
    document.getElementById("dtc-count-badge").className = "dtc-count-badge ok";
    showUDSResponse("0x54 — DTCs cleared successfully [Positive Response]");
  }, 600);
}

// ── Helper: show response in UDS response bar ──
function showUDSResponse(msg) {
  setText("uds-response-text", msg);
  const bar = document.getElementById("tech-uds-response");
  if (bar) {
    bar.classList.add("uds-resp-flash");
    setTimeout(() => bar.classList.remove("uds-resp-flash"), 400);
  }
}

function hexStr(val) {
  return "0x" + val.toString(16).toUpperCase().padStart(4, "0");
}

// ══════════════════════════════════════════════════
// THEME TOGGLE
// ══════════════════════════════════════════════════
function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("ecu-theme", next);
}

// ══════════════════════════════════════════════════
// MODE SWITCHING
// ══════════════════════════════════════════════════
function setMode(mode) {
  currentMode = mode;
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  document
    .querySelectorAll(".page")
    .forEach((p) => p.classList.remove("active"));
  const target = document.getElementById(mode + "-mode");
  if (target) {
    requestAnimationFrame(() => target.classList.add("active"));
  }
  document.body.classList.remove(
    "mode-live",
    "mode-advanced",
    "mode-technician",
    "mode-history",
    "mode-programming",
  );
  document.body.classList.add("mode-" + mode);
  if (mode === "history") loadHistory();
  if (mode === "programming") pgtermFocusInput();
}

// ══════════════════════════════════════════════════
// STATUS HELPERS
// ══════════════════════════════════════════════════
function setStatus(ok, msg) {
  const pill = document.getElementById("connection-status");
  const upd = document.getElementById("last-update");
  const dot = document.getElementById("conn-dot");
  const label = document.getElementById("conn-label");
  if (ok) {
    if (pill) {
      pill.textContent = "● LIVE";
      pill.className = "status-pill ok";
    }
    if (upd) upd.textContent = new Date().toLocaleTimeString();
    if (dot) dot.classList.add("live");
    if (label) label.textContent = "LIVE";
  } else {
    if (pill) {
      pill.textContent = "● " + (msg || "Disconnected");
      pill.className = "status-pill error";
    }
    if (dot) dot.classList.remove("live");
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
  setTimeout(() => {
    if (fill) {
      fill.style.transition = "width 6s linear";
      fill.style.width = "0%";
    }
  }, 50);
  setTimeout(() => {
    toast.classList.add("closing");
    setTimeout(() => toast.remove(), 220);
  }, 6000);
}

// ══════════════════════════════════════════════════
// CLOCK & DATE
// ══════════════════════════════════════════════════
function startClock() {
  const timeEl = document.getElementById("sys-time");
  const liveDateEl = document.getElementById("live-date-display");
  const advDateEl = document.getElementById("adv-date-display");

  setInterval(() => {
    const now = new Date();

    // Update Time (e.g., 16:40:21)
    if (timeEl) {
      timeEl.textContent = now.toLocaleTimeString("en-IN", { hour12: false });
    }

    // Update Date (e.g., 22 JUN 2026) - Formatted for a technical dashboard feel
    const dateStr = now
      .toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
      .toUpperCase();

    if (liveDateEl) liveDateEl.textContent = dateStr;
    if (advDateEl) advDateEl.textContent = dateStr;
  }, 1000);
}

// ══════════════════════════════════════════════════
// ALERT RULES
// ══════════════════════════════════════════════════
const ALERT_RULES = [
  {
    key: "coolant_high",
    critical: true,
    targets: ["coolantTemp", "sn-cool", "adv-cool-mini"],
    test: (d) => (d.coolant || d.coolant_temp || 0) > 110,
    message: (d) =>
      `Coolant ${(d.coolant || d.coolant_temp || 0).toFixed(1)}°C — engine overheating.`,
  },
  {
    key: "oil_temp_high",
    critical: true,
    targets: ["oil-val", "sn-oil", "adv-oiltemp-kpi"],
    test: (d) => (d.oil_temp || 0) > 130,
    message: (d) =>
      `Oil temp ${(d.oil_temp || 0).toFixed(1)}°C — above safe range.`,
  },
  {
    key: "voltage_low",
    critical: false,
    targets: ["batteryVoltage", "sn-volt"],
    test: (d) => (d.voltage || d.battery_v || 0) < 12.0,
    message: (d) =>
      `Battery voltage low (${(d.voltage || d.battery_v || 0).toFixed(2)} V).`,
  },
  {
    key: "fuel_low",
    critical: false,
    targets: ["fuelLevel", "sn-fuel", "adv-fuel-mini"],
    test: (d) => (d.fuel || d.fuel_pct || 0) < 10,
    message: (d) =>
      `Low fuel — ${(d.fuel || d.fuel_pct || 0).toFixed(1)}% remaining.`,
  },
  {
    key: "stall_risk",
    critical: true,
    targets: ["adv-stall-badge"],
    test: (d) => !!d.stall_risk,
    message: () =>
      `Stall risk — low RPM at low speed. Press clutch or shift down.`,
  },
  {
    key: "rev_limiter",
    critical: false,
    targets: ["revlim-val", "adv-revlim-badge"],
    test: (d) => !!d.rev_limiter,
    message: () => `Rev limiter engaged — back off the throttle.`,
  },
  {
    key: "tyre_fl",
    critical: false,
    targets: ["t-fl"],
    test: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return t.fl != null && (t.fl < 26 || t.fl > 38);
    },
    message: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return `Front-left tyre ${t.fl?.toFixed(1)} psi.`;
    },
  },
  {
    key: "tyre_fr",
    critical: false,
    targets: ["t-fr"],
    test: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return t.fr != null && (t.fr < 26 || t.fr > 38);
    },
    message: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return `Front-right tyre ${t.fr?.toFixed(1)} psi.`;
    },
  },
  {
    key: "tyre_rl",
    critical: false,
    targets: ["t-rl"],
    test: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return t.rl != null && (t.rl < 26 || t.rl > 38);
    },
    message: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return `Rear-left tyre ${t.rl?.toFixed(1)} psi.`;
    },
  },
  {
    key: "tyre_rr",
    critical: false,
    targets: ["t-rr"],
    test: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return t.rr != null && (t.rr > 38 || t.rr < 26);
    },
    message: (d) => {
      const t = d.tyres || d.tyre_pressure || {};
      return `Rear-right tyre ${t.rr?.toFixed(1)} psi.`;
    },
  },
];

const activeAlerts = {};

function applyHighlight(targets, critical) {
  targets.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("param-warn", "param-crit");
    el.classList.add(critical ? "param-crit" : "param-warn");
  });
}
function clearHighlight(targets) {
  targets.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("param-warn", "param-crit");
  });
}
function spawnToast(rule, msg) {
  const stack = document.getElementById("alert-toast-stack");
  if (!stack) return null;
  const toast = document.createElement("div");
  toast.className = "alert-toast" + (rule.critical ? " crit" : "");
  toast.innerHTML = `
        <div class="alert-toast-head">${rule.critical ? "🔴 CRITICAL" : "⚠️ WARNING"}</div>
        <div class="alert-toast-body">${msg}</div>
        ${
          rule.critical
            ? `<button class="alert-toast-ack" onclick="dismissToast('${rule.key}',false)">✓ Acknowledge</button>`
            : `<div class="alert-toast-bar"><div class="alert-toast-bar-fill"></div></div>`
        }
    `;
  stack.appendChild(toast);
  if (!rule.critical) {
    const fill = toast.querySelector(".alert-toast-bar-fill");
    setTimeout(() => {
      if (fill) {
        fill.style.transition = "width 10s linear";
        fill.style.width = "0%";
      }
    }, 50);
    const timer = setTimeout(() => dismissToast(rule.key, false), 10000);
    if (activeAlerts[rule.key]) activeAlerts[rule.key].autoTimer = timer;
  }
  return toast;
}
function dismissToast(key, deleteEntry = true) {
  const entry = activeAlerts[key];
  if (!entry || !entry.toastEl) return;
  if (entry.autoTimer) {
    clearTimeout(entry.autoTimer);
    entry.autoTimer = null;
  }
  const el = entry.toastEl;
  el.classList.add("closing");
  setTimeout(() => {
    if (el.parentNode) el.remove();
  }, 220);
  entry.toastEl = null;
  if (deleteEntry) delete activeAlerts[key];
}
function checkAlerts(d) {
  ALERT_RULES.forEach((rule) => {
    let triggered = false;
    try {
      triggered = !!rule.test(d);
    } catch (_) {
      triggered = false;
    }
    if (triggered) {
      applyHighlight(rule.targets, rule.critical);
      if (!activeAlerts[rule.key]) {
        activeAlerts[rule.key] = {
          critical: rule.critical,
          toastEl: null,
          autoTimer: null,
        };
        activeAlerts[rule.key].toastEl = spawnToast(rule, rule.message(d));
      }
    } else {
      if (activeAlerts[rule.key]) {
        clearHighlight(rule.targets);
        dismissToast(rule.key, true);
      }
    }
  });
}

// ══════════════════════════════════════════════════
// LIVE PAGE UPDATE
// ══════════════════════════════════════════════════
function updateLive(d) {
  lastSpeed = d.speed || 0;
  if (d.date) setText("live-date-display", d.date);

  const badge = document.getElementById("engine-state-badge");
  if (badge) {
    badge.textContent = d.engine_state || "IDLE";
    badge.className =
      "state-badge" +
      (["BRAKING", "STALLED", "DEAD", "OVERHEATING"].includes(d.engine_state)
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
  setText("gear-name", d.gear || "Neutral");
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
  const clutchState = d.clutch_state || d.clutch || "UP";
  if (clutchVal) clutchVal.textContent = clutchState;
  if (clutchEl) clutchEl.classList.toggle("active", clutchState === "DOWN");

  const brakeEl = document.getElementById("chip-brake");
  const brakeVal = document.getElementById("brake-val");
  const brakeState = d.brake_state || d.brake || "OFF";
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
  document
    .getElementById("chip-lowbeam")
    .classList.toggle("active", !!d.head_lamp);
  document
    .getElementById("chip-highbeam")
    .classList.toggle("active", !!d.high_beam);

  // Indicators — assumes d.indicator_state is "LEFT" | "RIGHT" | "HAZARD" | "OFF"
  const leftEl = document.getElementById("ind-left");
  const rightEl = document.getElementById("ind-right");
  const hazardEl = document.getElementById("ind-hazard");
  leftEl.classList.toggle("active", d.indicator_state === "LEFT");
  rightEl.classList.toggle("active", d.indicator_state === "RIGHT");
  hazardEl.classList.toggle("active", d.indicator_state === "HAZARD");

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
    battBar.style.width = Math.min(100, ((bv - 11) / 4) * 100).toFixed(0) + "%";
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

  bufTime.push(d.time);
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
function updatePreConditions(speed) {
  const isStopped = speed === 0;

  // Update Programming panel pre-condition UI
  const progPcSpeed = document.getElementById("prog-pc-speed");
  if (progPcSpeed) {
    const dot = progPcSpeed.querySelector(".prog-pc-dot");
    if (dot)
      dot.className = isStopped
        ? "prog-pc-dot prog-ok"
        : "prog-pc-dot prog-bad";
    const val = progPcSpeed.querySelector("#prog-speed-val");
    if (val) val.textContent = speed + " km/h";
  }
  // Pre-condition gating (vehicle must be stopped) is enforced inside
  // the pgterm engine's `security.seed` command — see lastSpeed usage there.
}

// ══════════════════════════════════════════════════
// ADVANCED PAGE UPDATE
// ══════════════════════════════════════════════════
function updateAdvanced(d) {
  const tyres = d.tyres || d.tyre_pressure || {};
  const bv = d.voltage || d.battery_v || 0;
  const bsoc = Math.max(0, Math.min(100, ((bv - 11.8) / (14.4 - 11.8)) * 100));
  const fuel = d.fuel || d.fuel_pct || 0;
  const cool = d.coolant || d.coolant_temp || 0;
  const ot = d.oil_temp || 0;
  const fr = d.fuel_rate || 0;
  const sp = d.speed || 0;
  const fuelL = d.remaining_fuel_l || d.fuel_l || 0;

  setText("adv-rpm-hero", (d.rpm || 0).toLocaleString());
  setText("adv-load-hero", (d.engine_load || 0).toFixed(1) + "%");
  setText("adv-iat-hero", (d.ambient_temp || 0).toFixed(1) + "°C");
  setText("adv-throttle-hero", (d.throttle_pct || 0).toFixed(1) + "%");

  setText("adv-engine-state-chip", d.engine_state || "IDLE");
  setText("adv-gear-chip", (d.gear_num || 0) === 0 ? "N" : String(d.gear_num));
  setText("adv-brake-chip", "BRAKE: " + (d.brake_state || d.brake || "OFF"));
  setText("adv-clutch-chip", "CLUTCH: " + (d.clutch_state || d.clutch || "UP"));

  setText("adv-speed-big", sp + " km/h");
  setText("adv-accel-mini", (d.accel_ms2 || d.accel || 0).toFixed(2));
  setText("adv-dist-mini", (d.distance_km || 0).toFixed(2));
  setText("adv-fuel-mini", fuel.toFixed(1));
  setText("adv-cool-mini", cool.toFixed(1));

  setText("sn-fuel", fuel.toFixed(1) + "%");
  setText("sn-oil", ot.toFixed(1) + "°C");
  setText("sn-cool", cool.toFixed(1) + "°C");
  setText("sn-volt", bv.toFixed(2) + " V");
  setText("sn-rpm", (d.rpm || 0).toLocaleString());
  setText("sn-fuelrate", fr.toFixed(2) + " mL/s");
  setText("sn-dist", (d.distance_km || 0).toFixed(3) + " km");
  // New actuator sensors
  setText(
    "sn-headlamp",
    d.head_lamp != null ? (d.head_lamp ? "ON" : "OFF") : "—",
  );
  setText(
    "sn-radfan",
    d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "—",
  );

  if (d.date) setText("adv-date-display", d.date);

  // KPIs
  setText("adv-batt", bsoc.toFixed(1) + "%");
  setText(
    "adv-batt-sub",
    bv.toFixed(2) + " V · " + (bv > 13.5 ? "Charging" : "Draining"),
  );
  const battBar = document.getElementById("adv-batt-bar");
  if (battBar) {
    battBar.style.width = bsoc.toFixed(1) + "%";
    battBar.style.background =
      bsoc > 50 ? "#10b981" : bsoc > 25 ? "#f59e0b" : "#ef4444";
  }
  setText("adv-alt", bv.toFixed(2) + " V");
  setText(
    "adv-alt-sub",
    bv > 13.5 ? "Alternator charging" : "Running on battery",
  );
  const altBar = document.getElementById("adv-alt-bar");
  if (altBar)
    altBar.style.width = Math.min(100, ((bv - 11) / 4) * 100).toFixed(0) + "%";
  setText("adv-oiltemp-kpi", ot.toFixed(1) + " °C");
  const otBar = document.getElementById("adv-oiltemp-bar");
  if (otBar) {
    otBar.style.width = Math.min(100, ((ot - 40) / 80) * 100).toFixed(0) + "%";
    otBar.style.background = ot > 110 ? "#ef4444" : "#f59e0b";
  }
  setText("adv-fuelrate-kpi", fr.toFixed(2) + " mL/s");
  const frBar = document.getElementById("adv-fuelrate-bar");
  if (frBar) {
    frBar.style.width = Math.min(100, (fr / 12) * 100).toFixed(0) + "%";
    frBar.style.background = fr > 8 ? "#ef4444" : "#f59e0b";
  }
  const estKm =
    fr > 0.01 && sp > 0 ? Math.round(((fuelL * 1000) / fr / 3600) * sp) : 0;
  setText("adv-range-kpi", estKm > 0 ? estKm + " km" : "—");
  const rngBar = document.getElementById("adv-range-bar");
  if (rngBar)
    rngBar.style.width = Math.min(100, (estKm / 400) * 100).toFixed(0) + "%";

  if (tyres.fl != null) {
    setTyre("t-fl", "t-fl-bar", tyres.fl);
    setTyre("t-fr", "t-fr-bar", tyres.fr);
    setTyre("t-rl", "t-rl-bar", tyres.rl);
    setTyre("t-rr", "t-rr-bar", tyres.rr);
  }

  const rlBadge = document.getElementById("adv-revlim-badge");
  const rlDot = document.getElementById("adv-revlim-dot");
  if (d.rev_limiter) {
    if (rlBadge) {
      rlBadge.textContent = "ACTIVE";
      rlBadge.className = "adv-pill adv-pill-bad";
    }
    if (rlDot) rlDot.style.background = "#ef4444";
    setText("adv-revlim-sub", "Rev limiter triggered!");
  } else {
    if (rlBadge) {
      rlBadge.textContent = "STANDBY";
      rlBadge.className = "adv-pill adv-pill-warn";
    }
    if (rlDot) rlDot.style.background = "#f59e0b";
    setText("adv-revlim-sub", "Monitoring");
  }
  const stBadge = document.getElementById("adv-stall-badge");
  const stDot = document.getElementById("adv-stall-dot");
  if (d.stall_risk) {
    if (stBadge) {
      stBadge.textContent = "WARNING";
      stBadge.className = "adv-pill adv-pill-bad";
    }
    if (stDot) stDot.style.background = "#ef4444";
    setText("adv-stall-sub", "Low RPM + low speed");
  } else {
    if (stBadge) {
      stBadge.textContent = "OK";
      stBadge.className = "adv-pill adv-pill-ok";
    }
    if (stDot) stDot.style.background = "#10b981";
    setText("adv-stall-sub", "All clear");
  }

  advSparkBuf.x.push(d.time);
  advSparkBuf.y.push(sp);
  if (advSparkBuf.x.length > 60) {
    advSparkBuf.x.shift();
    advSparkBuf.y.shift();
  }
  if(document.getElementById("adv-speed-chart"))
  Plotly.react(
    "adv-speed-chart",
    [
      {
        x: advSparkBuf.x,
        y: advSparkBuf.y,
        mode: "lines",
        type: "scatter",
        line: { color: "#7c3aed", width: 2, shape: "spline" },
        fill: "tozeroy",
        fillcolor: "rgba(124,58,237,0.08)",
      },
    ],
    {
      margin: { t: 4, b: 4, l: 4, r: 4 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      xaxis: { visible: false },
      yaxis: { visible: false },
      showlegend: false,
    },
    { responsive: true, displayModeBar: false },
  );
}

function setTyre(valId, barId, psi) {
  const el = document.getElementById(valId);
  const barEl = document.getElementById(barId);
  if (psi == null) return;
  const color = psi < 26 ? "#ef4444" : psi < 29 ? "#f59e0b" : "#10b981";
  if (el) {
    el.innerHTML = psi.toFixed(1) + ' <span class="adv-tyre-unit">psi</span>';
    el.style.color = color;
  }
  if (barEl) {
    barEl.style.width = Math.min(100, (psi / 36) * 100).toFixed(0) + "%";
    barEl.style.background = color;
  }
}

// ══════════════════════════════════════════════════
// TECHNICIAN PAGE UPDATE
// ══════════════════════════════════════════════════
function updateTechnician(d) {
  if (!techUnlocked) return;
  const tyres = d.tyres || d.tyre_pressure || {};
  const bv = d.voltage || d.battery_v || 0;
  const bsoc = Math.max(0, Math.min(100, ((bv - 11.8) / (14.4 - 11.8)) * 100));

  // ECM
  setText("tech-rpm", (d.rpm || 0).toLocaleString() + " RPM");
  setText("tech-load", (d.engine_load || 0).toFixed(1) + "%");
  setText("tech-throttle", (d.throttle_pct || 0).toFixed(1) + "%");
  setText("tech-coolant", (d.coolant || d.coolant_temp || 0).toFixed(1) + "°C");
  setText("tech-oiltemp", (d.oil_temp || 0).toFixed(1) + "°C");
  setText("tech-fuelrate", (d.fuel_rate || 0).toFixed(2) + " mL/s");
  setText("tech-accel", (d.accel_ms2 || d.accel || 0).toFixed(2) + " m/s²");
  setText("tech-stall", d.stall_risk ? "⚠ YES" : "NO");
  // New: engine_state in ECM card
  setText("tech-engstate", d.engine_state || "IDLE");

  // TCM
  setText("tech-gear", d.gear || "Neutral");
  setText("tech-gearnum", (d.gear_num || 0) === 0 ? "N" : String(d.gear_num));
  setText("tech-clutch", d.clutch_state || d.clutch || "UP");
  setText("tech-brake", d.brake_state || d.brake || "OFF");
  setText("tech-transtemp", (d.oil_temp || 0).toFixed(1) + "°C");

  // ABS
  setText("tech-speed", (d.speed || 0) + " km/h");
  const wsp = d.speed || 0;
  setText("tech-wfl", wsp + " km/h");
  setText("tech-wfr", wsp + " km/h");
  setText("tech-wrl", wsp + " km/h");
  setText("tech-wrr", wsp + " km/h");
  setText(
    "tech-brakepsi",
    (d.brake_state || d.brake) === "PRESSED" ? "12 bar" : "0 bar",
  );

  // BCM — now includes actuator states
  setText("tech-batt", bv.toFixed(2) + " V");
  setText("tech-soc", bsoc.toFixed(1) + "%");
  setText("tech-alt", bv > 13.5 ? "CHARGING" : "IDLE");
  setText(
    "tech-headlamp",
    d.head_lamp != null ? (d.head_lamp ? "ON" : "OFF") : "—",
  );
  setText(
    "tech-radfan",
    d.radiator_fan != null ? (d.radiator_fan ? "ON" : "OFF") : "—",
  );
  setText(
    "tech-fuelpump",
    d.fuel_pump != null ? (d.fuel_pump ? "ON" : "OFF") : "—",
  );
  if (tyres.fl != null) {
    setText("tech-tfl", tyres.fl.toFixed(1) + " psi");
    setText("tech-tfr", tyres.fr.toFixed(1) + " psi");
    setText("tech-trl", tyres.rl.toFixed(1) + " psi");
    setText("tech-trr", tyres.rr.toFixed(1) + " psi");
  }

  // CAN bus stats
  const msgRate = 40 + Math.floor(Math.random() * 20);
  const busLoad = Math.round((msgRate / 200) * 100);
  setText("tech-can-load", busLoad + "%");
  setText("tech-can-msgrate", msgRate + " msg/s");
  setText("tech-can-errrate", "0 err/s");
  setText("tech-can-latency", (Math.random() * 5 + 1).toFixed(1) + " ms");

  addSnifferRow(d);
}

const snifferCanIds = ["0x7E0", "0x7E1", "0x7E2", "0x7E3", "0x200", "0x100"];
const snifferSigs = [
  "Engine_RPM",
  "Gear",
  "Wheel_Speed",
  "Battery_V",
  "Speed_kmh",
  "Throttle_Pct",
];
let snifferRowCount = 0;

function addSnifferRow(d) {
  const body = document.getElementById("tech-sniffer-body");
  if (!body) return;
  snifferRowCount++;
  const idx = snifferRowCount % snifferCanIds.length;
  const values = [
    d.rpm || 0,
    d.gear_num || 0,
    d.speed || 0,
    d.voltage || 0,
    d.speed || 0,
    d.throttle_pct || 0,
  ];
  const hexVal = Math.round(values[idx])
    .toString(16)
    .toUpperCase()
    .padStart(4, "0");
  const hexData = `0x${hexVal.slice(0, 2)} 0x${hexVal.slice(2, 4)}`;
  const row = document.createElement("div");
  row.className = "tech-sniffer-row";
  row.innerHTML = `
        <span class="tech-sr-time">${d.time || "--"}</span>
        <span class="tech-sr-id">${snifferCanIds[idx]}</span>
        <span class="tech-sr-data">${hexData}</span>
        <span class="tech-sr-sig">${snifferSigs[idx]}</span>
        <span class="tech-sr-val">${values[idx].toFixed ? values[idx].toFixed(1) : values[idx]}</span>
    `;
  body.insertBefore(row, body.firstChild);
  while (body.children.length > 30) body.removeChild(body.lastChild);
}

// ══════════════════════════════════════════════════
// PLOTLY GAUGE
// ══════════════════════════════════════════════════
function updateGauge(id, value, min, max, suffix, barColor, bgInner) {
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
          font: { color: numColor, size: 22, family: "Inter,Segoe UI" },
        },
        gauge: {
          axis: {
            range: [min, max],
            tickcolor: isDark ? "#1e3a28" : "#aac8b8",
            tickfont: { size: 9, color: isDark ? "#4a7a5a" : "#5a8a6a" },
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
              color: isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.2)",
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
function updateLiveChart() {
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
        line: { color: "#00d4aa", width: 2.5, shape: "spline", smoothing: 1.3 },
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
      yaxis: { title: "Speed / RPM÷36", gridcolor: gridColor, zeroline: false },
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
const SIGNAL_MAP = {
  speed: { label: "Speed (km/h)", key: "speed", color: "#00d4aa" },
  rpm: { label: "Engine RPM", key: "rpm", color: "#4ade80" },
  coolant: { label: "Coolant Temp (°C)", key: "coolant", color: "#f87171" },
  oil_temp: { label: "Oil Temp (°C)", key: "oil_temp", color: "#fb923c" },
  fuel_pct: { label: "Fuel Level (%)", key: "fuel_pct", color: "#34d399" },
  fuel_rate: { label: "Fuel Rate (mL/s)", key: "fuel_rate", color: "#60a5fa" },
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
const FILL_MAP = {
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

function progCancelFlash() {
  if (!progFlashState.running) return;
  progFlashState.cancelled = true;
  progLog("User requested cancel. Waiting for safe abort point...", "warn");
  setTimeout(() => progFinishFlash(false), 400);
}

async function loadHistory() {
  if (currentMode !== "history") return;
  try {
    const res = await fetch("/history-data");
    const data = await res.json();
    if (data.error) {
      setStatus(false, data.error);
      return;
    }
    renderHistoryChart(data);
    renderTable(data);
    const sig = document.getElementById("signal-select").value;
    const range = document.getElementById("range-select").value;
    const meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed;
    const all = data[meta.key] || [];
    const n =
      range === "all" ? all.length : Math.min(all.length, parseInt(range, 10));
    const slice = all.slice(Math.max(0, all.length - n));
    if (slice.length) {
      setText("hs-min", Math.min(...slice).toFixed(1));
      setText("hs-max", Math.max(...slice).toFixed(1));
      setText(
        "hs-avg",
        (slice.reduce((a, b) => a + b, 0) / slice.length).toFixed(1),
      );
      setText("hs-cur", slice[slice.length - 1].toFixed(1));
      setText("hs-count", slice.length);
    }
  } catch (e) {
    setStatus(false, "Connection error");
  }
}

function getSlice(arr, rangeVal) {
  if (!arr || !arr.length) return [];
  if (rangeVal === "all") return arr;
  const n = parseInt(rangeVal, 10);
  return arr.slice(Math.max(0, arr.length - n));
}

function renderHistoryChart(data) {
  const sig = document.getElementById("signal-select").value;
  const range = document.getElementById("range-select").value;
  const meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed;
  const isDark =
    document.documentElement.getAttribute("data-theme") !== "light";
  const gridColor = isDark ? "#111828" : "#dde5f0";
  const fontColor = isDark ? "#4a5568" : "#6a7890";
  const x = getSlice(data.time || [], range);
  const y = getSlice(data[meta.key] || [], range);
  const isStep = sig === "gear_num";
  Plotly.react(
    "history-chart",
    [
      {
        x,
        y,
        mode: "lines",
        type: "scatter",
        name: meta.label,
        line: {
          color: meta.color,
          width: 2,
          shape: isStep ? "hv" : "spline",
          smoothing: isStep ? 0 : 1.2,
        },
        fill: "tozeroy",
        fillcolor: FILL_MAP[meta.color] || "rgba(0,212,170,0.08)",
      },
    ],
    {
      title: {
        text: meta.label,
        font: { color: isDark ? "#e0e8f0" : "#0d1126", size: 14 },
      },
      margin: { t: 46, b: 50, l: 60, r: 24 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: fontColor, size: 11 },
      xaxis: {
        title: "Time",
        gridcolor: gridColor,
        zeroline: false,
        tickfont: { size: 9 },
        nticks: 10,
        tickangle: -30,
      },
      yaxis: { title: meta.label, gridcolor: gridColor, zeroline: false },
    },
    { responsive: true, displayModeBar: false },
  );
}

function renderTable(data) {
  const range = document.getElementById("range-select").value;
  const tbody = document.getElementById("table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  const all = data.time || [];
  const n =
    range === "all" ? all.length : Math.min(all.length, parseInt(range, 10));
  const start = all.length - n;
  for (let i = all.length - 1; i >= start; i--) {
    const tr = document.createElement("tr");
    const gearVal = data.gear?.[i] ?? data.gear_num?.[i] ?? "--";
    tr.innerHTML = [
      data.time?.[i] ?? "--",
      gearVal,
      data.speed?.[i] ?? "--",
      data.rpm?.[i] ?? "--",
      data.coolant?.[i] ?? "--",
      data.oil_temp?.[i] ?? "--",
      data.fuel_pct?.[i] ?? "--",
      data.throttle?.[i] ?? "--",
      data.engine_state?.[i] ?? "--",
    ]
      .map((v) => `<td>${v}</td>`)
      .join("");
    tbody.appendChild(tr);
  }
}

// ══════════════════════════════════════════════════
// POLLING
// ══════════════════════════════════════════════════

function pollLive() {
  fetch("http://127.0.0.1:5000/live-data")
    .then((res) => res.json())
    .then((data) => {
      updateLive(data);
      updateAdvanced(data);
      updateTechnician(data);
      checkAlerts(data);
      setStatus(true);
    })
    .catch((err) => {
      console.error("Error : ", err);
    });
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

let pgFlashPolling = false;

function pgPrint(text, cls) {
  const screen = document.getElementById("pgterm-screen");
  const promptRow = document.getElementById("pgterm-prompt-row");
  if (!screen || !promptRow) return;
  const line = document.createElement("div");
  line.className = "pgterm-line" + (cls ? " " + cls : "");
  line.textContent = text;
  screen.insertBefore(line, promptRow);
  screen.scrollTop = screen.scrollHeight;
}

function pgPrintRaw(html, cls) {
  const screen = document.getElementById("pgterm-screen");
  const promptRow = document.getElementById("pgterm-prompt-row");
  if (!screen || !promptRow) return;
  const line = document.createElement("div");
  line.className = "pgterm-line" + (cls ? " " + cls : "");
  line.innerHTML = html;
  screen.insertBefore(line, promptRow);
  screen.scrollTop = screen.scrollHeight;
}

function pgProgressLog(text, cls) {
  const log = document.getElementById("pg-progress-log");
  if (!log) return;
  const now = new Date().toLocaleTimeString("en-IN", { hour12: false });
  const line = document.createElement("div");
  line.className = "pg-log-line" + (cls ? " " + cls : "");
  line.textContent = "[" + now + "] " + text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function pgSetProgress(pct, status) {
  const fill = document.getElementById("pg-progress-fill");
  const stat = document.getElementById("pg-progress-status");
  const pctEl = document.getElementById("pg-progress-pct");
  if (fill) fill.style.width = pct + "%";
  if (stat) stat.textContent = status || "Idle — no operation in progress";
  if (pctEl) pctEl.textContent = pct + "%";
}

function pgEcho(cmd) {
  pgPrint(cmd, "l-cmd");
}

function pgtermFocusInput() {
  const input = document.getElementById("pgterm-input");
  if (input) setTimeout(() => input.focus(), 50);
}

function pgBar(pct) {
  const width = 24;
  const filled = Math.round((pct / 100) * width);
  return (
    "[" + "■".repeat(filled) + "□".repeat(width - filled) + "] " + pct + "%"
  );
}

// ── Boot banner, printed once on first entry ──
function pgBootBanner() {
  const boot = document.getElementById("pgterm-boot");
  if (!boot || boot.dataset.done === "1") return;
  boot.dataset.done = "1";
  const lines = [
    ["ECU PROGRAMMING INTERFACE  v2.1.0  (UDS ISO 14229-1)", "l-bold"],
    [
      "Target: Bosch EDC17C46  |  Link: CAN 500 kbps  |  Session: DEFAULT (0x01)",
      "l-dim",
    ],
    ["Type 'help' for the command list, or use the buttons below.", "l-dim"],
    ["", ""],
  ];
  boot.innerHTML = "";
  lines.forEach(([t, c]) => {
    const d = document.createElement("div");
    d.className = "pgterm-line" + (c ? " " + c : "");
    d.textContent = t;
    boot.appendChild(d);
  });
}

function showProgPanel() {
  const progBtn = document.getElementById("prog-tab-btn");
  if (progBtn) progBtn.classList.remove("hidden");
  setMode("programming");
  pgBootBanner();
}

// Way B — backdoor entry. Skips the seed/key exchange but still
// notifies the backend so /prog/* routes treat the session as unlocked.
async function enterProgrammingSessionBackdoor() {
  showProgPanel();
  pgPrint(
    "⚠ Alternate access path used — bypassing Security Access (0x27)",
    "l-amber",
  );
  try {
    const res = await fetch("/prog/security_access/1");
    const seedData = await res.json();
    const seedHex = seedData.message;
    const seedInt = parseInt(seedHex, 16);
    const keyHex = "0x" + (seedInt ^ 0x5aa5).toString(16).toUpperCase();
    await pgCmd_securityKey(keyHex);
  } catch (_) {
    pgPrint("Backdoor auth failed — backend unreachable.", "l-red");
  }
  showToastMessage("Programming session entered via alternate access.", false);
}

async function exitProgrammingSession() {
  progUnlocked = false;
  currentSecurityLevel = 0;
  try {
    await fetch("/prog/exit_session", { method: "POST" });
  } catch (_) {}
  updateSessionDisplay("EXT 0x03");
  sendSessionControl(3);
  pgRefreshStatusBar();
  const progBtn = document.getElementById("prog-tab-btn");
  if (progBtn) progBtn.classList.add("hidden");
  setMode("technician");
}

async function pgRefreshStatusBar() {
  try {
    const res = await fetch("/prog/state");
    const data = await res.json();
    if (data.status !== "success") return;
    const s = data.data;
    setText(
      "pg-stat-session",
      s.session === 2 ? "PROGRAMMING (0x02)" : "DEFAULT (0x01)",
    );
    const secEl = document.getElementById("pg-stat-security");
    if (secEl) {
      secEl.textContent = s.security.level >= 2 ? "UNLOCKED" : "LOCKED";
      secEl.className = s.security.level >= 2 ? "" : "warn";
    }
    const fileEl = document.getElementById("pg-stat-file");
    if (fileEl)
      fileEl.textContent = s.files.modified
        ? s.files.modified.name
        : s.files.original
          ? s.files.original.name + " (read only)"
          : "none";
    const flashEl = document.getElementById("pg-stat-flash");
    if (flashEl) {
      flashEl.textContent =
        s.flash.status +
        (s.flash.status !== "idle" && s.flash.status !== "success"
          ? ` ${s.flash.progress}%`
          : "");
      flashEl.className =
        s.flash.status === "error"
          ? "err"
          : s.flash.status === "success"
            ? ""
            : "warn";
    }
    setText("pg-stat-vbat", s.flash.voltage.toFixed(1) + "V");
  } catch (_) {}
}

// ── Command implementations ──
async function pgCmd_ecuId() {
  pgPrint(
    "Sending 0x22 — ReadDataByIdentifier (ECU Identification block)...",
    "l-dim",
  );
  const res = await fetch("/prog/ecu_info");
  const data = await res.json();
  const i = data.data;
  pgPrint(`ECU Part Number      : ${i.part_number}`);
  pgPrint(`Software Version     : ${i.software_version}`);
  pgPrint(`Hardware Version     : ${i.hardware_version}`);
  pgPrint(`VIN                  : ${i.vin}`);
  pgPrint(`Serial Number        : ${i.serial_number}`);
  pgPrint(`Manufacturer         : ${i.manufacturer}`);
  pgPrint(`Supported Protocols  : ${i.protocols}`);
  pgPrint(`Memory Type          : ${i.memory_type}`);
  pgPrint(`Bootloader Version   : ${i.bootloader_version}`, "l-bold");
}

async function pgCmd_securitySeed() {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

async function pgCmd_securityKey(levelStr) {
  if (!levelStr) {
    pgPrint("usage: security.key <level>   e.g. security.key 2", "l-dim");
    return;
  }
  const level = parseInt(levelStr, 10);
  if (![1, 2, 3].includes(level)) {
    pgPrint("usage error — level must be 1, 2, or 3", "l-red");
    return;
  }

  pgPrint(`Sending 0x27 — Security Access (level ${level}) seed+key handshake...`, "l-dim");
  let data;
  try {
    const res = await fetch(`/security_access/${level}`);
    data = await res.json();
  } catch (e) {
    pgPrint(`Error: ${e.message}`, "l-red");
    return;
  }

  if (data.status === "success") {
    currentSecurityLevel = level;
    progUnlocked = level >= 2;

    const overlay = document.getElementById("pg-editor-overlay");
    const editor = document.getElementById("pg-code-editor");
    const actions = document.getElementById("pg-editor-actions");
    const lockLabel = document.getElementById("pg-editor-lock");
    if (progUnlocked) {
      if (overlay) overlay.style.display = "none";
      if (editor) {
        editor.disabled = false;
        editor.focus();
      }
      if (actions) actions.style.display = "flex";
      if (lockLabel) lockLabel.textContent = "✓ UNLOCKED";
    }

    pgPrint(`0x67 — Security Access GRANTED at level ${level}.`, "l-bold");
    pgProgressLog(`Security Access GRANTED — level ${level}.`);
    if (progUnlocked) {
      pgSetProgress(0, "Session ready. Awaiting command.");
      updateSessionDisplay("PROG 0x02");
      sendSessionControl(2);
    }
  } else {
    pgPrint(`0x7F 0x27 — ${data.message || "Security Access Failed"}`, "l-red");
  }
  pgRefreshStatusBar();
}


const DID_LENGTHS = {
  0xF180: 12, 0xF181: 11, 0xF184: 16, 0xF185: 16, 0xF186: 1,
  0xF18C: 12, 0xF18E: 8, 0xF190: 17, 0xF197: 16, 0xF19D: 8,
};

const DID_SECURITY_LEVELS = {
  0xF180: 0, 0xF181: 0, 0xF186: 0, 0xF18C: 0, 0xF190: 0,
  0xF18E: 1, 0xF197: 1,
  0xF19D: 2, 0xF184: 2, 0xF185: 2,
};

async function pgCmd_didRead(hexStr) {
  if (!hexStr) { pgPrint("usage: did.read <hex>  e.g. did.read 0xF19D", "l-dim"); return; }
  const did = parseInt(hexStr, 16);
  const required = DID_SECURITY_LEVELS[did];
  if (required != null && currentSecurityLevel < required) {
    pgPrint(
      `0x7F 0x22 0x33 — securityAccessDenied. ${hexStr} requires level ${required}, current level is ${currentSecurityLevel}. Run: security.key ${required}`,
      "l-red",
    );
    return;
  }
  pgPrint(`Sending 0x22 — ReadDataByIdentifier (${hexStr})...`, "l-dim");
  const res = await fetch(`/DID/${did}`);
  const data = await res.json();
  // data.data is the reslist dict {did: value} from uds_client, or null on NRC
  const val = data.data ? data.data[did] : null;
  if (val != null) pgPrint(`0x62 ${hexStr} = "${val}"`, "l-bold");
  else pgPrint(`0x7F 0x22 — read failed or unsupported DID`, "l-red");
}

async function pgCmd_didWrite(hexStr, value) {
  if (!hexStr || value == null) { pgPrint("usage: did.write <hex> <value>", "l-dim"); return; }
  const did = parseInt(hexStr, 16);
  const required = DID_SECURITY_LEVELS[did];
  if (required != null && currentSecurityLevel < required) {
    pgPrint(
      `0x7F 0x2E 0x33 — securityAccessDenied. ${hexStr} requires level ${required}, current level is ${currentSecurityLevel}. Run: security.key ${required}`,
      "l-red",
    );
    return;
  }
  const expected = DID_LENGTHS[did];
  if (expected != null && value.length !== expected) {
    pgPrint(`usage error — ${hexStr} requires exactly ${expected} bytes, got ${value.length}`, "l-red");
    return;
  }
  pgPrint(`Sending 0x2E — WriteDataByIdentifier (${hexStr} = "${value}")...`, "l-dim");
  const res = await fetch("/DID", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ DID: did, value }),
  });
  const data = await res.json();
  if (data.status === "success") pgPrint(`0x6E ${hexStr} — write acknowledged`, "l-bold");
  else pgPrint(`0x7F 0x2E — SID 0x${data.sid?.toString(16)} NRC 0x${data.nrc?.toString(16)}`, "l-red");
}

async function pgCmd_fileSelect(tag) {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

async function pgCmd_flashStart() {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

function pgStartFlashPolling() {
  if (pgFlashPolling) return;
  pgFlashPolling = true;
  let lastLoggedPct = -1;
  const poll = async () => {
    try {
      const res = await fetch("/prog/flash_status");
      const s = await res.json();
      pgRefreshStatusBar();
      if (
        s.status === "erasing" ||
        s.status === "writing" ||
        s.status === "verifying"
      ) {
        if (s.progress !== lastLoggedPct) {
          lastLoggedPct = s.progress;
          pgPrint(
            `${pgBar(s.progress)}  ${s.operation}  |  VBAT ${s.voltage}V  |  ${s.connection}`,
            "l-progress",
          );
          pgProgressLog(`${s.operation} — ${s.progress}%  VBAT ${s.voltage}V`);
          pgSetProgress(s.progress, s.operation);
        }
        setTimeout(poll, 500);
      } else if (s.status === "success") {
        pgPrint(pgBar(100) + "  Flash Successful!", "l-bold");
        pgProgressLog("Flash complete — checksum verified.", "l-bold");
        pgSetProgress(100, "Flash complete — verified");
        pgPrint("Verifying... checksum match confirmed.", "l-dim");
        pgFlashPolling = false;
      } else if (s.status === "error") {
        pgPrint(`FLASH FAILED — ${s.error}`, "l-red");
        pgFlashPolling = false;
      } else {
        pgFlashPolling = false;
      }
    } catch (_) {
      pgFlashPolling = false;
    }
  };
  poll();
}

async function pgCmd_flashStatus() {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

async function pgCmd_featureList() {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

async function pgCmd_featureSet(name, state) {
  if (!name || !state) {
    pgPrint("usage: feature.set <name> on|off", "l-dim");
    return;
  }
  const value = state.toLowerCase() === "on";
  pgPrint(
    `Sending 0x2E — coding ${name} = ${value ? "ON" : "OFF"} ...`,
    "l-dim",
  );
  const res = await fetch("/prog/feature_coding", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feature: name, value }),
  });
  const data = await res.json();
  if (data.status === "success") {
    pgPrint(`0x6E — ${name} ${value ? "ENABLED" : "DISABLED"}`, "l-bold");
  } else {
    pgPrint(`Error — ${data.message}`, "l-red");
  }
}

async function pgCmd_securityExtra(action, label) {
  pgPrint(`${label}...`, "l-dim");
  const res = await fetch("/prog/security_extras", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  const data = await res.json();
  if (data.status === "success") {
    pgPrint(`Done. ${JSON.stringify(data.data)}`, "l-amber");
  } else {
    pgPrint(`Error — ${data.message}`, "l-red");
  }
}

async function pgCmd_bench(step, tool) {
  pgPrint("⚠ not implemented — backend route for this command does not exist yet", "l-amber");
  return;
}

async function pgCmd_dtcClear() {
  pgPrint("Sending 0x14 0xFF 0xFF 0xFF — Clear all DTCs...", "l-dim");
  const res = await fetch("/prog/clear_dtc", { method: "POST" });
  const data = await res.json();
  if (data.status === "success") {
    pgPrint("0x54 — DTCs cleared successfully [Positive Response]", "l-bold");
  } else {
    pgPrint(`Error — ${data.message}`, "l-red");
  }
}

async function pgCmd_report() {
  const res = await fetch("/prog/state");
  const data = await res.json();
  const s = data.data;
  pgPrint("════ PROGRAMMING SESSION — FINAL REPORT ════", "l-bold");
  pgPrint(
    `Session        : ${s.session === 2 ? "PROGRAMMING (0x02)" : "DEFAULT (0x01)"}`,
  );
  pgPrint(`Security       : ${s.security.level >= 2 ? "UNLOCKED" : "LOCKED"}`);
  pgPrint(`Original File  : ${s.files.original ? s.files.original.name : "—"}`);
  pgPrint(`Modified File  : ${s.files.modified ? s.files.modified.name : "—"}`);
  pgPrint(
    `Flash Status   : ${s.flash.status.toUpperCase()} (${s.flash.progress}%)`,
  );
  pgPrint(
    `Immobilizer    : ${s.security_extras.immo_disabled ? "DISABLED" : "ACTIVE"}`,
  );
  pgPrint(
    `Comp. Protect. : ${s.security_extras.component_protection ? "ACTIVE" : "REMOVED"}`,
  );
  pgPrint(`Keys Programmed: ${s.security_extras.keys_programmed}`);
  pgPrint(`DTCs Cleared   : ${s.dtc_cleared_count} time(s)`);
  pgPrint("══════════════════════════════════════════", "l-bold");
}

function pgTriggerDownload(url, filename) {
  const a = document.createElement("a");
  a.href = url;
  if (filename) a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function pgCmd_logsDownload() {
  pgPrint("Requesting CAN log file from listener/logger...", "l-dim");
  try {
    pgTriggerDownload("/download/logger", "can_logs.csv");
    pgPrint("Download started — check your browser's downloads.", "l-bold");
    pgProgressLog("Log file download requested.");
  } catch (e) {
    pgPrint(`Error: ${e.message}`, "l-red");
  }
}

async function pgCmd_sysinfo() {
  pgPrint("════ SYSTEM STATUS ════", "l-bold");

  // Session / security state — tracked locally, updated by security.key and session changes
  pgPrint(`Security Level    : ${currentSecurityLevel}`);
  pgPrint(`Programming Mode  : ${progUnlocked ? "UNLOCKED" : "LOCKED"}`);

  // ECU identity — pulled live from the real DID table via /DID
  const idFields = [
    ["0xF180", "Boot SW Version"],
    ["0xF181", "App SW Version"],
    ["0xF18C", "Serial Number"],
    ["0xF190", "VIN"],
  ];
  for (const [hex, label] of idFields) {
    const did = parseInt(hex, 16);
    try {
      const res = await fetch(`/DID/${did}`);
      const data = await res.json();
      const val = data.data ? data.data[did] : null;
      pgPrint(`${label.padEnd(18, " ")}: ${val != null ? val : "—"}`);
    } catch (_) {
      pgPrint(`${label.padEnd(18, " ")}: — (read failed)`, "l-red");
    }
  }
  pgPrint("════════════════════════", "l-bold");
}

const HISTORY_FIELDS = {
  speed: "Speed (km/h)", rpm: "RPM", coolant: "Coolant Temp (°C)",
  oil_temp: "Oil Temp (°C)", fuel_pct: "Fuel %", fuel_rate: "Fuel Rate",
  throttle: "Throttle %", engine_load: "Engine Load %", accel: "Accel (m/s²)",
  battery: "Battery (V)",
};

async function pgCmd_historySummary(field) {
  const res = await fetch("/history-data");
  const data = await res.json();
  if (!field) {
    pgPrint("usage: history.summary <field>", "l-dim");
    pgPrint(`available fields: ${Object.keys(HISTORY_FIELDS).join(", ")}`, "l-dim");
    return;
  }
  const series = data[field];
  if (!series || !series.length) {
    pgPrint(`No history data for "${field}" yet.`, "l-red");
    return;
  }
  const nums = series.filter((v) => typeof v === "number");
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
  pgPrint(`${HISTORY_FIELDS[field] || field} — ${nums.length} samples`, "l-bold");
  pgPrint(`  min ${min.toFixed(1)}   max ${max.toFixed(1)}   avg ${avg.toFixed(1)}   current ${nums[nums.length - 1].toFixed(1)}`);
}

const ACTUATOR_IDS = {
  fan: 0x1001,
  "fuel.pump": 0x1002,
  headlamp: 0x1003,
  "door.lock": 0x1004,
};

async function pgCmd_ioSet(name, state) {
  const did = ACTUATOR_IDS[name];
  if (did == null) {
    pgPrint(`usage: io.set <actuator> on|off|ecu`, "l-dim");
    pgPrint(`available actuators: ${Object.keys(ACTUATOR_IDS).join(", ")}`, "l-dim");
    return;
  }
  let control_parameter, control_state;
  if (state === "ecu") {
    control_parameter = 0; // return control to ECU
    control_state = false;
  } else if (state === "on" || state === "off") {
    control_parameter = 3; // short-term adjustment
    control_state = state === "on";
  } else {
    pgPrint(`usage: io.set ${name} on|off|ecu`, "l-dim");
    return;
  }
  pgPrint(`Sending 0x2F — IOControl (${name} = ${state})...`, "l-dim");
  const res = await fetch("/IO_control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ DID: did, control_parameter, control_state }),
  });
  const data = await res.json();
  if (data.status === "success") pgPrint(`0x6F — ${name} set to ${state.toUpperCase()}`, "l-bold");
  else pgPrint(`Error — ${data.message}`, "l-red");
}

async function pgCmd_reportDownload() {
  pgPrint("Building session report...", "l-dim");
  const lines = [
    "════ PROGRAMMING SESSION — REPORT ════",
    `Generated      : ${new Date().toLocaleString()}`,
    `Security Level : ${currentSecurityLevel} (${currentSecurityLevel >= 2 ? "PROGRAMMING access" : currentSecurityLevel === 1 ? "EXTENDED access" : "no access"})`,
    `Prog. Session  : ${progUnlocked ? "UNLOCKED" : "LOCKED"}`,
    "═══════════════════════════════════════",
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  pgTriggerDownload(url, "session_report.txt");
  URL.revokeObjectURL(url);
  pgPrint("Report downloaded as session_report.txt", "l-bold");
  pgProgressLog("Session report downloaded.");
}


function pgCmd_help() {
  [
    "ecu.id                       read ECU identification block",
    "did.read <hex>               read any DID (0x22)",
    "did.write <hex> <value>      write a writable DID (0x2E)",
    "logs.download                download CAN log file from listener",
    "report.download              download session report as .txt",
    "security.key <level>         grant security access 1/2/3 (0x27)",
    "history.summary <field>      min/max/avg for a logged signal",
    "io.set <actuator> on|off|ecu force or release an actuator (0x2F)",
    "sysinfo                       show ECU identity + session/security state",
    "file.select <tag>            load a modified/tuned file (e.g. stage2)",
    "flash.start                  write the modified file to the ECU",
    "flash.status                 check flashing progress",
    "feature.list                 show feature-coding state",
    "feature.set <name> on|off    toggle a hidden OEM feature",
    "immo.off / immo.on           disable/enable immobilizer",
    "cp.remove / cp.restore       remove/restore component protection",
    "key.program                  program a new key/fob",
    "bench.remove                 remove ECU for bench flashing",
    "bench.power                  connect bench power supply",
    "bench.tool <name>            connect flashing tool (e.g. kess)",
    "dtc.clear                    clear all stored DTCs",
    "report                       print final session report",
    "clear                        clear the screen",
    "exit                          leave the programming session",
  ].forEach((l) => pgPrint(l, "l-dim"));
}

// ── Command dispatcher ──
async function pgRunCommand(raw) {
  const cmd = raw.trim();
  if (!cmd) return;
  pgEcho(cmd);

  const parts = cmd.split(/\s+/);
  const head = parts[0].toLowerCase();
  const args = parts.slice(1);

  try {
    switch (head) {
      case "help":
        pgCmd_help();
        break;
      case "clear": {
        const screen = document.getElementById("pgterm-screen");
        const boot = document.getElementById("pgterm-boot");
        const promptRow = document.getElementById("pgterm-prompt-row");
        if (screen && boot && promptRow) {
          screen.innerHTML = "";
          screen.appendChild(boot);
          screen.appendChild(promptRow);
        }
        break;
      }
      case "ecu.id":
        await pgCmd_ecuId();
        break;
      case "did.read":
        await pgCmd_didRead(args[0]);
        break;
      case "did.write":
        await pgCmd_didWrite(args[0], args[1]);
        break;
      case "logs.download":
        await pgCmd_logsDownload();
        break;
      case "report.download":
        await pgCmd_reportDownload();
        break;
      case "history.summary":
        await pgCmd_historySummary(args[0]);
        break;
      case "io.set":
        await pgCmd_ioSet(args[0], args[1]);
        break;
      case "sysinfo":
        await pgCmd_sysinfo();
        break;
      case "security.seed":
        await pgCmd_securitySeed();
        break;
      case "security.key":
        await pgCmd_securityKey(args[0]);
        break;
      case "file.select":
        await pgCmd_fileSelect(args[0]);
        break;
      case "flash.start":
        await pgCmd_flashStart();
        break;
      case "flash.status":
        await pgCmd_flashStatus();
        break;
      case "feature.list":
        await pgCmd_featureList();
        break;
      case "feature.set":
        await pgCmd_featureSet(args[0], args[1]);
        break;
      case "immo.off":
        await pgCmd_securityExtra(
          "disable_immo",
          "Disabling immobilizer (bench flashing prep)",
        );
        break;
      case "immo.on":
        await pgCmd_securityExtra("enable_immo", "Re-enabling immobilizer");
        break;
      case "cp.remove":
        await pgCmd_securityExtra("remove_cp", "Removing component protection");
        break;
      case "cp.restore":
        await pgCmd_securityExtra(
          "restore_cp",
          "Restoring component protection",
        );
        break;
      case "key.program":
        await pgCmd_securityExtra(
          "program_key",
          "Programming new key (Transponder 48)",
        );
        break;
      case "bench.remove":
        await pgCmd_bench("remove_ecu");
        break;
      case "bench.power":
        await pgCmd_bench("connect_power");
        break;
      case "bench.tool":
        await pgCmd_bench("connect_tool", args[0] || "KESS V2");
        break;
      case "bench.reinstall":
        await pgCmd_bench("reinstall");
        break;
      case "dtc.clear":
        await pgCmd_dtcClear();
        break;
      case "report":
        await pgCmd_report();
        break;
      case "exit":
        exitProgrammingSession();
        break;
      case "ecu.reset": {
        if (
          !confirm("Hard reset will clear session and adaptations. Continue?")
        )
          break;
        pgPrint("Sending 0x11 0x01 — Hard Reset...", "l-dim");
        pgProgressLog("ECU Reset requested...", "l-amber");
        try {
          const res = await fetch("/diagnostics_session_control/1");
          pgPrint("0x51 0x01 — ECU Reset acknowledged.", "l-bold");
          pgProgressLog("ECU Reset complete. Returning to Default session.");
          pgSetProgress(0, "Idle — no operation in progress");
          exitProgrammingSession();
          exitTechMode();
        } catch (e) {
          pgPrint("Error: " + e.message, "l-red");
        }
        break;
        
      }
      default:
        pgPrint(`command not found: ${head}  (type 'help')`, "l-red");
    }
  } catch (e) {
    pgPrint(`Error: ${e.message}`, "l-red");
  }
  pgRefreshStatusBar();
}

function initProgTerminal() {
  const input = document.getElementById("pgterm-input");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = input.value;
        input.value = "";
        pgRunCommand(val);
      }
    });
  }
  document.querySelectorAll(".pgterm-qbtn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cmd = btn.dataset.cmd;
      const shouldRun = btn.dataset.run === "1";
      if (!input) return;
      if (shouldRun) {
        pgRunCommand(cmd);
        input.value = "";
      } else {
        input.value = cmd;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
        return; // don't steal focus back below
      }
    });
  });
  pgRefreshStatusBar();
}

async function pgEditorWrite() {
  const editor = document.getElementById("pg-code-editor");
  const status = document.getElementById("pg-editor-status");
  if (!editor || !editor.value.trim()) return;
  if (status) status.textContent = "Writing...";
  pgPrint("Sending 0x2E — WriteDataByIdentifier (editor content)...", "l-dim");
  // Calls the existing writeDID with a custom DID for ECU code block
  try {
    const res = await fetch("/DID", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ DID: 0xf19d, value: editor.value }),
    });
    const data = await res.json();
    if (data.status === "success") {
      pgPrint("0x6E — Write acknowledged [Positive Response]", "l-bold");
      if (status) status.textContent = "✓ Written to ECU";
    } else {
      pgPrint("0x7F 0x2E — " + (data.data || "Write failed"), "l-red");
      if (status) status.textContent = "✗ Write failed";
    }
  } catch (e) {
    pgPrint("Error: " + e.message, "l-red");
  }
}

function pgEditorClear() {
  const editor = document.getElementById("pg-code-editor");
  const status = document.getElementById("pg-editor-status");
  if (editor) editor.value = "";
  if (status) status.textContent = "";
}

// ══════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  startClock();
  setMode("live");
  initProgTerminal();

  document.getElementById("signal-select")?.addEventListener("change", () => {
    if (currentMode === "history") loadHistory();
  });
  document.getElementById("range-select")?.addEventListener("change", () => {
    if (currentMode === "history") loadHistory();
  });
});

setInterval(loadHistory, 3000);
setInterval(updateLiveChart, 1000);
setInterval(pollLive, 100);

pollLive();
