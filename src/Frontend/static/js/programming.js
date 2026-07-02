// Programming tab (Security Access granted): the pgterm command-line
// terminal, all pgCmd_* command handlers (security access, DID read/write,
// feature coding, flash workflow, reports), and CAN sniffer bootstrap.

import { state } from "./state.js";
import { HISTORY_FIELDS } from "./history.js";
import { setMode } from "./navigation.js";
import {
    exitTechMode,
    sendSessionControl,
    updateSessionDisplay,
} from "./session.js";
import { setText, showToastMessage, hexStr } from "./ui.js";

let currentSecurityLevel = 0;
let secAttemptsLeft = 3;
let secLockout = false;
// Cancel any in-progress simulated flash operation and stop its status polling.
function progCancelFlash() {
    if (!progFlashState.running) return;
    progFlashState.cancelled = true;
    progLog("User requested cancel. Waiting for safe abort point...", "warn");
    setTimeout(() => progFinishFlash(false), 400);
}

let pgFlashPolling = false;

// Append a formatted line of output to the pgterm console.
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

// Append a raw (unstyled) line of output to the pgterm console.
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

// Append a progress-log line to the pgterm console during long-running operations.
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

// Update the pgterm inline progress bar's percentage.
function pgSetProgress(pct, status) {
    const fill = document.getElementById("pg-progress-fill");
    const stat = document.getElementById("pg-progress-status");
    const pctEl = document.getElementById("pg-progress-pct");
    if (fill) fill.style.width = pct + "%";
    if (stat) stat.textContent = status || "Idle — no operation in progress";
    if (pctEl) pctEl.textContent = pct + "%";
}

// Echo the user's typed command back into the pgterm console before executing it.
function pgEcho(cmd) {
    pgPrint(cmd, "l-cmd");
}

// Focus the pgterm command-line input, e.g. after switching into the Programming tab.
export function pgtermFocusInput() {
    const input = document.getElementById("pgterm-input");
    if (input) setTimeout(() => input.focus(), 50);
}

// Render an ASCII-style progress bar string of the given width/percentage for pgterm output.
function pgBar(pct) {
    const width = 24;
    const filled = Math.round((pct / 100) * width);
    return (
        "[" + "■".repeat(filled) + "□".repeat(width - filled) + "] " + pct + "%"
    );
}

// ── Boot banner, printed once on first entry ──
// Print the pgterm boot banner shown when the Programming session backdoor is triggered.
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
        [
            "Type 'help' for the command list, or use the buttons below.",
            "l-dim",
        ],
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

// Reveal the Programming-session terminal panel and hide the pre-session placeholder.
function showProgPanel() {
    const progBtn = document.getElementById("prog-tab-btn");
    if (progBtn) progBtn.classList.remove("hidden");
    setMode("programming");
    pgBootBanner();
}

// Way B — backdoor entry. Skips the seed/key exchange but still
// notifies the backend so /prog/* routes treat the session as unlocked.
// Enter the Programming session via the keyboard backdoor sequence: unlocks the terminal and prints the boot banner.
export async function enterProgrammingSessionBackdoor() {
    try {
        const res = await fetch("/diagnostics_session_control/2");
        const data = await res.json();
        showToastMessage(data.status, true);

        if (data.status == "success") {
            updateSessionDisplay("PROG 0x02");
            showProgPanel();
        }
        showToastMessage("Programming session entered", true);
    } catch (e) {
        console.log(e);
        showToastMessage("Could not enter programming session", false);
        pgPrint("Backdoor auth failed — backend unreachable.", "l-red");
    }
}

// Tear down the Programming session, resetting security level and hiding the terminal panel.
export async function exitProgrammingSession() {
    state.progUnlocked = false;
    currentSecurityLevel = 0;
    try {
        await fetch("/diagnostics_session_control/3", { method: "GET" });
    } catch (_) {}
    updateSessionDisplay("EXT 0x03");
    sendSessionControl(3);
    pgRefreshStatusBar();
    const progBtn = document.getElementById("prog-tab-btn");
    if (progBtn) progBtn.classList.add("hidden");
    setMode("technician");
}

// Refresh the pgterm status bar (session/security-level/ECU-id summary).
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
// pgterm command: read and display the target ECU's identifier DID.
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

// pgterm command: request a SecurityAccess (0x27) seed for the given level.
async function pgCmd_securitySeed() {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}

