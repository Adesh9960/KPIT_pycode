// Application entry point. Wires up global effects (tilt, clock), starts
// the live-data poll loop that fans out to every tab's update function, and
// exposes the handful of functions referenced by inline onclick="" handlers
// in the HTML onto window (ES modules are not global scope by default).

import { state } from "./state.js";
import { updateAdvanced } from "./advanced.js";
import { loadHistory } from "./history.js";
import { updateLive, updateLiveChart, updateWeatherDisplay } from "./live.js";
import { setMode } from "./navigation.js";

import {
    initProgTerminal,
    pgRunCommand,
    pgEditorWrite,
    pgEditorClear,
} from "./programming.js";
import {
    readDID,
    ioControl,
    loadDTCs,
    clearDTCs,
    updateTechnician,
} from "./technician.js";
import {
    confirmTechUnlock,
    cancelTechUnlock,
    exitTechMode,
} from "./session.js";
import { checkAlerts, setStatus, startClock } from "./ui.js";

// Poll /live-data and fan the result out to every tab's update function, plus alerts and status.
function pollLive() {
    fetch("http://127.0.0.1:5000/live-data")
        .then((res) => res.json())
        .then((data) => {
            updateLive(data);
            updateAdvanced(data);
            updateTechnician(data);
            checkAlerts(data);
            setStatus(true);
            updateWeatherDisplay(data);
        })
        .catch((err) => {
            console.error("Error : ", err);
        });
}

// Add a pointer-tracked tilt/lighting effect to elements with the tilt-card class.
function bindTilt(card) {
    card.addEventListener("mousemove", (e) => {
        if (!document.body.classList.contains("fx-mode-tilt")) return;
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width; // 0 to 1
        const py = (e.clientY - r.top) / r.height; // 0 to 1
        const rotateY = (px - 0.5) * 10; // max 5deg either side
        const rotateX = (0.5 - py) * 10;
        card.style.transform = `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg)`;
    });
    card.addEventListener("mouseleave", () => {
        if (document.body.classList.contains("fx-mode-tilt")) {
            card.style.transform =
                "perspective(800px) rotateX(0deg) rotateY(0deg)";
        }
    });
}

// ══════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════
// Application entry point: starts the clock, binds tilt effects, and kicks off the first data poll.
function init() {
    cards().forEach(bindMouseLight);
    cards().forEach(bindTilt);
    updateScrollLight();
    updateMagneticGlowColor();
}

document.addEventListener("DOMContentLoaded", () => {
    startClock();
    setMode("live");
    initProgTerminal();

    document.getElementById("signal-select")?.addEventListener("change", () => {
        if (state.currentMode === "history") loadHistory();
    });
    document.getElementById("range-select")?.addEventListener("change", () => {
        if (state.currentMode === "history") loadHistory();
    });
});

setInterval(loadHistory, 3000);
setInterval(updateLiveChart, 1000);
setInterval(pollLive, 100);
loadHistory();
pollLive();
