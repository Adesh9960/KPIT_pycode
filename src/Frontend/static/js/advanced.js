// Advanced User Mode tab: extended readouts, tyre pressures, and UDS
// pre-condition checks (e.g. vehicle-stopped) shown before allowing certain operations.

import { setText } from "./ui.js";

let advSparkBuf = { x: [], y: [] };
// Evaluate and display UDS pre-condition checks (e.g. vehicle stopped) based on current speed.
export function updatePreConditions(speed) {
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
    // the pgterm engine's `security.seed` command — see state.lastSpeed usage there.
}
// Update a single tyre-pressure readout element with a value and status color.
export function updateTyrePressure(id, barId, pressure) {
    const valueEl = document.getElementById(id);
    const barEl = document.getElementById(barId);

    if (pressure == null || isNaN(pressure)) {
        valueEl.innerHTML = `— <span class="adv-tyre-unit">psi</span>`;
        if (barEl) barEl.style.width = "0%";
        return;
    }

    valueEl.innerHTML = `${pressure.toFixed(1)} <span class="adv-tyre-unit">psi</span>`;

    // Scale 20–40 psi to 0–100%
    const percent = Math.max(0, Math.min(100, ((pressure - 20) / 20) * 100));
    if (barEl) barEl.style.width = `${percent}%`;

    // Optional color indication
    if (pressure < 28)
        if (barEl)
            barEl.style.background = "#ef4444"; // Red
        else if (pressure < 30)
            if (barEl)
                barEl.style.background = "#f59e0b"; // Orange
            else if (pressure <= 36)
                if (barEl)
                    barEl.style.background = "#22c55e"; // Green
                else if (barEl) barEl.style.background = "#3b82f6"; // Blue
}
// ══════════════════════════════════════════════════
// ADVANCED PAGE UPDATE
// ══════════════════════════════════════════════════
// Update the Advanced tab's extended signal readouts, tyre pressures, and pre-condition checks from a polled data payload.
export function updateAdvanced(d) {
    const tyres = d.tyres || d.tyre_pressure || {};
    const bv = d.voltage || d.battery_v || 0;
    const bsoc = Math.max(
        0,
        Math.min(100, ((bv - 11.8) / (14.4 - 11.8)) * 100),
    );
    const fuel = d.fuel || d.fuel_pct || 0;
    const cool = d.coolant || d.coolant_temp || 0;
    const ot = d.oil_temp || 0;
    const fr = d.fuel_rate || 0;
    const sp = d.speed || 0;
    const fuelL = d.remaining_fuel_l || d.fuel_l || 0;
    const fuel_pump = d.fuel_pump;

    setText("adv-rpm-hero", (d.rpm || 0).toLocaleString());
    setText("adv-load-hero", (d.engine_load || 0).toFixed(1) + "%");
    setText("adv-iat-hero", (d.ambient_temp || 0).toFixed(1) + "°C");
    setText("adv-throttle-hero", (d.throttle_pct || 0).toFixed(1) + "%");

    setText("adv-engine-state-chip", d.engine_state || "IDLE");
    setText(
        "adv-gear-chip",
        (d.gear_num || 0) === 0 ? "N" : String(d.gear_num),
    );
    setText("adv-brake-chip", "BRAKE: " + (d.brake_state ? "DOWN" : "UP"));
    setText("adv-clutch-chip", "CLUTCH: " + (d.clutch_state ? "DOWN" : "UP"));

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

    // Fuel
    // Clamp percentage to 0-100
    const pct = Math.max(0, Math.min(100, fuel ?? 0));

    // Fuel bar
    document.getElementById("adv-fuel-bar").style.width = `${pct}%`;
    document.getElementById("adv-fuel-pct-val").textContent =
        `${pct.toFixed(0)}%`;

    // Remaining fuel
    document.getElementById("adv-fuel-l-val").textContent = (
        fuelL ?? 0
    ).toFixed(1);

    // Fuel consumption rate
    document.getElementById("adv-fuel-rate-val").textContent = (
        fr ?? 0
    ).toFixed(1);

    // Fuel pump status
    document.getElementById("adv-fuel-pump-val").textContent = fuel_pump
        ? "ON"
        : "OFF";

    //Tyre Pressure

    updateTyrePressure("t-fl", "t-fl-bar", d.tyre_pressure_fl);
    updateTyrePressure("t-fr", "t-fr-bar", d.tyre_pressure_fr);
    updateTyrePressure("t-rl", "t-rl-bar", d.tyre_pressure_rl);
    updateTyrePressure("t-rr", "t-rr-bar", d.tyre_pressure_rr);

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
        altBar.style.width =
            Math.min(100, ((bv - 11) / 4) * 100).toFixed(0) + "%";
    setText("adv-oiltemp-kpi", ot.toFixed(1) + " °C");
    const otBar = document.getElementById("adv-oiltemp-bar");
    if (otBar) {
        otBar.style.width =
            Math.min(100, ((ot - 40) / 80) * 100).toFixed(0) + "%";
        otBar.style.background = ot > 110 ? "#ef4444" : "#f59e0b";
    }
    document.getElementById("adv-engload-kpi").textContent =
        `${d.engine_load.toFixed(0)}%`;
    document.getElementById("adv-engload-bar").style.width =
        `${d.engine_load}%`;
    const estKm =
        fr > 0.01 && sp > 0 ? Math.round(((fuelL * 1000) / fr / 3600) * sp) : 0;
    setText("adv-range-kpi", estKm > 0 ? estKm + " km" : "—");
    const rngBar = document.getElementById("adv-range-bar");
    if (rngBar)
        rngBar.style.width =
            Math.min(100, (estKm / 400) * 100).toFixed(0) + "%";

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
    if (document.getElementById("adv-speed-chart"))
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

// Render one tyre indicator's fill/label on the Advanced tab's tyre diagram.
function setTyre(valId, barId, psi) {
    const el = document.getElementById(valId);
    const barEl = document.getElementById(barId);
    if (barEl == null) return;
    if (psi == null) return;
    const color = psi < 26 ? "#ef4444" : psi < 29 ? "#f59e0b" : "#10b981";
    if (el) {
        el.innerHTML =
            psi.toFixed(1) + ' <span class="adv-tyre-unit">psi</span>';
        el.style.color = color;
    }
    if (barEl) {
        barEl.style.width = Math.min(100, (psi / 36) * 100).toFixed(0) + "%";
        barEl.style.background = color;
    }
}
