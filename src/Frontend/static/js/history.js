// Signal History tab: historical chart + table view.

import { state } from "./state.js";
import { SIGNAL_MAP, FILL_MAP } from "./live.js";
import { setStatus, setText } from "./ui.js";

// Fetch the recorded signal history and render the chart/table for the History tab.
export async function loadHistory() {
    if (state.currentMode !== "history") return;
    try {
        const res = await fetch("/history-data");
        const data = await res.json();
        if (data.error) {
            setStatus(false, data.error);
            return;
        }
        // console.log(data)
        renderHistoryChart(data);
        renderTable(data);
        const sig = document.getElementById("signal-select").value;
        const range = document.getElementById("range-select").value;
        const meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed;
        const all = data[meta.key] || [];
        const n =
            range === "all"
                ? all.length
                : Math.min(all.length, parseInt(range, 10));
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

// Extract the most recent N samples of a given field from the history dataset.
export function getSlice(arr, rangeVal) {
    if (!arr || !arr.length) return [];
    if (rangeVal === "all") return arr;
    const n = parseInt(rangeVal, 10);
    return arr.slice(Math.max(0, arr.length - n));
}

// Draw the multi-signal history line chart via Plotly.
export function renderHistoryChart(data) {
    const sig = document.getElementById("signal-select").value;
    const range = document.getElementById("range-select").value;
    const meta = SIGNAL_MAP[sig] || SIGNAL_MAP.speed;
    const isDark =
        document.documentElement.getAttribute("data-theme") !== "light";
    const gridColor = isDark ? "#111828" : "#dde5f0";
    const fontColor = isDark ? "#4a5568" : "#6a7890";
    const y = getSlice(data[meta.key] || [], range);
    const x = y.map((_, i) => i);
    const isStep = sig === "gear_num";
    console.log(x.slice(0, 20));
    console.log(y.slice(0, 20));
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

// Render the tabular view of recent history samples.
export function renderTable(data) {
    const range = document.getElementById("range-select").value;
    const tbody = document.getElementById("table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    const all = data.time || [];
    const n =
        range === "all"
            ? all.length
            : Math.min(all.length, parseInt(range, 10));
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
export const HISTORY_FIELDS = {
    speed: "Speed (km/h)",
    rpm: "RPM",
    coolant: "Coolant Temp (°C)",
    oil_temp: "Oil Temp (°C)",
    fuel_pct: "Fuel %",
    fuel_rate: "Fuel Rate",
    throttle: "Throttle %",
    engine_load: "Engine Load %",
    accel: "Accel (m/s²)",
    battery: "Battery (V)",
};