// pgterm command: submit a computed SecurityAccess key and update the granted security level on success.
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

    pgPrint(
        `Sending 0x27 — Security Access (level ${level}) seed+key handshake...`,
        "l-dim",
    );
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
        state.progUnlocked = level >= 2;

        const overlay = document.getElementById("pg-editor-overlay");
        const editor = document.getElementById("pg-code-editor");
        const actions = document.getElementById("pg-editor-actions");
        const lockLabel = document.getElementById("pg-editor-lock");
        if (state.progUnlocked) {
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
        if (state.progUnlocked) {
            pgSetProgress(0, "Session ready. Awaiting command.");
            updateSessionDisplay("PROG 0x02");
            sendSessionControl(2);
        }
    } else {
        pgPrint(
            `0x7F 0x27 — ${data.message || "Security Access Failed"}`,
            "l-red",
        );
    }
    pgRefreshStatusBar();
}

const DID_LENGTHS = {
    0xf180: 12,
    0xf181: 11,
    0xf184: 16,
    0xf185: 16,
    0xf186: 1,
    0xf18c: 12,
    0xf18e: 8,
    0xf190: 17,
    0xf197: 16,
    0xf19d: 8,
};

const DID_SECURITY_LEVELS = {
    0xf180: 0,
    0xf181: 0,
    0xf186: 0,
    0xf18c: 0,
    0xf190: 0,
    0xf18e: 1,
    0xf197: 1,
    0xf19d: 2,
    0xf184: 2,
    0xf185: 2,
};

// pgterm command: ReadDataByIdentifier, enforcing the DID's minimum security level before sending.
async function pgCmd_didRead(hexStr) {
    if (!hexStr) {
        pgPrint("usage: did.read <hex>  e.g. did.read 0xF19D", "l-dim");
        return;
    }
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

// pgterm command: WriteDataByIdentifier, enforcing the DID's minimum security level before sending.
async function pgCmd_didWrite(hexStr, value) {
    if (!hexStr || value == null) {
        pgPrint("usage: did.write <hex> <value>", "l-dim");
        return;
    }
    const did = parseInt(hexStr, 16);
    const required = DID_SECURITY_LEVELS[did];
    if (required != null && currentSecurityLevel < required) {
        pgPrint(
            `0x7F 0x2E 0x33 — securityAccessDenied. ${hexStr} requires level ${required}, current level is ${currentSecurityLevel}. Run: security.key ${required}`,
            "l-red",
        );
        return;
    }
    // const expected = DID_LENGTHS[did];
    // if (expected != null && value.length !== expected) {
    //   pgPrint(`usage error — ${hexStr} requires exactly ${expected} bytes, got ${value.length}`, "l-red");
    //   return;
    // }
    pgPrint(
        `Sending 0x2E — WriteDataByIdentifier (${hexStr} = "${value}")...`,
        "l-dim",
    );
    const res = await fetch("/DID", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ DID: did, value }),
    });
    const data = await res.json();
    if (data.status === "success")
        pgPrint(`0x6E ${hexStr} — write acknowledged`, "l-bold");
    else
        pgPrint(
            `0x7F 0x2E — SID 0x${data.sid?.toString(16)} NRC 0x${data.nrc?.toString(16)}`,
            "l-red",
        );
}
// pgterm command: list all known DIDs with their required security levels.
async function pgCmd_didLS() {
  try{
    const response = await fetch('/DID')
    const DID_namelist = await response.json()
    for(const [hex_key, name] of Object.entries(DID_namelist)){
      pgPrint(name + ": " + hex_key)
    }
  }
  catch(err){
    pgPrint("Could not fetch DID list", "l-red")
    console.error(err)
  }

}

// pgterm command: select a firmware image file for the simulated flash workflow.
async function pgCmd_fileSelect(tag) {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}

// pgterm command: start the simulated ECU flash routine for the selected file.
async function pgCmd_flashStart() {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}

