// UDS diagnostic-session lifecycle: Extended-session unlock (keyboard
// sequence + confirmation modal), Programming-session backdoor detection,
// TesterPresent keep-alive, ECUReset, and the shared UDS response-bar helper.

import { state } from "./state.js";
import { setMode } from "./navigation.js";
import {
    enterProgrammingSessionBackdoor,
    exitProgrammingSession,
} from "./programming.js";
import { setText, showToastMessage } from "./ui.js";

let tpInterval = null; // TesterPresent (0x3E) heartbeat timer
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
        if (!state.techUnlocked) {
            sendSessionControl(3)
                .then((res) => res.json())
                .then((data) => {
                    if (data.status === "success") showUDSModal();
                    else showToastMessage(data.message);
                })
                .catch((e) => showToastMessage(e.message));
        }
    }
    // Way B — Backdoor for Programming Session (only you know this)
    // Sequence: p r o g 1 2 3  (typed while in technician mode)
    checkBackdoor(e.key.toLowerCase());
});

// ── Way B: Programming backdoor buffer ──
const PROG_BACKDOOR = ["p", "r", "o", "g", "1", "2", "3"];
let progBuffer = [];
// Watch keystrokes for the Programming-session backdoor sequence once Extended session is active.
function checkBackdoor(key) {
    if (!state.techUnlocked) return; // Must be in Extended session first
    progBuffer.push(key);
    if (progBuffer.length > PROG_BACKDOOR.length) progBuffer.shift();
    if (progBuffer.join("") === PROG_BACKDOOR.join("")) {
        progBuffer = [];
        // Still enforce speed pre-condition
        if (state.lastSpeed > 0) {
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

// Reveal the Extended-session (Technician mode) unlock confirmation modal.
function showUDSModal() {
    document.getElementById("uds-overlay").classList.add("visible");
}

// Send diagnosticSessionControl(0x03) to enter Extended (Technician) session and update UI state on success.
export function confirmTechUnlock() {
    state.techUnlocked = true;

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

// Dismiss the Technician-unlock modal without changing session state.
export function cancelTechUnlock() {
    document.getElementById("uds-overlay").classList.remove("visible");
}

// Return to the default session (0x01), tearing down Programming session first if one is active.
export function exitTechMode() {
    // If in programming, exit that first
    if (state.progUnlocked) exitProgrammingSession();
    state.techUnlocked = false;
    stopTesterPresent();
    const techBtn = document.getElementById("tech-tab-btn");
    if (techBtn) techBtn.classList.add("hidden");
    const udsStatus = document.getElementById("uds-status");
    const udsLabel = document.getElementById("uds-label");
    if (udsStatus) udsStatus.classList.remove("extended");
    if (udsLabel) udsLabel.textContent = "DEFAULT";
    const hint = document.getElementById("adv-uds-hint");
    if (hint)
        hint.textContent =
            "🔒 Technician mode locked — type 0x10 0x03 to unlock";
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

// Clear the TesterPresent (0x3E) keep-alive interval, if one is running.
function stopTesterPresent() {
    if (tpInterval) {
        clearInterval(tpInterval);
        tpInterval = null;
    }
    const tpIndicator = document.getElementById("tp-indicator");
    if (tpIndicator) tpIndicator.classList.add("hidden");
}

// Send a single TesterPresent (0x3E) request to hold the current diagnostic session open.
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
    if (document.hidden && state.techUnlocked) {
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
// Refresh the session-state badge in the header to reflect the active UDS session.
export function updateSessionDisplay(label) {
    const el = document.getElementById("uds-label");
    if (el) el.textContent = label;
    const can = document.getElementById("can-session-display");
    if (can) can.textContent = label;
}

// ══════════════════════════════════════════════════
// UDS REST CALLS — matches new app.py endpoints
// ══════════════════════════════════════════════════

// GET /DID/<int:DID>  — ReadDataByIdentifier (0x22)
// POST a diagnosticSessionControl request for the given session type to the backend.
export async function sendSessionControl(session) {
    return await fetch(`/diagnostics_session_control/${session}`);
}

// ECU Reset (0x11) — only in Programming session
// Send an ECUReset (0x11) hard-reset request and report the response.
export async function ecuReset() {
    // if (!state.progUnlocked) {
    //   showUDSResponse("0x7F 0x11 0x33 — Security access denied");
    //   return;
    // }
    if (
        !confirm(
            "Hard reset will clear session, adaptations and restart signal generation. Continue?",
        )
    )
        return;
    showUDSResponse("Sending 0x11 0x01 — Hard Reset ...");
    try {
        // Reuse session control endpoint as proxy for reset signal
        await fetch("/diagnostics_session_control/1");
        await fetch("/security_access/0");
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
// Update the CAN bus connection indicator from the latest polled data payload.
export function updateCANStatus(data) {
    document.getElementById("tech-can-load").textContent =
        data.bus_status ?? "UNKNOWN";

    document.getElementById("tech-can-msgrate").textContent =
        `${data.message_speed ?? 0} frames/s`;

    document.getElementById("tech-can-errrate").textContent =
        data.error_frames ?? 0;
}
// Write a formatted UDS request/response line into the response bar.
export function showUDSResponse(msg) {
    setText("uds-response-text", msg);
    const bar = document.getElementById("tech-uds-response");
    if (bar) {
        bar.classList.add("uds-resp-flash");
        setTimeout(() => bar.classList.remove("uds-resp-flash"), 400);
    }
}
