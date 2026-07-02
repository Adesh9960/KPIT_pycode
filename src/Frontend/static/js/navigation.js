// Tab (mode) switching for the dashboard's five pages.

import { state } from "./state.js";
import { loadHistory } from "./history.js";
import { pgtermFocusInput } from "./programming.js";

// ══════════════════════════════════════════════════
// MODE SWITCHING
// ══════════════════════════════════════════════════
// Switch the active dashboard tab: toggles nav/page visibility and body mode class, and triggers any tab-entry side effects (history reload, terminal focus).
export function setMode(mode) {
    state.currentMode = mode;
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