// Begin polling the backend for simulated flash-progress updates and stream them to pgterm.
function pgStartFlashPolling() {
  if (pgFlashPolling) return;
  pgFlashPolling = true;
  let lastLoggedPct = -1;
  const poll = async () => {
    try {
      const res = await fetch("/flash_status");
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

// pgterm command: report the current status of an in-progress or completed flash operation.
async function pgCmd_flashStatus() {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}

// pgterm command: list available feature-coding options and their current state.
async function pgCmd_featureList() {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}

// pgterm command: enable/disable a feature-coding option via WriteDataByIdentifier.
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

// pgterm command: perform an extended security-access operation (e.g. immobilizer/component protection).
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

// pgterm command: run the bench-flash workflow variant (off-vehicle programming).
async function pgCmd_bench(step, tool) {
    pgPrint(
        "⚠ not implemented — backend route for this command does not exist yet",
        "l-amber",
    );
    return;
}
// Clear all stored DTCs (ClearDiagnosticInformation, 0x14) -- shared by pgterm and the Technician DTC panel.
export async function pgCmd_dtcClear() {
    pgPrint("Sending 0x14 0xFF 0xFF 0xFF — Clear all DTCs...", "l-dim");
    const res = await fetch("/DTC", { method: "DELETE" });
    const data = await res.json();
    if (data.status === "success") {
        pgPrint(
            "0x54 — DTCs cleared successfully [Positive Response]",
            "l-bold",
        );
        return {
            status: "success",
            message: "0x54 — DTCs cleared successfully [Positive Response]",
        };
    } else {
        pgPrint(`Error — ${data.message}`, "l-red");
        return {
            status: "error",
            message: data.message,
        };
    }
}

// pgterm command: generate a session summary report.
async function pgCmd_report() {
    const res = await fetch("/state");
    const data = await res.json();
    const s = data.data;
    pgPrint("════ PROGRAMMING SESSION — FINAL REPORT ════", "l-bold");
    pgPrint(
        `Session        : ${s.session === 2 ? "PROGRAMMING (0x02)" : "DEFAULT (0x01)"}`,
    );
    pgPrint(
        `Security Level      : ${s.security.level >= 2 ? "UNLOCKED" : "LOCKED"}`,
    );
    pgPrint(
        `Original File  : ${s.files.original ? s.files.original.name : "—"}`,
    );
    pgPrint(
        `Modified File  : ${s.files.modified ? s.files.modified.name : "—"}`,
    );
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

// Trigger a browser download for a backend-generated file (logs/report/firmware).
async function pgDownloadFile(url, filename) {
    pgPrint("Requesting firmware bin file from ECU...", "l-dim");

    try {
        const response = await fetch(`/download/${url}`);

        // Server returned an error (e.g. 400, 500)
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.message || "Download failed");
        }

        const contentType = response.headers.get("Content-Type");

        // ECU returned NRC as JSON
        if (contentType.includes("application/json")) {
            const data = await response.json();
            pgPrint(data.message, "l-red");
            return;
        }

        // Firmware received
        const blob = await response.blob();

        const download_url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = download_url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();

        window.URL.revokeObjectURL(download_url);

        pgPrint("Download started — check your browser's downloads.", "l-bold");
        pgProgressLog(`${filename} file download requested.`);
    } catch (e) {
        pgPrint(`Error: ${e.message}`, "l-red");
    }
}
// pgterm command: download the currently loaded firmware image.
async function pgCmd_firmwareDownload() {
    pgPrint("Requesting firmware bin file from ECU...", "l-dim");
    await pgDownloadFile("firmware", "firmware.bin");
}
// pgterm command: download the CAN logger output.
async function pgCmd_logsDownload() {
    pgPrint("Requesting CAN log file from listener/logger...", "l-dim");
    await pgDownloadFile("logger", "all_logs.zip");
}

// pgterm command: print a summary of current session/security/ECU state.
async function pgCmd_sysinfo() {
    pgPrint("════ SYSTEM STATUS ════", "l-bold");

    // Session / security state — tracked locally, updated by security.key and session changes
    pgPrint(`Security Level    : ${currentSecurityLevel}`);
    pgPrint(
        `Programming Mode  : ${state.progUnlocked ? "UNLOCKED" : "LOCKED"}`,
    );

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

// pgterm command: print a compact summary of recent signal history.
async function pgCmd_historySummary(field) {
    const res = await fetch("/history-data");
    const data = await res.json();
    if (!field) {
        pgPrint("usage: firmware.download ", "l-dim");
        pgPrint(
            `available fields: ${Object.keys(HISTORY_FIELDS).join(", ")}`,
            "l-dim",
        );
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
    pgPrint(
        `${HISTORY_FIELDS[field] || field} — ${nums.length} samples`,
        "l-bold",
    );
    pgPrint(
        `  min ${min.toFixed(1)}   max ${max.toFixed(1)}   avg ${avg.toFixed(1)}   current ${nums[nums.length - 1].toFixed(1)}`,
    );
}

const ACTUATOR_IDS = {
    fan: 0x1001,
    "fuel.pump": 0x1002,
    headlamp: 0x1003,
    "door.lock": 0x1004,
};

// pgterm command: drive an actuator via InputOutputControlByIdentifier.
async function pgCmd_ioSet(name, state) {
    const did = ACTUATOR_IDS[name];
    if (did == null) {
        pgPrint(`usage: io.set <actuator> on|off|ecu`, "l-dim");
        pgPrint(
            `available actuators: ${Object.keys(ACTUATOR_IDS).join(", ")}`,
            "l-dim",
        );
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
    if (data.status === "success")
        pgPrint(`0x6F — ${name} set to ${state.toUpperCase()}`, "l-bold");
    else pgPrint(`Error — ${data.message}`, "l-red");
}

// pgterm command: download the generated session report file.
async function pgCmd_reportDownload() {
    pgPrint("Building session report...", "l-dim");
    const lines = [
        "════ PROGRAMMING SESSION — REPORT ════",
        `Generated      : ${new Date().toLocaleString()}`,
        `Security Level : ${currentSecurityLevel} (${currentSecurityLevel >= 2 ? "PROGRAMMING access" : currentSecurityLevel === 1 ? "EXTENDED access" : "no access"})`,
        `Prog. Session  : ${state.progUnlocked ? "UNLOCKED" : "LOCKED"}`,
        "═══════════════════════════════════════",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    pgTriggerDownload(url, "session_report.txt");
    URL.revokeObjectURL(url);
    pgPrint("Report downloaded as session_report.txt", "l-bold");
    pgProgressLog("Session report downloaded.");
}

// pgterm command: list all available terminal commands.
function pgCmd_help() {
    [
        "ecu.id                       read ECU identification block",
        "did.read <hex>               read any DID (0x22)",
        "did.write <hex> <value>      write a writable DID (0x2E)",
        "logs.download                download CAN log file from listener",
        "report.download              download session report as .txt",
        "security.key <level>         grant security access 1/2/3 (0x27)",
        "firmware.download            download bin file of ECU firmware",
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
// Parse and dispatch a raw pgterm command line to the matching pgCmd_* handler.
export async function pgRunCommand(raw) {
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
            case "did.ls":
                await pgCmd_didLS();
            case "logs.download":
                await pgCmd_logsDownload();
                break;
            case "report.download":
                await pgCmd_reportDownload();
                break;
            case "firmware.download":
                await pgCmd_firmwareDownload();
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
                await pgCmd_securityExtra(
                    "enable_immo",
                    "Re-enabling immobilizer",
                );
                break;
            case "cp.remove":
                await pgCmd_securityExtra(
                    "remove_cp",
                    "Removing component protection",
                );
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
            case "report_dtcClear();":
                await pgCmd_report();
                break;
            case "exit":
                exitProgrammingSession();
                break;
            case "ecu.reset": {
                if (
                    !confirm(
                        "Hard reset will clear session and adaptations. Continue?",
                    )
                )
                    break;
                pgPrint("Sending 0x11 0x01 — Hard Reset...", "l-dim");
                pgProgressLog("ECU Reset requested...", "l-amber");
                try {
                    const res = await fetch("/diagnostics_session_control/1");
                    pgPrint("0x51 0x01 — ECU Reset acknowledged.", "l-bold");
                    pgProgressLog(
                        "ECU Reset complete. Returning to Default session.",
                    );
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

// Wire up the pgterm input element's keydown handling (history, submit) on first load.
export function initProgTerminal() {
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

// Write the value currently entered in the DID editor panel via WriteDataByIdentifier.
export async function pgEditorWrite() {
    const editor = document.getElementById("pg-code-editor");
    const status = document.getElementById("pg-editor-status");
    if (!editor || !editor.value.trim()) return;
    if (status) status.textContent = "Writing...";
    pgPrint(
        "Sending 0x2E — WriteDataByIdentifier (editor content)...",
        "l-dim",
    );
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

// Reset the DID editor panel's input fields.
export function pgEditorClear() {
    const editor = document.getElementById("pg-code-editor");
    const status = document.getElementById("pg-editor-status");
    if (editor) editor.value = "";
    if (status) status.textContent = "";
}

// ── Tilt: rotateX/rotateY based on mouse position within card ──
