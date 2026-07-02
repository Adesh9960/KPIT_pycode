// Technician tab (UDS Extended Session): ReadDataByIdentifier /
// WriteDataByIdentifier / IOControl primitives, the DTC panel, and the CAN
// message sniffer.

import { state } from "./state.js";
import { updateTyrePressure } from "./advanced.js";
import { pgCmd_dtcClear } from "./programming.js";
import { showUDSResponse, updateCANStatus } from "./session.js";
import { hexStr, setText, showToastMessage } from "./ui.js";

// Send ReadDataByIdentifier (0x22) for a DID and render the result into the given target element.
export async function readDID(did, targetId, unit) {
    showUDSResponse(`Sending 0x22 ${hexStr(did)} ...`);
    try {
        const res = await fetch(`http://127.0.0.1:5000/DID/${did}`);
        const data = await res.json();
        if (data.status === "success") {
            const val = data.data[did] != null ? data.data[did] : "—";
            console.log(val);
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
// Send WriteDataByIdentifier (0x2E) for a DID with a new value and report the response.
export async function writeDID(did, value) {
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
// Send InputOutputControlByIdentifier (0x2F) to actuate a component and report the response.
export async function ioControl(did, controlParam, controlState) {
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
            showUDSResponse(
                `0x6F ${hexStr(did)} — IO Control applied: ${label}`,
            );
        } else {
            showUDSResponse(`0x7F 0x2F — ${data.message}`);
        }
    } catch (e) {
        showUDSResponse(`Error: ${e.message}`);
    }
}

// GET /diagnostics_session_control/<int:session>
// Send ReadDTCInformation (0x19) and render the returned DTC list.
export async function loadDTCs() {
    try {
        showUDSResponse("Sending 0x19 — Loading all DTCs ...");
        const res = await fetch("/DTC");
        const data = await res.json();
        if (data.status === "success") {
            renderDTCs(data.dtcs);
            showUDSResponse(
                "0x59 — DTCs loaded successfully [Positive Response]",
            );
        } else showToastMessage(data.message);
    } catch (err) {
        console.error(err);
    }
}
// Clear all stored DTCs via the Programming-tab DTC-clear command and refresh the DTC panel.
export async function clearDTCs() {
    showUDSResponse("Sending 0x14 0xFF 0xFF 0xFF — Clear all DTCs ...");

    const res = await pgCmd_dtcClear();
    if (res.status == "success") {
        document.getElementById("tech-dtc-list").innerHTML =
            '<div class="tech-dtc-empty">No DTCs stored. All systems nominal.</div>';
        setText("dtc-count-badge", "No Active DTCs");
        document.getElementById("dtc-count-badge").className =
            "dtc-count-badge ok";
        showUDSResponse("0x54 — DTCs cleared successfully [Positive Response]");
    } else showUDSResponse(res.message);
}

// ── Helper: show response in UDS response bar ──
// ══════════════════════════════════════════════════
// TECHNICIAN PAGE UPDATE
// ══════════════════════════════════════════════════
// Update the Technician tab's live readouts, tyre pressures, and CAN status from a polled data payload (Extended session only).
export function updateTechnician(d) {
    if (!state.techUnlocked) return;
    const tyres = d.tyres || d.tyre_pressure || {};
    const bv = d.voltage || d.battery_v || 0;
    const bsoc = Math.max(
        0,
        Math.min(100, ((bv - 11.8) / (14.4 - 11.8)) * 100),
    );

    // ECM
    setText("tech-rpm", (d.rpm || 0).toLocaleString() + " RPM");
    setText("tech-load", (d.engine_load || 0).toFixed(1) + "%");
    setText("tech-throttle", (d.throttle_pct || 0).toFixed(1) + "%");
    setText(
        "tech-coolant",
        (d.coolant || d.coolant_temp || 0).toFixed(1) + "°C",
    );
    setText("tech-oiltemp", (d.oil_temp || 0).toFixed(1) + "°C");
    setText("tech-fuelrate", (d.fuel_rate || 0).toFixed(2) + " mL/s");
    setText("tech-accel", (d.accel_ms2 || d.accel || 0).toFixed(2) + " m/s²");
    setText("tech-stall", d.stall_risk ? "⚠ YES" : "NO");
    // New: engine_state in ECM card
    setText("tech-engstate", d.engine_state || "IDLE");

    // TCM
    setText("tech-gear", d.gear_num == 0 ? "Neutral" : d.gear_num);
    setText("tech-gearnum", (d.gear_num || 0) === 0 ? "N" : String(d.gear_num));
    setText("tech-clutch", d.clutch_state ? "DOWN" : "UP");
    setText("tech-brake", d.brake_state ? "DOWN" : "UP");
    setText("tech-transtemp", (d.oil_temp || 0).toFixed(1) + "°C");

    // ABS
    setText("tech-speed", (d.speed || 0) + " km/h");
    const wsp = d.speed || 0;
    setText("tech-wfl", wsp + " km/h");
    setText("tech-wfr", wsp + " km/h");
    setText("tech-wrl", wsp + " km/h");
    setText("tech-wrr", wsp + " km/h");
    setText("tech-brakepct", d.brake_force_pct + "%");

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
    updateTyrePressure("tech-tfl", null, d.tyre_pressure_fl);
    updateTyrePressure("tech-tfr", null, d.tyre_pressure_fr);
    updateTyrePressure("tech-trl", null, d.tyre_pressure_rl);
    updateTyrePressure("tech-trr", null, d.tyre_pressure_rr);

    // CAN bus stats
    updateCANStatus(d);

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

// Append one decoded CAN frame row to the message sniffer table, trimming old rows past the row cap.
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

// Render the DTC list panel: empty state, count badge, and one row per active DTC.
export function renderDTCs(dtcs) {
    const list = document.getElementById("tech-dtc-list");
    const badge = document.getElementById("dtc-count-badge");
    const clearBtn = document.getElementById("dtc-clear-btn");

    list.innerHTML = "";

    if (!dtcs || dtcs.length === 0) {
        badge.textContent = "No Active DTCs";
        badge.className = "dtc-count-badge ok";

        clearBtn.disabled = true;

        list.innerHTML = `
            <div class="tech-dtc-empty">
                No DTCs stored. All systems nominal.
            </div>
        `;
        return;
    }

    badge.textContent = `${dtcs.length} DTC${dtcs.length > 1 ? "s" : ""} Found`;
    badge.className = "dtc-count-badge fault";

    clearBtn.disabled = false;

    dtcs.forEach((dtc) => {
        const code = dtc.code.toString(16).toUpperCase().padStart(6, "0");
        const status =
            "0x" + dtc.status.toString(16).toUpperCase().padStart(2, "0");

        const row = document.createElement("div");
        row.className = "tech-dtc-item";

        row.innerHTML = `
            <div class="tech-dtc-main">
                <div class="tech-dtc-code">${code}</div>
            </div>

            <div class="tech-dtc-status">
                ${status}
            </div>
        `;

        list.appendChild(row);
    });
}

// ══════════════════════════════════════════════════
// POLLING
// ══════════════════════════════════════════════════

// Build a single DTC list-item DOM node with formatted code/status text.
function createDTCListItem(){
  <div class="tech-dtc-item">

    <div class="tech-dtc-codes">
        <span class="dtc-code">P0301</span>
        <span class="dtc-code uds-code">0x123456</span>
    </div>

    <div class="tech-dtc-description">
        Cylinder 1 Misfire Detected
    </div>

</div>
}
