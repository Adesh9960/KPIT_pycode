// Generic UI helpers shared by every tab: status indicator, live clock,
// generic toast messages, and the rule-based alert/toast system driven by
// polled data (over/under-range warnings on gauges).

// Format a numeric DID as a zero-padded 0x hex string.
export function hexStr(val) {
    return "0x" + val.toString(16).toUpperCase().padStart(4, "0");
}

// ══════════════════════════════════════════════════
// STATUS HELPERS
// ══════════════════════════════════════════════════
// Toggle the CAN-connected/disconnected indicator in the header.
export function setStatus(ok, msg) {
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

// Set textContent on an element by id, no-op if the element isn't present.
export function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// Spawn a one-off toast notification (used for generic errors/info, distinct from the rule-based alert toasts).
export function showToastMessage(msg, critical) {
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
// Start the header's live wall-clock display, updating once per second.
export function startClock() {
    const timeEl = document.getElementById("sys-time");
    const liveDateEl = document.getElementById("live-date-display");
    const advDateEl = document.getElementById("adv-date-display");

    setInterval(() => {
        const now = new Date();

        // Update Time (e.g., 16:40:21)
        if (timeEl) {
            timeEl.textContent = now.toLocaleTimeString("en-IN", {
                hour12: false,
            });
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

// Apply the out-of-range highlight style to a gauge/readout element.
function applyHighlight(targets, critical) {
    targets.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove("param-warn", "param-crit");
        el.classList.add(critical ? "param-crit" : "param-warn");
    });
}
// Remove the out-of-range highlight style from a gauge/readout element.
function clearHighlight(targets) {
    targets.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.classList.remove("param-warn", "param-crit");
    });
}
// Create and animate in an alert toast for a triggered ALERT_RULES entry.
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
// Animate out and remove an active alert toast.
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
// Evaluate ALERT_RULES against the latest polled data and spawn/dismiss toasts accordingly.
export function checkAlerts(d) {
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
                activeAlerts[rule.key].toastEl = spawnToast(
                    rule,
                    rule.message(d),
                );
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
